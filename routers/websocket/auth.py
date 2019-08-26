from starlette.websockets import WebSocket

from Utils import Redis


async def hello(websocket: WebSocket, message):
    if not hasattr(websocket, "auth_info"):
        reply = {"authorized": False}
    else:
        reply = {
            "authorized": True,
            "user_info": await Redis.ask_the_bot("user_info", user_id=websocket.auth_info.user_id)
        }
    await websocket.send_json(
        {
            "type": "hello",
            "content": reply
        })


def auth_required(handler):
    async def wrapper(websocket, message):
        if hasattr(websocket, "auth_info"):
            return await handler(websocket, message)
    return wrapper
