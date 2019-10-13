import asyncio
import json
from collections import namedtuple

from aiohttp import client

from Utils import Redis
from Utils.Configuration import API_LOCATION
from Utils.Perms import DASH_PERMS
from routers.websocket import socket_by_subscription

# stats handlers
stat_sender = None


async def stats_start():
    global stat_sender
    stat_sender = asyncio.create_task(stats_sender())
    asyncio.ensure_future(stat_sender)


async def stats_sender():
    while True:
        await asyncio.sleep(10)
        await send_to_subscribers("stats", **await Redis.get_redis().hgetall("botstats"))


async def stats_send(websocket, subkey):
    global stat_sender
    if stat_sender.cancelled() or stat_sender.done():
        stat_sender = asyncio.create_task(stats_sender())
    await websocket.send_json({
        "type": "stats",
        "content": await Redis.get_redis().hgetall("botstats")
    })


async def stats_end():
    stat_sender.cancel()


async def guilds_start(websocket, subkey):
    # tell the bot to send this user's guilds
    await Redis.send_to_bot("user_guilds", user_id=subkey)

    # get non gearbot servers
    headers = {
        "Authorization": f"Bearer {websocket.auth_info.user.api_token}"
    }

    async with client.ClientSession() as session_pool:

        async with session_pool.get(f"{API_LOCATION}/users/@me/guilds", headers=headers) as resp:
            guild_list = await resp.json()
            if not isinstance(guild_list, list):
                from Utils.Auth import deauth_user
                await deauth_user(websocket.auth_info.user.id)
                await websocket.auth_info.delete()
                return False
            to_send = dict()
            for guild in guild_list:
                if guild["owner"] or guild["permissions"] & 32 == 32:
                    to_send[str(guild["id"])] = {
                        "id": str(guild["id"]),
                        "name": str(guild["name"]),
                        "icon": guild["icon"]
                    }
            await websocket.send_json({
                "type": "guilds",
                "content": {
                    "type": "all_guilds",
                    "guilds": to_send
                }
            })

    await session_pool.close()


def is_last_subkey(channel, subkey):
    for holder in socket_by_subscription[channel]:
        if holder.subkey == subkey:
            return False
    return True


async def guilds_end(websocket, subkey):
    if is_last_subkey("guilds", subkey):
        await Redis.send_to_bot("user_guilds_end", user_id=subkey)


async def always_allowed(info, subkey):
    return True


async def user_id_check(info, subkey):
    return info is not None and subkey == str(info.user_id)


def needs_perm(perm):
    async def actual_checker(info, subkey):
        if info is None:
            return False
        user_perms = await Redis.ask_the_bot("guild_user_perms", guild_id=subkey, user_id=info.user_id)
        return (user_perms & perm) == perm

    return actual_checker


async def guild_info_start(websocket, subkey):
    await Redis.send_to_bot("guild_info_watch", guild_id=subkey, user_id=websocket.auth_info.user_id)


async def guild_info_end(websocket, subkey):
    await Redis.send_to_bot("guild_info_watch_end", guild_id=subkey, user_id=websocket.auth_info.user_id)


ChannelHandlers = namedtuple("ChannelHandlers", "allowed start add remove end")
handlers = {
    "stats": ChannelHandlers(always_allowed, stats_start, stats_send, None, stats_end),
    "guilds": ChannelHandlers(user_id_check, None, guilds_start, guilds_end, None),
    "guild_info": ChannelHandlers(needs_perm(DASH_PERMS.ACCESS), None, guild_info_start, guild_info_end, None),
    "guild_settings": ChannelHandlers(needs_perm(DASH_PERMS.VIEW_CONFIG), None, None, None, None)
    # TODO: acutally make this do something
}


async def subscribe(websocket, message):
    new = False
    channel = message["channel"]

    if channel not in handlers:
        await websocket.send_json(dict(type="error", content="Unknown channel!"))
        return
    handler = handlers[channel]
    subkey = message.get("subkey", None)
    if not await handler.allowed(getattr(websocket, "auth_info", None), subkey):
        await websocket.send_json(dict(type="error", content="You are not allowed to subscribe to this channel!"))
        return

    # create channel list if needed
    if channel not in socket_by_subscription:
        socket_by_subscription[channel] = list()
        new = True

    # subscribe and hit that bell for updates!
    if channel not in websocket.active_subscriptions:
        socket_by_subscription[channel].append(websocket)
        websocket.active_subscriptions[channel] = str(subkey)
    else:
        websocket.send_json({
            "type": "error",
            "message": f"You are already subscribed to {channel}"
        })

    # NEW CHANNEL HYPE!!!
    if new and handlers[channel].start is not None:
        await handlers[channel].start()

    if handlers[channel].add is not None:
        await handlers[channel].add(websocket, subkey)


async def unsubscribe(websocket, message):
    channel = message["channel"]
    subkey = message.get("subkey", None)

    # you're no longer interesting, unsubscribed

    socket_by_subscription[channel].remove(websocket)
    if handlers[channel].remove is not None:
        await handlers[channel].remove(websocket, websocket.active_subscriptions[channel])
    del websocket.active_subscriptions[channel]

    if len(socket_by_subscription[channel]) is 0:
        # we lost all our subscribers, better delete our channel and retire
        del socket_by_subscription[channel]
        if handlers[channel].end is not None:
            await handlers[channel].end()


async def send_to_subscribers(channel, subkey=None, uid=None, **kwargs):
    if channel in socket_by_subscription:
        for socket in socket_by_subscription[channel]:
            auth_info = getattr(socket, "auth_info", None)
            if socket.active_subscriptions[channel] == str(subkey) and (uid is None or (auth_info is not None and auth_info.user_id == int(uid))):
                await socket.send_json(dict(type=channel, content=kwargs))
