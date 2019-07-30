import asyncio
from time import time_ns, time

import prometheus_client as prom
from starlette.middleware.base import BaseHTTPMiddleware, Request
from starlette.responses import Response, JSONResponse

from Utils.Responses import unauthorized_response, failed_response, no_reply_response
from Utils.Errors import NoReplyException, UnauthorizedException, BadRequestException, FailedException

request_counter = prom.Counter(
    "dashapi_total_requests",
    "Number of HTTP requests we have received",
    ["endpoint", "method"]
)

response_counter = prom.Counter(
    "dashapi_total_responses",
    "Number of HTTP responses we have sent to clients",
    ["endpoint", "method", "response_code"]
)

error_counter = prom.Counter(
    "dashapi_total_errors",
    "The number of errors we have gotten and from which area",
    ["source"]
)

active_sessions = prom.Gauge(
    "dashapi_current_sessions",
    "Number of sessions that are currently signed in",
    multiprocess_mode="livesum"
)

redis_message_count = prom.Counter(
    "dashapi_redis_messages",
    "Number of messages we have processed through Redis",
    ["direction"]
)

bot_response_latency = prom.Histogram(
    "dashapi_gearbot_response_latency",
    "Average response time of Gearbot to our requests"
)

api_response_latency = prom.Histogram(
    "dashapi_api_response_latency",
    "Average response time the API has to user requests"
)

from Utils.Redis import get_ms_passed, get_redis


async def session_monitor():
    redis = await get_redis()

    # Restore sessions after a restart from Redis
    current_sessions = await redis.zcard("current_dash_sessions")
    if current_sessions != None:
        active_sessions.set(current_sessions)

    while True:
        # Check if the set currently has any contents, O(1)
        current_sessions = await redis.zcard("current_dash_sessions")
        if current_sessions != 0:
            current_time = time()
            # Remove all sessions that are older, or as old, as our timeout length
            dead_sessions = await redis.zremrangebyscore(
                "current_dash_sessions",
                max=current_time - (2 * 60 * 60)  # Max "active session" length is 2 hours
            )

            if dead_sessions != None:
                active_sessions.set(current_sessions - dead_sessions)

        await asyncio.sleep(4.9)


async def notice_session(user_id, was_add: bool):
    redis = await get_redis()

    if was_add:
        current_time = time()
        await redis.zadd("current_dash_sessions", current_time, user_id)
        active_sessions.inc()
    else:
        await redis.zrem("current_dash_sessions", user_id)
        active_sessions.dec()

    return


class PromStatsMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        processing_start = time_ns()

        path: str = request.url.path
        method = request.method

        is_uncounted_request = False

        # Filter out guild IDs, metric requests, and keepalives
        if any(char.isdigit() for char in path):
            path_parts = [part for i, part in enumerate(path.split("/")) if i != 3]
            path: str = "/".join(path_parts)

            # Clean up the exact config fields
            if "config" in path:
                path = "/".join(path_parts[:-1])

            request_counter.labels(path, method).inc()

        # Normalize request paths
        elif path.endswith("/"):
            path = path[:-1]
            request_counter.labels(path, method).inc()
        # Ignore metric endpoint requests
        elif path.endswith("/metrics"):
            is_uncounted_request = True
        # Ignore keepalive
        elif path.endswith("/spinning"):
            is_uncounted_request = True
        else:
            request_counter.labels(path, method).inc()

        try:
            response: Response = await call_next(request)
        except Exception as error:
            # Generate the appropriate error response
            if isinstance(error, FailedException):
                response = failed_response
            elif isinstance(error, UnauthorizedException):
                response = unauthorized_response
            elif isinstance(error, NoReplyException):
                response = no_reply_response
            elif isinstance(error, BadRequestException):
                response = JSONResponse(dict(status="Bad request", errors=error.errors), status_code=400)
            else:
                response=JSONResponse(dict(status="Unknown error occurred"), status_code=500)

            # Try and get the proper error root if we can
            if hasattr(error, "source"):
                error_counter.labels(error.source).inc()
            else:
                error_counter.labels(error.__class__.__name__).inc()
                raise

            # Pass the exact error and stacktrace through
            api_response_latency.observe(get_ms_passed(processing_start, time_ns()))
            return response

        # Don't count metric requests
        if not is_uncounted_request:
            response_counter.labels(path, method, response.status_code).inc()
            api_response_latency.observe(get_ms_passed(processing_start, time_ns()))

        return response
