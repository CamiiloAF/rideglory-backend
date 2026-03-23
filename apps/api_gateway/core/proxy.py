import os
from typing import Any

from fastapi import HTTPException, Request, Response
import httpx


from collections.abc import Mapping

from apps.api_gateway.core.proxy_types import ForwardRequestParams

HOP_BY_HOP_HEADERS = {
    "connection",
    "keep-alive",
    "proxy-authenticate",
    "proxy-authorization",
    "te",
    "trailers",
    "transfer-encoding",
    "upgrade",
    "host",
}

def filter_request_headers(headers: Mapping[str, str]) -> dict[str, str]:
    return {
        key: value
        for key, value in headers.items()
        if key.lower() not in HOP_BY_HOP_HEADERS
    }

def filter_response_headers(headers: Mapping[str, str]) -> dict[str, str]:
    return {
        key: value
        for key, value in headers.items()
        if key.lower() not in HOP_BY_HOP_HEADERS
    }

async def forward_request(
   request: Request,
   params: ForwardRequestParams
) -> Response:
    forwarded_headers = filter_request_headers(request.headers)
    query_params = dict(request.query_params)
    url = f"{params.base_url.rstrip('/')}/{params.path.lstrip('/')}"

    try:
        client = request.app.state.http_client
        resp = await client.request(request.method, url, json=request.body)
    except httpx.ConnectError as exc:
        raise HTTPException(status_code=502, detail="Upstream unavailable") from exc
    except (httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout) as exc:
        raise HTTPException(status_code=504, detail="Upstream timeout") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Gateway upstream error") from exc

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers=filter_response_headers(resp.headers),
    )