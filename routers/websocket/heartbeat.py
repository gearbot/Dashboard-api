async def ping(websocket, message):
    await websocket.send_json(dict(type="pong"))