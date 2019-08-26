import asyncio
from collections import namedtuple

from Utils import Redis
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
        todo = socket_by_subscription["stats"].copy()
        for websocket in todo:
            await stats_send(websocket)

async def stats_send(websocket):
    await websocket.send_json({
        "type": "stats",
        "content": await Redis.get_redis().hgetall("botstats")
    })


async def stats_end():
    stat_sender.cancel()


ChannelHandlers = namedtuple("ChannelHandlers", "start add end", defaults=(None, None, None))
handlers = {
    "stats": ChannelHandlers(stats_start, stats_send, stats_end)
}


async def subscribe(websocket, message):
    new = False
    channel = message["channel"]

    # create channel list if needed
    if channel not in socket_by_subscription:
        socket_by_subscription[channel] = list()
        new = True

    # subscribe and hit that bell for updates!
    socket_by_subscription[channel].append(websocket)
    websocket.active_subscriptions.append(channel)

    # NEW CHANNEL HYPE!!!
    if new and channel in handlers and handlers[channel].start is not None:
        await handlers[channel].start()

    if channel in handlers and handlers[channel].add is not None:
        await handlers[channel].add(websocket)


async def unsubscribe(websocket, message):
    channel = message["channel"]

    # you're no longer interesting, unsubscribed
    socket_by_subscription[channel].remove(websocket)
    websocket.active_subscriptions.remove(channel)

    if len(socket_by_subscription[channel]) is 0:
        # we lost all our subscribers, better delete our channel and retire
        del socket_by_subscription[channel]
        await handlers[channel].end()
