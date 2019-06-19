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


@router.get("/whoami")
@Auth.auth_required
async def identify_endpoint(request: Request):
    return await Redis.ask_the_bot("user_info", user_id=request.session["user_id"])


@router.get("/logout")
@Auth.auth_required
async def logout(request: Request):
    for k in ["user_id", "refresh_token", "access_token", "expires_at"]:
        del request.session[k]
    return JSONResponse(dict(status="Success"))


@router.get("/guilds")
@Auth.auth_required
async def guild_list_endpoint(request: Request):
    # Grab the user's guilds from Discord
    print("getting guild info")
    guilds_list = await Auth.query_endpoint(request, "get", "/users/@me/guilds")

    formatted_guild_list = []

    for guild in guilds_list:
        formatted_guild_list.append(guild["id"])
    print("asking the bot")
    return await Redis.ask_the_bot("guild_perms", user_id=request.session["user_id"], guild_list=formatted_guild_list)
