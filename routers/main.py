import asyncio
import os

from fastapi import APIRouter
from starlette.responses import JSONResponse, Response
from starlette.requests import Request

import prometheus_client as prom
from prometheus_client import multiprocess, CollectorRegistry

from Utils.Prometheus import active_sessions, notice_session
from Utils.Responses import successful_action_response
from routers import discord, crowdin, guilds

if "prometheus_multiproc_dir" in os.environ:
    prom_multit_mode = True
else:
    prom_multit_mode = False

router = APIRouter()

from Utils import Auth, Redis

@router.get("/")
async def read_root():
    return {"status": "WIP"}

@router.get("/metrics")
async def get_prom_metrics():
    if prom_multit_mode:
        registry = CollectorRegistry()
        multiprocess.MultiProcessCollector(registry)
        metric_data = prom.generate_latest(registry).decode("utf-8")
    else:
        metric_data = prom.generate_latest(prom.REGISTRY).decode("utf-8")
    return Response(metric_data, media_type="text/plain")

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
    # If their session expires before they press logout then gauge could be at 0
    # If it was, then don't bother removing their session again, it already happened
    if active_sessions._value._value > 0:
        loop = asyncio.get_running_loop()
        loop.create_task(notice_session(request.session["user_id"], False))

    request.session.clear()

    return successful_action_response

# In case some other method of accessing these stats are needed
@router.get("/spinning")
async def still_spinning(request: Request):
    return await Redis.is_bot_alive()

@router.get("/whoami")
@Auth.auth_required
async def identify_endpoint(request: Request):
    # Make sure that after a restart we keep the session counter out of the negitive
    # This will catch sessions that exist but don't hit the login endpoint
    if active_sessions._value._value <= 0:
        loop = asyncio.get_running_loop()
        loop.create_task(notice_session(request.session["user_id"], True))

    return await Redis.ask_the_bot("user_info", user_id=request.session["user_id"])

@router.get("/general_info")
async def general_info():
    return await Redis.get_cache_info()

router.include_router(discord.router, prefix="/discord", responses={404: {"description": "Not found"}})
router.include_router(crowdin.router, prefix="/crowdin-webhook", responses={404: {"description": "Not found"}})
router.include_router(guilds.router, prefix="/guilds", responses={404: {"description": "Not found"}})