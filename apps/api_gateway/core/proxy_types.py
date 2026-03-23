from dataclasses import dataclass
from http import HTTPMethod
from typing import Any

@dataclass(slots=True)
class ForwardRequestParams:
  method: HTTPMethod
  base_url: str
  path: str
  body: dict[str, Any] | None = None