from fastapi import APIRouter, Cookie
from starlette.responses import JSONResponse
from starlette.requests import Request


router = APIRouter()

from Utils import Auth, Redis

@router.get("/")
async def read_root():
    return {"status": "WIP"}


@router.get("/test")
async def test(request: Request):
    request.session["test"] = "testing"
    return {"status": "TESTING"}

@router.get("/test2")
async def get_test(request: Request):
    return {"test": request.session["test"]}

@Auth.auth_required
@router.get("/whoami")
async def identify_endpoint(request: Request):
    if request.session == {}:
        return Auth.bad_auth_resp
    return await Redis.ask_the_bot("user_info", user_id=request.session["user_id"])

@Auth.auth_required
@router.get("/guilds")
async def guild_list_endpoint(request: Request):
    session_pool  = request.app.session_pool

    # Grab the user's guilds from Discord
    guilds_list = await Auth.query_endpoint(request, "get", "/users/@me/guilds")

    formatted_guild_list = []

    for guild in guilds_list:
        formatted_guild_list.append(guild["id"])

    return await Redis.ask_the_bot("guild_perms", user_id=request.session["user_id"], guild_list=formatted_guild_list)
