import asyncio
import time
import sys

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request

from Utils.Prometheus import PromStatsMiddleware, session_monitor
from Utils import Configuration, Redis
from routers import main

app = FastAPI()


@app.on_event("startup")
async def session_init():
    await Redis.initialize()
    print("Redis connections initialized")

    loop = asyncio.get_running_loop()
    loop.create_task(session_monitor())
    print("Session monitor initialized")

    await Redis.cache()

# This currently breaks closing Redis when running inside pytest, will need a better fix
@app.on_event("shutdown")
async def session_close(): # Stay tidy
    if "pytest" in sys.modules:
        return
    await Redis.get_redis().close()


@app.middleware("http")
async def add_process_time_header(request: Request, call_next):
    f = time.perf_counter_ns if hasattr(time, "perf_counter_ns") else time.perf_counter
    start_time = f()
    response = await call_next(request)
    process_time = f() - start_time
    response.headers["X-Process-Time"] = str(process_time)
    return response


app.add_middleware(SessionMiddleware, max_age=Configuration.SESSION_TIMEOUT_LEN, secret_key=Configuration.SESSION_KEY)
app.add_middleware(CORSMiddleware, allow_origins=Configuration.CORS_ORGINS, allow_credentials=True, allow_methods=['GET', 'POST', 'PATCH', 'PUT', 'DELETE', 'OPTIONS'], allow_headers =['*'])
app.add_middleware(PromStatsMiddleware)
app.include_router(main.router, prefix="/api", responses={404: {"description": "Not found"}})

import uvicorn

if __name__ == "__main__":
    print("Starting Gearbot Dashboard Backend...")
    uvicorn.run("api:app", host="127.0.0.1", port=5000, log_level="info", reload=True)