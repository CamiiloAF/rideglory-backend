from typing import Any

import httpx
from fastapi.testclient import TestClient

from apps.api_gateway import main


class _FakeResponse:
    def __init__(
        self,
        status_code: int,
        content: bytes = b'{"status":"ok"}',
        headers: dict[str, str] | None = None,
    ) -> None:
        self.status_code = status_code
        self.content = content
        self.headers = headers or {"content-type": "application/json"}


class _FakeAsyncClient:
    def __init__(self, *args: Any, **kwargs: Any) -> None:
        self._raise_on_call = kwargs.pop("raise_on_call", False)

    async def __aenter__(self) -> "_FakeAsyncClient":
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> None:
        return None

    async def get(self, _url: str) -> _FakeResponse:
        return _FakeResponse(200, b'{"status":"ok"}')

    async def post(self, _url: str, json: dict[str, Any]) -> _FakeResponse:
        return _FakeResponse(
            201,
            content=(
                b'{"id":"veh-1","plate":"'
                + json["plate"].encode()
                + b'","brand":"'
                + json["brand"].encode()
                + b'"}'
            ),
        )


class _FailingAsyncClient(_FakeAsyncClient):
    async def get(self, _url: str) -> _FakeResponse:
        raise httpx.ConnectError("connection error")

    async def post(self, _url: str, json: dict[str, Any]) -> _FakeResponse:
        raise httpx.ConnectError("connection error")


def test_health_endpoint() -> None:
    client = TestClient(main.app)
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_services_health_aggregates_downstream(monkeypatch: Any) -> None:
    monkeypatch.setattr(main.httpx, "AsyncClient", _FakeAsyncClient)
    client = TestClient(main.app)

    response = client.get("/health/services")

    assert response.status_code == 200
    assert response.json()["status"] == "ok"
    assert response.json()["services"]["vehicles_service"]["status"] == "ok"


def test_create_vehicle_proxy_forwards_payload(monkeypatch: Any) -> None:
    monkeypatch.setattr(main.httpx, "AsyncClient", _FakeAsyncClient)
    client = TestClient(main.app)

    response = client.post(
        "/api/v1/vehicles",
        json={"plate": "ABC-123", "brand": "Mazda"},
    )

    assert response.status_code == 201
    assert response.json()["plate"] == "ABC-123"
    assert response.json()["brand"] == "Mazda"


def test_proxy_returns_502_if_downstream_unavailable(monkeypatch: Any) -> None:
    monkeypatch.setattr(main.httpx, "AsyncClient", _FailingAsyncClient)
    client = TestClient(main.app)

    response = client.post(
        "/api/v1/vehicles",
        json={"plate": "ABC-123", "brand": "Mazda"},
    )

    assert response.status_code == 502
