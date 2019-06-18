import json
from datetime import timedelta

from aiohttp import client

from fastapi import FastAPI
from starlette.middleware.sessions import SessionMiddleware

from Utils import Configuration, Redis
from routers import crowdin, main, discord

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


app.add_middleware(SessionMiddleware, max_age=Configuration.SESSION_TIMEOUT_LEN, secret_key=Configuration.SESSION_KEY)
app.include_router(main.router, prefix="/api", responses={404: {"description": "Not found"}})
app.include_router(discord.router, prefix="/api/discord", responses={404: {"description": "Not found"}})
app.include_router(crowdin.router, prefix="/api/crowdin-webhook", responses={404: {"description": "Not found"}})

import uvicorn

if __name__ == "__main__":
    print("Starting Gearbot Dashboard Backend...")
    uvicorn.run(app, host="127.0.0.1", port=5000, log_level="info", reload=True)
