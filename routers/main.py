from fastapi import APIRouter, Cookie
from starlette.responses import JSONResponse
from starlette.requests import Request

from routers import discord, crowdin, guilds

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


@router.get("/logout")
@Auth.auth_required
async def logout(request: Request):
    for k in ["user_id", "refresh_token", "access_token", "expires_at"]:
        del request.session[k]
    return JSONResponse(dict(status="Success"))


@router.get("/whoami")
@Auth.auth_required
async def identify_endpoint(request: Request):
    return await Redis.ask_the_bot("user_info", user_id=request.session["user_id"])

router.include_router(discord.router, prefix="/discord", responses={404: {"description": "Not found"}})
router.include_router(crowdin.router, prefix="/crowdin-webhook", responses={404: {"description": "Not found"}})
router.include_router(guilds.router, prefix="/guilds", responses={404: {"description": "Not found"}})