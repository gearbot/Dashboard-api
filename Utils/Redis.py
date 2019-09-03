import asyncio
import uuid
from time import time_ns
from datetime import datetime

import aioredis
from aiohttp import client

from Utils.Configuration import REDIS_ADDRESS
from Utils.Errors import FailedException, NoReplyException, UnauthorizedException, BadRequestException
from Utils.Prometheus import redis_message_count, bot_response_latency
from Utils.Configuration import OUTAGE_DETECTION
from Utils.Configuration import MAX_BOT_OUTAGE_WARNINGS, BOT_OUTAGE_WEBHOOK, BOT_OUTAGE_MESSAGE, BOT_OUTAGE_PINGED_ROLES
from routers.websocket.subscriptions import send_to_subscribers

bot_alive = False
storage_pool = None
message_pool = None
replies = dict()
cache_info = None


async def cache_info(message):
    global cache_info
    cache_info = message


async def get_cache_info():
    if cache_info is None:
        await cache()
    return cache_info


async def cache():
    global cache_info
    try:
        cache_info = await ask_the_bot('cache_info')
    except NoReplyException:
        pass


def get_info(message):
    return str(message.get("guild_id", None)), str(message.get("user_id", None))


async def reply(message):
    replies[message["uid"]] = {
        "state": message["state"],
        "reply": message.get("reply", {}),
        "errors": message.get("errors", {})
    }
    asyncio.get_running_loop().create_task(cleaner(message["uid"]))


async def guild_add(message):
    await send_to_subscribers("guilds", subkey=str(message["user_id"]), type="add", guilds=message["guilds"])


async def guild_remove(message):
    await send_to_subscribers("guilds", subkey=str(message["user_id"]), type="remove", guild=message["guild"])


async def guild_update(message):
    guild_id, user_id = get_info(message)
    await send_to_subscribers("guild_info", guild_id, user_id, **message["info"])


handlers = dict(
    cache_info=cache_info,
    reply=reply,
    guild_add=guild_add,
    guild_remove=guild_remove,
    guild_update=guild_update
)


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

    if OUTAGE_DETECTION:
        loop.create_task(bot_spinning())


async def is_bot_alive():
    return bot_alive


async def notify_outage(warning_count: int):
    hook_client = client.ClientSession()

    message_data = BOT_OUTAGE_MESSAGE

    # Apply the timestamp
    message_data["embeds"][0]["timestamp"] = datetime.now().isoformat()

    # Generate the custom message and role pings
    if BOT_OUTAGE_PINGED_ROLES:
        pinged_roles = []
        for role_id in BOT_OUTAGE_PINGED_ROLES:
            pinged_roles.append(f"<@&{role_id}>")

        message_data["content"] += f" Pinging: {', '.join(pinged_roles)}"

    result = await hook_client.post(
        BOT_OUTAGE_WEBHOOK,
        json=message_data
    )

    print("Sent outage notification!")

    await hook_client.close()


async def bot_spinning():
    print("GearBot outage monitor initalized")
    retry_attempts = 0
    warnings_sent = 0
    while True:
        uid = str(uuid.uuid4())
        await message_pool.publish_json(
            "dash-bot-messages",
            dict(
                type="heartbeat",
                uid=uid
            )
        )

        # Wait for a heartbeat for 5 seconds max
        waited = 0
        alive_internal = False
        while uid not in replies:
            await asyncio.sleep(0.1)
            waited += 1
            if waited >= 50:
                alive_internal = False
                retry_attempts += 1
                print("The bot couldn't be reached!")
                break

        if retry_attempts >= 3 and warnings_sent < MAX_BOT_OUTAGE_WARNINGS:

            if BOT_OUTAGE_WEBHOOK:
                warnings_sent += 1
                loop = asyncio.get_running_loop()
                loop.create_task(notify_outage(warnings_sent))
            else:
                print("A webhook to use for notifying was not set up, no warning will be sent!")

            retry_attempts = 0

        if waited < 20:
            retry_attempts = 0
            alive_internal = replies[uid]["reply"]
            del replies[uid]

        global bot_alive
        bot_alive = alive_internal

        await asyncio.sleep(60)


async def receiver():
    recv = await message_pool.subscribe("bot-dash-messages")
    recv_channel = recv[0]
    while await recv_channel.wait_message():
        reply: dict = await recv_channel.get_json()
        await handlers[reply["type"]](reply["message"])
        redis_message_count.labels("received").inc()


async def cleaner(uid):
    await asyncio.sleep(5)  # If nobody retreived it after 5s something is already broken, no need to leak as well
    if uid in replies:
        del replies[uid]


async def send_to_bot(t, **kwargs):
    await message_pool.publish_json("dash-bot-messages", dict(type=t, message=kwargs))


async def ask_the_bot(type, **kwargs):
    # Attach uid for tracking and send to the bot
    uid = str(uuid.uuid4())
    await send_to_bot("question", type=type, uid=uid, data=kwargs)

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

    r = replies[uid]
    del replies[uid]

    if r["state"] == "Failed":
        raise FailedException(source="Gearbot")
    if r["state"] == "Unauthorized":
        raise UnauthorizedException(source="User")
    if r["state"] == "Bad Request":
        raise BadRequestException(source="User", errors=r["errors"])

    return r["reply"]
