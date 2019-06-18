import asyncio
import uuid

import aioredis

storage_pool = None
message_pool = None
replies = dict()


def get_redis():
    return storage_pool


async def initialize():
    global storage_pool, message_pool
    storage_pool = await aioredis.create_redis_pool(("192.168.0.128", 6379), encoding="utf-8", db=0)
    message_pool = await aioredis.create_redis_pool(("192.168.0.128", 6379), encoding="utf-8", db=0, maxsize=2)
    loop = asyncio.get_running_loop()
    loop.create_task(receiver())


async def receiver():
    recv = await message_pool.subscribe("bot-dash-messages")
    recv_channel = recv[0]
    while await recv_channel.wait_message():
        reply = await recv_channel.get_json()
        replies[reply["uid"]] = reply["reply"]
        await asyncio.sleep(5)  # If nobody retreived it after 5s something is already broken, no need to leak as well
        if reply["uid"] in replies:
            del replies[reply["uid"]]


async def ask_the_bot(type, **kwargs):
    # Attach uid for tracking and send to the bot
    uid = str(uuid.uuid4())
    await message_pool.publish_json("dash-bot-messages", dict(type=type, uid=uid, **kwargs))
    # Wait for a reply for up to 6 seconds
    waited = 0
    while uid not in replies:
        await asyncio.sleep(0.1)
        waited += 1
        if waited >= 60:
            raise RuntimeError("No reply after 6 seconds, something must have gone wrong!")

    r = replies[uid]
    del replies[uid]
    return r
