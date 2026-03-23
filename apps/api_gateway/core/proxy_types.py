from http import HTTPMethod
from typing import Any


class ForwardRequestParams:
  method: HTTPMethod
  base_url: str
  path: str
  body: dict[str, Any] | None = None
  headers: dict[str, str] | None = None
  query_params: dict[str, str] | None = None