from dataclasses import dataclass
from http import HTTPMethod
from typing import Any


@dataclass(slots=True)
class ForwardRequestParams:
    """Parameters for forwarding a request to an upstream service."""

    method: HTTPMethod
    base_url: str
    path: str
    # dict (JSON-serializable) or Pydantic model (serialized via model_dump in proxy).
    body: Any | None = None
