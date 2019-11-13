import asyncio
import time
import sys

import sentry_sdk
from fastapi import FastAPI
from sentry_sdk.integrations.asgi import SentryAsgiMiddleware
from starlette.middleware.cors import CORSMiddleware
from starlette.requests import Request
from tortoise import Tortoise

from Utils.Configuration import DB_URL, DSN
from Utils.Prometheus import session_monitor
from Utils import Configuration, Redis
from Utils.RateLimits import cleaner_task
from routers import api, websocket

app = FastAPI()

if DSN != "":
    sentry_sdk.init(dsn=DSN)
    app.add_middleware(SentryAsgiMiddleware)

@app.on_event("startup")
async def session_init():
    await Redis.initialize()
    print("Redis connections initialized")

    loop = asyncio.get_running_loop()
    loop.create_task(cleaner_task())

    await Tortoise.init(
        db_url=DB_URL,
        modules={'models': ['Utils.DataModels']}
    )
    # Generate the schema
    await Tortoise.generate_schemas()
    print("Database connection established")

    await Redis.cache()
    print("Startup complete")

# This currently breaks closing Redis when running inside pytest, will need a better fix
@app.on_event("shutdown")
async def session_close(): # Stay tidy
    if "pytest" in sys.modules:
        return
    await Redis.get_redis().close()
    await Tortoise.close_connections()


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    f = time.perf_counter_ns if hasattr(time, "perf_counter_ns") else time.perf_counter
    start_time = f()
    response = await call_next(request)
    process_time = f() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response





# app.add_middleware(SessionMiddleware, max_age=Configuration.SESSION_TIMEOUT_LEN, secret_key=Configuration.SESSION_KEY)
app.add_middleware(CORSMiddleware, allow_origins=Configuration.CORS_ORGINS, allow_credentials=True, allow_methods=['GET', 'POST', 'PATCH', 'PUT', 'DELETE', 'OPTIONS'], allow_headers =['*'])
# app.add_middleware(PromStatsMiddleware)
app.include_router(api.router, prefix="/api", responses={404: {"description": "Not found"}})
app.include_router(websocket.router) # NO PREFIX HERE OR IT WILL FAIL



import uvicorn

if __name__ == "__main__":
    print("Starting Gearbot Dashboard Backend...")
    uvicorn.run("api:app", host="127.0.0.1", port=5000, log_level="info", reload=True)