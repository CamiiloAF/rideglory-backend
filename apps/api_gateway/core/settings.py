import os

VEHICLES_SERVICE_BASE_URL = os.getenv(
    "VEHICLES_SERVICE_BASE_URL", "http://localhost:8001"
)

# Timeouts (segundos)
HTTP_CONNECT_TIMEOUT = float(os.getenv("HTTP_CONNECT_TIMEOUT", "2.0"))
HTTP_READ_TIMEOUT = float(os.getenv("HTTP_READ_TIMEOUT", "5.0"))
HTTP_WRITE_TIMEOUT = float(os.getenv("HTTP_WRITE_TIMEOUT", "5.0"))
HTTP_POOL_TIMEOUT = float(os.getenv("HTTP_POOL_TIMEOUT", "2.0"))
# Pool limits
HTTP_MAX_CONNECTIONS = int(os.getenv("HTTP_MAX_CONNECTIONS", "100"))
HTTP_MAX_KEEPALIVE_CONNECTIONS = int(os.getenv("HTTP_MAX_KEEPALIVE_CONNECTIONS", "20"))

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_JSON = os.getenv("LOG_JSON", "false").lower() in ("1", "true", "yes")

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
    "content-length",
}
