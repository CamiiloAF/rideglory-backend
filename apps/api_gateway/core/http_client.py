from typing import Awaitable
import httpx

from apps.api_gateway.core.settings import HTTP_CONNECT_TIMEOUT, HTTP_MAX_CONNECTIONS, HTTP_MAX_KEEPALIVE_CONNECTIONS, HTTP_POOL_TIMEOUT, HTTP_READ_TIMEOUT, HTTP_WRITE_TIMEOUT

def build_http_client() -> httpx.AsyncClient:
    timeout = httpx.Timeout(
        connect=HTTP_CONNECT_TIMEOUT,
        read=HTTP_READ_TIMEOUT,
        write=HTTP_WRITE_TIMEOUT,
        pool=HTTP_POOL_TIMEOUT,
    )
    limits = httpx.Limits(
        max_connections=HTTP_MAX_CONNECTIONS,
        max_keepalive_connections=HTTP_MAX_KEEPALIVE_CONNECTIONS,
    )
    return httpx.AsyncClient(timeout=timeout, limits=limits)



def close_http_client(client: httpx.AsyncClient) -> Awaitable[None]:
    return client.aclose()