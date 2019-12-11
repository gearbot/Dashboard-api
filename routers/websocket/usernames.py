
# looks up usernames, just forwards to the bot
from Utils import Redis


async def get_users_info(websocket, message):
    await Redis.send_to_bot("get_users_info", uid=websocket.uid, ids=message.get("ids", []))
