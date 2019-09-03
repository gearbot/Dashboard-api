from Utils import Redis


async def inbox(websocket, message):
    print(message)
    auth_info = getattr(websocket, "auth_info", None)
    user_id = auth_info and auth_info.user_id
    reply = await Redis.ask_the_bot(message["question"], **message["info"], user_id=user_id)
    print(reply)
    await websocket.send_json({
        "type": "reply",
        "content": {
            "uid": message["uid"],
            "answer": reply
        }
    })
