import asyncio
import os

from fastapi import APIRouter, Cookie
from starlette.responses import Response
from starlette.requests import Request

import prometheus_client as prom
from prometheus_client import multiprocess, CollectorRegistry

from Utils.Auth import reauth_socket
from Utils.Prometheus import active_sessions, notice_session
from Utils.Responses import successful_action_response, unauthorized_response
from routers import crowdin, admin
from routers.api import discord
from routers.websocket import socket_by_user

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


@router.get("/logout")
async def logout(request: Request):
    if "token" in request.cookies:
        token = request.cookies["token"]
        info = await Auth.get_token_info(token)
        if info is not None:
            user_id = info.user.id
            await info.delete()
            if user_id in socket_by_user:
                for socket in socket_by_user[user_id]:
                    if socket.auth_info.id == token:
                        await reauth_socket(socket)

    return successful_action_response

# In case some other method of accessing these stats are needed
@router.get("/spinning")
async def still_spinning(request: Request):
    return await Redis.is_bot_alive()

@router.get("/whoami")
async def whoami(request: Request, token: str = Cookie(None)):
    if token is None:
        return unauthorized_response

    info = await Auth.get_token_info(token)
    if info is None:
        return unauthorized_response

    return {
        "id": str(info.user_id),
        **await Redis.ask_the_bot("user_info", user_id=info.user_id)
    }

@router.get("/general_info")
async def general_info():
    return await Redis.get_cache_info()

router.include_router(discord.router, prefix="/discord", responses={404: {"description": "Not found"}})
router.include_router(crowdin.router, prefix="/crowdin-webhook", responses={404: {"description": "Not found"}})
router.include_router(admin.router, prefix="/admin", responses={404: {"description": "Not found"}})