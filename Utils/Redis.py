import asyncio
import uuid
from time import time_ns

import aioredis

from Utils.Configuration import REDIS_ADDRESS
from Utils.Errors import FailedException, NoReplyException, UnauthorizedException, BadRequestException
from Utils.Prometheus import redis_message_count, bot_response_latency

storage_pool = None
message_pool = None
replies = dict()


def get_ms_passed(start: float, finish: float) -> float:
    diff = finish - start
    miliseconds_passed = diff / 1000000
    return miliseconds_passed



def get_redis():
    return storage_pool


async def initialize():
    global storage_pool, message_pool
    storage_pool = await aioredis.create_redis_pool(REDIS_ADDRESS, encoding="utf-8", db=0)
    message_pool = await aioredis.create_redis_pool(REDIS_ADDRESS, encoding="utf-8", db=0)
    loop = asyncio.get_running_loop()
    loop.create_task(receiver())


async def receiver():
    recv = await message_pool.subscribe("bot-dash-messages")
    recv_channel = recv[0]
    while await recv_channel.wait_message():
        reply: dict = await recv_channel.get_json()
        replies[reply["uid"]] = {
            "state": reply["state"],
            "reply": reply.get("reply", {}),
            "errors": reply.get("errors", {})
        }
        redis_message_count.labels("received").inc()
        asyncio.get_running_loop().create_task(cleaner(reply["uid"]))


async def cleaner(uid):
    await asyncio.sleep(5)  # If nobody retreived it after 5s something is already broken, no need to leak as well
    if uid in replies:
        del replies[uid]

async def ask_the_bot(type, **kwargs):
    # Attach uid for tracking and send to the bot
    uid = str(uuid.uuid4())
    await message_pool.publish_json("dash-bot-messages", dict(type=type, uid=uid, **kwargs))
    redis_message_count.labels("sent").inc()

    send_time = time_ns()

    # Wait for a reply for up to 12 seconds
    waited = 0
    while uid not in replies:
        await asyncio.sleep(0.1)
        waited += 1
        if waited >= 120:
            raise NoReplyException(
                source="Redis",
                details="Gearbot didn't reply after 12 seconds, Something must of gone wrong!",
            )

    # Track how long it took the bot to respond
    bot_response_latency.observe(get_ms_passed(send_time, time_ns()))

    r = replies[uid]
    del replies[uid]

    if r["state"] == "Failed":
        raise FailedException(source="Gearbot")
    if r["state"] == "Unauthorized":
        raise UnauthorizedException(source="User")
    if r["state"] == "Bad Request":
        raise BadRequestException(source="User", errors=r["errors"])

    return r["reply"]
