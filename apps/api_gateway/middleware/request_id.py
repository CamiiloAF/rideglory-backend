from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from apps.api_gateway.core.request_context import (
    generate_request_id,
    reset_request_id,
    set_request_id,
)

HEADER_NAME = "X-Request-ID"


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        rid = generate_request_id()

        token = set_request_id(rid)

        try:
            response = await call_next(request)
            response.headers[HEADER_NAME] = rid
            return response
        finally:
            reset_request_id(token)