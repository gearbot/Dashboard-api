from fastapi import APIRouter, Cookie
from starlette.responses import JSONResponse
from starlette.requests import Request


router = APIRouter()

from Utils import Auth, Redis

@router.get("/")
async def read_root():
    return {"status": "WIP"}

@router.get("/whoami")
async def identify_endpoint(authtoken: str = Cookie(None), request: Request=None):
    print(authtoken)
    bad_auth_resp = JSONResponse({ "status": "INVALID AUTH" }, status_code=401)
    if authtoken == None:
        # Handle this on the frontend via sending them to login
        return bad_auth_resp
    user = await Auth.verify_user(authtoken, request)

    if user.is_err():
        return bad_auth_resp
    else:
        user = user.unwrap()
        user_id = user["id"]
        token = user["token"]

    print("Sending info request to Gearbot...")

    data_link = await Redis.get_redis(0)
    recv = await data_link.subscribe("bot-dash-messages")
    recv_channel = recv[0]

    await data_link.publish_json("dash-bot-messages", dict(type="user_info",
        uid = user_id
    ))

    while (await recv_channel.wait_message()):
        user_info = await recv_channel.get_json()
        if user_info == None:
            print("Invalid user was requested")
            return bad_auth_resp
        else:
            print(user_info)
            return { "status": "VALIDATED" }
