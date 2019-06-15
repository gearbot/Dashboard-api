redis_link = None


async def get_redis():
    global redis_link
    if redis_link is None:
        redis_link = await aioredis.create_redis_pool(("localhost", 6379), encoding="utf-8", db=0,
                                                      maxsize=2)  # size 2: one send, one receive
    return redis_link