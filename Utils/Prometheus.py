import asyncio
from time import time_ns, time

import prometheus_client as prom
from starlette.middleware.base import BaseHTTPMiddleware, Request
from starlette.responses import Response, JSONResponse

from Utils.Responses import unauthorized_response, failed_response, no_reply_response
from Utils.Errors import FailedException, NoReplyException, UnauthorizedException, BadRequestException
from Utils.Configuration import SESSION_TIMEOUT_LEN

API_REGISTRY = prom.REGISTRY

request_counter = prom.Counter(
    "total_requests",
    "Number of HTTP requests we have received",
    ["endpoint", "method"]
)

response_counter = prom.Counter(
    "total_responses",
    "Number of HTTP responses we have sent to clients",
    ["endpoint", "method", "response_code"]
)

error_counter = prom.Counter(
    "total_errors",
    "The number of errors we have gotten and from which area",
    ["source"]
)

active_sessions = prom.Gauge(
    "current_sessions",
    "Number of sessions that are currently signed in"
)

redis_message_count = prom.Counter(
    "redis_messages",
    "Number of messages we have processed through Redis",
    ["direction"]
)

bot_response_latency = prom.Histogram(
    "gearbot_response_latency",
    "Average response time of Gearbot to our requests"
)

api_response_latency = prom.Histogram(
    "api_response_latency",
    "Average response time the API has to user requests"
)

from Utils.Redis import get_ms_passed, get_redis


async def session_monitor():
    redis = await get_redis()
    while True:
        # Check if the set currently has any contents, O(1)
        if await redis.zcard("current_dash_sessions") != 0: 
            current_time = time()
            # Remove all sessions that are older, or as old, as our timeout length
            dead_sessions = await redis.zremrangebyscore(
                "current_dash_sessions",
                max = current_time - SESSION_TIMEOUT_LEN
            )

            if dead_sessions != None:
                active_sessions.dec(dead_sessions)

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

        path = request.url.path
        method = request.method

        request_counter.labels(path, method).inc()
        try:
            response: Response = await call_next(request)
        except Exception as error:
            # Generate the appropriate error response
            if isinstance(error, BadRequestException):
                response = failed_response
            elif isinstance(error, UnauthorizedException):
                response = unauthorized_response
            elif isinstance(error, NoReplyException):
                response = no_reply_response
            elif isinstance(error, BadRequestException):
                response = JSONResponse(dict(status="Bad request", errors=ex.errors), status_code=400)

            # Try and get the proper error root if we can
            if hasattr(error, "source"):
                error_counter.labels(error.source).inc()
            else:
                error_counter.labels(error.__class__.__name__).inc()
                raise

            # Pass the exact error and stacktrace through
            api_response_latency.observe(get_ms_passed(processing_start, time_ns()))
            return response

        response_counter.labels(path, method, response.status_code).inc()

        api_response_latency.observe(get_ms_passed(processing_start, time_ns()))
        return response
        