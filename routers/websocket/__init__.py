import json
from datetime import datetime

from fastapi import APIRouter
from starlette.websockets import WebSocket, WebSocketState, WebSocketDisconnect
from tortoise.exceptions import DoesNotExist

from Utils.DataModels import Dashsession


router = APIRouter()

socket_by_token = dict()
socket_by_subscription = dict()

from routers.websocket.auth import hello
from routers.websocket.subscriptions import unsubscribe, subscribe

handlers = {
    "hello": hello,
    "subscribe": subscribe,
    "unsubscribe": unsubscribe
}


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    if "token" in websocket.cookies:
        token = websocket.cookies["token"]
        # validate token, close socket if it's a bad token
        try:
            info = await Dashsession.get(id=token)
        except DoesNotExist:
            pass  # invalid token pretend it's not there
        else:
            # is the token still valid?
            if info.expires_at > datetime.now():
                websocket.auth_info = info
                socket_by_token[token] = websocket

    # wrap in try except to make sure we can cleanup no matter what goes wrong
    websocket.active_subscriptions = []
    try:
        await websocket.accept()
        print("Websocket accepted")
        while websocket.application_state == WebSocketState.CONNECTED and websocket.client_state == WebSocketState.CONNECTED:
            try:
                data = await websocket.receive_text()
                if data != "":
                    data = json.loads(data)
                    await handlers[data["type"]](websocket, data.get("message", {}))
            except WebSocketDisconnect:
                break
        print("websocket closed")
    except Exception as ex:
        await cleanup(websocket)
        raise ex
    else:
        await cleanup(websocket)
    print("closed")


async def cleanup(websocket):
    if hasattr(websocket, "auth_info"):
        del socket_by_token[websocket.auth_info.id]
    for s in websocket.active_subscriptions:
        await unsubscribe(websocket, dict(channel=s))
