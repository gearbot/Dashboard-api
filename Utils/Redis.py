redis_link = None
import aioredis

# Index List:
# 0 - General Dashboard
# 1 - Security Related Items
# 2 - Crowdin Link

async def get_redis(db_index: int):
    global redis_link
    if redis_link is None:
        redis_link = await aioredis.create_redis_pool(
            ("localhost", 6379), 
            encoding="utf-8", 
            db=db_index,
            maxsize=2 # size 2: one send, one receive
        )
    return redis_link