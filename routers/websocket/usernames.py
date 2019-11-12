
# looks up usernames, just forwards to the bot
from Utils import Redis


async def get_usernames(websocket, message):
    await Redis.send_to_bot("usernames_request", uid=websocket.uid, ids=message.get("ids", []))
