from fastapi import APIRouter, Cookie
from starlette.responses import JSONResponse, Response
from starlette.requests import Request

import prometheus_client as prom

from Utils.Prometheus import API_REGISTRY, active_sessions
from routers import discord, crowdin, guilds

router = APIRouter()

from Utils import Auth, Redis

@router.get("/")
async def read_root():
    return {"status": "WIP"}

@router.get("/metrics")
async def get_prom_metrics():
    metric_data = prom.generate_latest(API_REGISTRY).decode("utf-8")
    return Response(metric_data, media_type="text/plain")

@router.get("/test")
async def test(request: Request):
    request.session["test"] = "testing"
    return {"status": "TESTING"}


@router.get("/test2")
async def get_test(request: Request):
    return {"test": request.session["test"]}


@router.get("/logout")
async def logout(request: Request):
    request.session.clear()

    active_sessions.dec()

    return JSONResponse(dict(status="Success"))


@router.get("/whoami")
@Auth.auth_required
async def identify_endpoint(request: Request):
    # Make sure that after a restart we keep the session counter out of the negitive
    # This will catch sessions that exist but don't hit the login endpoint
    if active_sessions._value._value <= 0:
        active_sessions.inc()

    return await Redis.ask_the_bot("user_info", user_id=request.session["user_id"])

@router.get("/languages")
async def languages(request: Request):
    return await Redis.ask_the_bot("languages")

router.include_router(discord.router, prefix="/discord", responses={404: {"description": "Not found"}})
router.include_router(crowdin.router, prefix="/crowdin-webhook", responses={404: {"description": "Not found"}})
router.include_router(guilds.router, prefix="/guilds", responses={404: {"description": "Not found"}})