import os
from typing import Any

from fastapi import HTTPException, Response
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
   request: ForwardRequestParams
) -> Response:
    forwarded_headers = filter_request_headers(request.headers)
    url = f"{request.base_url}{request.path}"

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.request(request.method, url, json=request.body)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail=f"Service unavailable: {exc}") from exc
    
    return Response(
        content=resp.content,
        status_code=resp.status_code,
        media_type=resp.headers.get("content-type", "application/json"),
        headers=filter_response_headers(resp.headers),
    )