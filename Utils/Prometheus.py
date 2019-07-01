from time import time_ns

import prometheus_client as prom
from starlette.middleware.base import BaseHTTPMiddleware, Request
from starlette.responses import Response, JSONResponse

from Utils.Responses import unauthorized_response, failed_response, no_reply_response
from Utils.Errors import FailedException, NoReplyException, UnauthorizedException, BadRequestException

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

from Utils.Redis import get_ms_passed

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
        