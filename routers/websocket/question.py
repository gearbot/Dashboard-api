import asyncio

from aiohttp import client
from Utils.Configuration import API_LOCATION
from Utils import Redis
from routers.websocket.infractions import inf_search


async def inbox(websocket, message):
    print(message)
    auth_info = getattr(websocket, "auth_info", None)
    user_id = auth_info and auth_info.user_id
    info = message["info"] or dict()
    info ["user_id"] = user_id
    reply = await Redis.ask_the_bot(message["question"], **info)
    print(reply)
    await websocket.send_json({
        "type": "reply",
        "content": {
            "uid": message["uid"],
            "answer": reply
        }
    })


async def get_user_guilds_gearbot(websocket, **kwargs):
    auth_info = websocket.auth_info
    assembled = dict()
    return await Redis.ask_the_bot("get_user_guilds", user_id = websocket.auth_info.user_id)

async def get_user_guilds_all(websocket, **kwargs):
    auth_info = websocket.auth_info
    headers = {
        "Authorization": f"Bearer {auth_info.user.api_token}"
    }
    async with client.ClientSession() as session_pool:
        async with session_pool.get(f"{API_LOCATION}/users/@me/guilds", headers=headers) as resp:
            guild_list = await resp.json()
            if not isinstance(guild_list, list):
                return False
            all_guilds = dict()
            for guild in guild_list:
                if guild["owner"] or guild["permissions"] & 32 == 32:
                    all_guilds[str(guild["id"])] = {
                        "id": str(guild["id"]),
                        "name": str(guild["name"]),
                        "icon": guild["icon"]
                    }
    await session_pool.close()
    return all_guilds

handlers = {
    "get_user_guilds_gearbot": get_user_guilds_gearbot,
    "get_user_guilds_all": get_user_guilds_all,
    "infraction_search": inf_search
}


async def inbox_api(websocket, message):
    print(message)
    info = message["info"] or dict()
    if message["question"] not in handlers:
        await websocket.send_json(dict(type="error", content="Unknown api question type!"))
    else:
        reply = await handlers[message["question"]](websocket, **info)
        print(reply)
        await websocket.send_json({
            "type": "reply",
            "content": {
                "uid": message["uid"],
                "answer": reply
            }
        })

