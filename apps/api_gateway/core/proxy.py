import time
from typing import Any, cast

from fastapi import HTTPException, Request, Response
import httpx


from collections.abc import Mapping

from loguru import logger

from apps.api_gateway.core.proxy_types import ForwardRequestParams
from apps.api_gateway.core.settings import HOP_BY_HOP_HEADERS

log = logger.bind(service="api_gateway", component="proxy")

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

def calculate_duration_ms(start_time: float) -> float:
    return round((time.perf_counter() - start_time) * 1000, 2)

def log_proxy_error(exc: Exception, params: ForwardRequestParams, start_time: float) -> None:
    duration_ms = calculate_duration_ms(start_time)

    log.bind(
        event="proxy_upstream_error",
        duration_ms=duration_ms,
        upstream_status=None,
        path=params.path,
        method=params.method.value,
    ).warning("proxy_upstream_error error_type={error_type}", error_type=type(exc).__name__)
    
def log_proxy_success(
    *, params: ForwardRequestParams, duration_ms: float, upstream_status: int
) -> None:
    log.bind(
        event="proxy_upstream_success",
        duration_ms=duration_ms,
        upstream_status=upstream_status,
        path=params.path,
        method=params.method.value,
    ).info("proxy_upstream_success")


async def forward_request(
    request: Request,
    params: ForwardRequestParams,
) -> Response:
    start_time = time.perf_counter()

    forwarded_headers = filter_request_headers(request.headers)
    query_params = dict(request.query_params)
    url = f"{params.base_url.rstrip('/')}/{params.path.lstrip('/')}"

    # `request.body` es un método async, no el cuerpo: no pasarlo a `json=` (TypeError al serializar).
    # JSON explícito de la ruta → `params.body`; si no, bytes crudos con `await request.body()`.
    request_kwargs: dict[str, Any] = {
        "method": params.method.value,
        "url": url,
        "headers": forwarded_headers,
    }
    if query_params:
        request_kwargs["params"] = query_params
    if params.body is not None:
        request_kwargs["json"] = params.body
    else:
        body_bytes = await request.body()
        if body_bytes:
            request_kwargs["content"] = body_bytes

    try:
        client = cast(httpx.AsyncClient, request.app.state.http_client)
        resp = await client.request(**request_kwargs)
    except httpx.ConnectError as exc:
        log_proxy_error(exc, params, start_time)
        raise HTTPException(status_code=502, detail="Upstream unavailable") from exc
    except (httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout) as exc:
        log_proxy_error(exc, params, start_time)
        raise HTTPException(status_code=504, detail="Upstream timeout") from exc
    except httpx.HTTPError as exc:
        log_proxy_error(exc, params, start_time)
        raise HTTPException(status_code=502, detail="Gateway upstream error") from exc

    log_proxy_success(params=params, duration_ms=calculate_duration_ms(start_time), upstream_status=resp.status_code)

    return Response(
        content=resp.content,
        status_code=resp.status_code,
        headers=filter_response_headers(resp.headers),
    )