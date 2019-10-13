from Utils.Errors import FailedException, UnauthorizedException, NoReplyException, BadRequestException
from collections import namedtuple
from routers.websocket.question import inbox

socket_by_user = dict()
socket_by_subscription = dict()



from fastapi import APIRouter
from starlette.websockets import WebSocket, WebSocketState, WebSocketDisconnect

from Utils import Auth, Configuration
from routers.websocket.heartbeat import ping

router = APIRouter()



from routers.websocket.auth import hello
from routers.websocket.subscriptions import unsubscribe, subscribe

handlers = {
    "hello": hello,
    "subscribe": subscribe,
    "unsubscribe": unsubscribe,
    "ping": ping,
    "question": inbox
}


@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    if "origin" not in websocket.headers or websocket.headers["origin"] not in Configuration.CORS_ORGINS:
        await websocket.accept()
        await websocket.send_text("it's too late in the evening to come up with a with a punny denied message so this will do for now")
        await websocket.close()
        return
    if "token" in websocket.cookies:
        token = websocket.cookies["token"]
        info = await Auth.get_token_info(token)
        if info is not None:
            websocket.auth_info = info
            if info.user.id not in socket_by_user:
                socket_by_user[info.user.id] = list()
            socket_by_user[info.user.id].append(websocket)

    # wrap in try except to make sure we can cleanup no matter what goes wrong
    websocket.active_subscriptions = dict()
    try:
        await websocket.accept()
        print("Websocket accepted")
        while websocket.application_state == WebSocketState.CONNECTED and websocket.client_state == WebSocketState.CONNECTED:
            try:
                data = await websocket.receive_json()
                if data["type"] not in handlers:
                    await websocket.send_json(dict(type="error", content="Unknown type!"))
                else:
                    await handlers[data["type"]](websocket, data.get("message", {}))
            except WebSocketDisconnect:
                break
            except Exception as ex:
                if isinstance(ex, FailedException):
                    await websocket.send_json(dict(type="error", content="Seems the bot failed to process your query, please try again later"))
                elif isinstance(ex, UnauthorizedException):
                    await websocket.send_json(dict(type="error", content="Access denied!"))
                elif isinstance(ex, NoReplyException):
                    await websocket.send_json(dict(type="error", content="Unable to communicate with GearBot, please try again later"))
                else:
                    await websocket.send_json(dict(type="error", content="Something went wrong!"))
                    raise ex
    except Exception as ex:
        await cleanup(websocket)
        raise ex
    else:
        await cleanup(websocket)
    print("Websocket closed")


async def cleanup(websocket):
    if hasattr(websocket, "auth_info"):
        if len(socket_by_user[websocket.auth_info.user.id]) is 1:
            del socket_by_user[websocket.auth_info.user.id]
        else:
            socket_by_user[websocket.auth_info.user.id].remove(websocket)
    for channel in websocket.active_subscriptions.copy().keys():
        await unsubscribe(websocket, dict(channel=channel))
