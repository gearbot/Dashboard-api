import json
from datetime import timedelta

from aiohttp import client

from fastapi import FastAPI
from starlette.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware

from Utils import Configuration, Redis
from routers import crowdin, main, discord, guilds

app = FastAPI()


@app.on_event("startup")
async def session_init():
    app.session_pool = client.ClientSession()
    print("HTTP Client Session initialized")
    await Redis.initialize()
    print("Redis connections initialized")


@app.on_event("shutdown")
async def session_close():  # Stay tidy
    await app.session_pool.close()
    await Redis.get_redis().close()


app.add_middleware(SessionMiddleware, max_age=Configuration.SESSION_TIMEOUT_LEN, secret_key=Configuration.SESSION_KEY)
app.add_middleware(CORSMiddleware, allow_origins=Configuration.CORS_ORGINS, allow_credentials=True, allow_methods=['GET', 'POST', 'PATCH', 'PUT', 'DELETE', 'OPTIONS'], allow_headers =['*'])
app.include_router(main.router, prefix="/api", responses={404: {"description": "Not found"}})

import uvicorn

if __name__ == "__main__":
    print("Starting Gearbot Dashboard Backend...")
    uvicorn.run("api:app", host="127.0.0.1", port=5000, log_level="info", reload=True)