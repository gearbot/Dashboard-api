import json
from secrets import token_urlsafe
from time import time
from datetime import timedelta

from aiohttp import client

from fastapi import FastAPI

from Utils import Redis


with open("config.json") as config_file:
    config = json.load(config_file)

API_LOCATION = "https://discordapp.com/api"

CLIENT_ID = config["clientID"]
CLIENT_SECRET = config["clientSecret"]
REDIRECT_URI = config["redirect_uri"]
CLIENT_URL = config["client_url"]
SESSION_TIMEOUT_LEN = config["session_timeout_length"]

HMAC_KEY = None
KEY_CYCLE_LENGTH = timedelta(days=SESSION_TIMEOUT_LEN)

app = FastAPI()

@app.on_event("startup")
async def crypto_init():
    global HMAC_KEY
    redis_db = await Redis.get_redis(1)

    print("Registering HMAC key...")
    stored_hmac_key = await redis_db.get("hmackey")

    if stored_hmac_key == None:
        HMAC_KEY = token_urlsafe(64)
        await redis_db.set("hmackey", f"{time()}tstp{HMAC_KEY}")
    else: # This has been tested to work
        timestamp, stored_hmac_key = stored_hmac_key.split("tstp")
        if (time() - float(timestamp)) < KEY_CYCLE_LENGTH.total_seconds(): # Make sure the HMAC key stays "fresh". Probably good practice
            HMAC_KEY = stored_hmac_key
        else:
            print("The old key expired, refreshing it!")
            HMAC_KEY = token_urlsafe(64)
            await redis_db.set("hmackey", f"{time()}tstp{HMAC_KEY}")

    app.HMAC_KEY = HMAC_KEY
    print("Secrets setup!")

@app.on_event("startup")
async def session_init():
    app.session_pool = client.ClientSession()
    print("HTTP Client Session initialized")

@app.on_event("shutdown")
async def session_close(): # Stay tidy
    await app.session_pool.close()

from routers import crowdin, main, discord

app.include_router(main.router, prefix="/api", responses={404: {"description": "Not found"}})
app.include_router(discord.router, prefix="/api/discord", responses={404: {"description": "Not found"}})
app.include_router(crowdin.router, prefix="/api/crowdin-webhook", responses={404: {"description": "Not found"}})

import uvicorn

if __name__ == "__main__":
    print("Starting Gearbot Dashboard Backend...")
    uvicorn.run(app, host="127.0.0.1", port=5000, log_level="info", reload=True)
