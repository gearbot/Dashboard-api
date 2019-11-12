import asyncio

bucket_by_route = dict()
bucket_by_id = dict()
global_lock = asyncio.Event()
globally_locked = False


class Bucket:
    def __init__(self) -> None:
        self._remaining = 1
        self._limit = 1
        self._sem = asyncio.Semaphore()
        self._scheduled_release = False
        self._release_delay = 10

    async def acquire(self):
        await self._sem.acquire()
        self._remaining -= 1

    def set_limits(self, headers):
        self._limit = int(headers["X-RateLimit-Limit"])
        remaining = int(headers["X-RateLimit-Remaining"])
        self._release_delay = headers["X-RateLimit-Reset-After"]
        while remaining > self._remaining:
            self._sem.release() # we have more then we thought, release some
        while self._remaining < remaining:
            asyncio.ensure_future(self._sem.acquire()) # yikes, we used more then we thought, waste a few
        if not self._scheduled_release:
            self._scheduled_release = True
            asyncio.ensure_future(self._reset_after(float(headers["X-RateLimit-Reset-After"])))

    def _release(self):
        self._remaining += 1
        self._sem.release()

    async def _reset_after(self, delay):
        await asyncio.sleep(delay)
        while self._remaining < self._limit:
            self._release()
        self._scheduled_release = False


async def make_request(pool, method, route, *route_args, **request_kwargs):
    global globally_locked
    if globally_locked:  # we're hitting global limits, wait for them to clear first
        await global_lock.wait()

    discovered = route in bucket_by_route
    if not discovered:
        bucket_by_route[route] = Bucket()  # temp give it a 1-1-10 bucket so to block things while we discover the route

    bucket = bucket_by_route[route]
    await bucket.acquire()

    async with getattr(pool, method)(route.format(*route_args), **request_kwargs) as response:
        # handle rate limits
        if response.status == 429:
            print("RATE LIMIT HIT!")
            info = await response.json()
            if info["global"]:
                globally_locked = True
                await asyncio.sleep(info["retry_after"] / 1000)
                globally_locked = False
                global_lock.set()
                await asyncio.sleep(0.1) # not 100% sure this is needed
                global_lock.clear()
            else:
                #not global, our bucket must be wrong
                if not discovered:
                    bucket_id = route.headers["X-RateLimit-Bucket"]
                    if bucket_id in bucket_by_id:
                        # we already had a bucket, use it for the route in the future
                        bucket_by_route[route] = bucket_by_id[bucket_by_id]
                        bucket_by_route[route].set_limitse(response.headers)
                    else:
                        bucket_by_id[bucket_id] = bucket
                bucket.set_limits(response.headers)
                await asyncio.sleep(info["retry_after"] / 1000)
                return await make_request(pool, method, route, *route_args, **request_kwargs)
        else:
            if not discovered:
                bucket_id = response.headers["X-RateLimit-Bucket"]
                if bucket_id in bucket_by_id:
                    # we already had a bucket, use it for the route in the future
                    bucket_by_route[route] = bucket_by_id[bucket_by_id]
                    bucket_by_route[route].set_limits(response.headers)
                else:
                    bucket_by_id[bucket_id] = bucket
            bucket.set_limits(response.headers) # if we just discovered it, still set limits on this bucket in case we have others waiting on this undiscovered bucket
        return await response.json()

