import asyncio
import time

from Utils.Configuration import API_LOCATION

base_buckets = dict()
bucket_wrappers = dict()
cleaner = None


class BucketWrapper:
    def __init__(self) -> None:
        self.bucket_by_route = dict()
        self.global_lock = asyncio.Event()
        self.globally_locked = False
        self.last_used = time.time()


class Bucket:
    def __init__(self) -> None:
        self._remaining = 1
        self._limit = 1
        self._sem = asyncio.Semaphore()
        self._scheduled_release = False
        self._release_delay = 10
        self.last_used = time.time()

    async def acquire(self):
        await self._sem.acquire()
        self._remaining -= 1

    def set_limits(self, headers):
        self._limit = int(headers["X-RateLimit-Limit"])
        remaining = int(headers["X-RateLimit-Remaining"])
        self._release_delay = headers["X-RateLimit-Reset-After"]
        while remaining > self._remaining:
            self._sem.release()  # we have more then we thought, release some
        while self._remaining < remaining:
            asyncio.ensure_future(self._sem.acquire())  # yikes, we used more then we thought, waste a few
        if not self._scheduled_release:
            self._scheduled_release = True
            asyncio.ensure_future(self._reset_after(float(headers["X-RateLimit-Reset-After"])))
        self.last_used = time.time()

    def _release(self):
        self._remaining += 1
        self._sem.release()

    async def _reset_after(self, delay):
        await asyncio.sleep(delay)
        while self._remaining < self._limit:
            self._release()
        self._scheduled_release = False

    def clone(self):
        bucket = Bucket()
        bucket._remaining = self._remaining
        bucket._limit = self._limit
        return bucket


async def make_request(pool, method, route, wrapper_identifier="default", *route_args, **request_kwargs):
    if wrapper_identifier not in bucket_wrappers:
        bucket_wrappers[wrapper_identifier] = BucketWrapper()
    wrapper = bucket_wrappers[wrapper_identifier]
    wrapper.last_used = time.time()

    if wrapper.globally_locked:  # we're hitting global limits, wait for them to clear first
        await wrapper.global_lock.wait()

    discovered = route in wrapper.bucket_by_route
    if not discovered:
        wrapper.bucket_by_route[
            route] = Bucket()  # temp give it a 1-1-10 bucket so to block things while we discover the route

    bucket = wrapper.bucket_by_route[route]
    await bucket.acquire()

    async with getattr(pool, method)(API_LOCATION + route.format(*route_args), **request_kwargs) as response:
        # handle rate limits
        if response.status == 429:
            print("RATE LIMIT HIT!")
            info = await response.json()
            if info["global"]:
                wrapper.globally_locked = True
                await asyncio.sleep(info["retry_after"] / 1000)
                wrapper.globally_locked = False
                wrapper.global_lock.set()
                await asyncio.sleep(0.1)  # not 100% sure this is needed
                wrapper.global_lock.clear()
            else:
                # not global, our bucket must be wrong
                if not discovered:
                    bucket_id = route.headers["X-RateLimit-Bucket"]
                    if bucket_id in base_buckets:
                        # we already had a bucket, use it for the route in the future
                        wrapper.bucket_by_route[route] = base_buckets[bucket_id].clone()
                        wrapper.bucket_by_route[route].set_limitse(response.headers)
                    else:
                        bucket.set_limits(response.headers)
                        base_buckets[bucket_id] = bucket.clone()
                else:
                    bucket.set_limits(response.headers)
                await asyncio.sleep(info["retry_after"] / 1000)
                return await make_request(pool, method, route, *route_args, **request_kwargs)
        else:
            if not discovered:
                bucket_id = response.headers["X-RateLimit-Bucket"]
                if bucket_id in base_buckets:
                    # we already had a bucket, use it for the route in the future
                    wrapper.bucket_by_route[route] = base_buckets[bucket_id].clone()
                    wrapper.bucket_by_route[route].set_limits(response.headers)
                else:
                    base_buckets[bucket_id] = bucket.clone()
            # if we just discovered it, still set limits on this bucket in case we have others waiting on this undiscovered bucket
            bucket.set_limits(response.headers)
        return await response.json()


async def cleaner_task():
    global bucket_wrappers
    while True:
        await asyncio.sleep(900)
        limit = time.time() - 600
        bucket_wrappers = {i: wrapper for i, wrapper in bucket_wrappers.items() if wrapper.last_used > limit}
        for bucket_wrapper in bucket_wrappers.values():
            bucket_wrapper.bucket_by_route = {i: bucket for i, bucket in bucket_wrapper.bucket_by_route.items() if bucket.last_used > limit}
