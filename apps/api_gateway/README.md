# API Gateway - Guia para mejorar `forward_request`

Este documento explica como evolucionar el proxy actual del API Gateway para que sea mas robusto, mantenible y listo para produccion.

La idea es que avances por iteraciones pequenas y entendiendo el por que de cada cambio.

**Logs (Loguru) y Docker (stdout/stderr):** ver [README_LOGGING.md](./README_LOGGING.md).

**Request ID, contexto async, unificación con Uvicorn y campos del proxy:** ver [README_REQUEST_ID_AND_LOG_UNIFICATION.md](./README_REQUEST_ID_AND_LOG_UNIFICATION.md).

## 1) Estado actual (resumen)

Hoy `forward_request`:

- crea un `httpx.AsyncClient` por cada request,
- solo soporta `json_body`,
- maneja errores con un `except httpx.HTTPError` generico,
- no filtra headers de request/response,
- no propaga `query params`,
- fija `content-type` por defecto a JSON.

Funciona para un MVP, pero en trafico real puede generar latencia, respuestas inconsistentes y poca observabilidad.

## 2) Objetivo de la version mejorada

Construir un `forward_request` que:

- reutilice conexiones HTTP (pool),
- tenga timeouts bien definidos por fase,
- reenvie correctamente headers, params y body,
- traduzca errores de red a codigos HTTP adecuados (502/504),
- deje trazabilidad (logs con request id y duracion),
- sea facil de testear.

## 3) Conceptos clave (explicados para junior)

### 3.1 `AsyncClient` compartido y pool de conexiones

Si creas un cliente por request, cada llamada vuelve a abrir conexiones TCP/TLS. Eso es caro.

Si usas un cliente compartido (en startup/shutdown de FastAPI), `httpx` reusa conexiones y mejora performance.

### 3.2 Timeouts por etapa

No es lo mismo:

- tardar en conectar (`connect` timeout),
- tardar en enviar body (`write` timeout),
- tardar en recibir respuesta (`read` timeout),
- quedarse esperando una conexion libre del pool (`pool` timeout).

Separarlos ayuda a diagnosticar y responder mejor.

### 3.3 502 vs 504

- `502 Bad Gateway`: el gateway no puede hablar bien con upstream (caido, DNS, reset de conexion, etc.).
- `504 Gateway Timeout`: el upstream no respondio a tiempo.

### 3.4 Hop-by-hop headers

Headers como `connection`, `host`, `transfer-encoding` pertenecen al tramo actual de red y no deben reenviarse como proxy.

### 3.5 Idempotencia y retries

Puedes reintentar operaciones idempotentes (`GET`, `HEAD`) con menos riesgo.
No reintentes `POST` por defecto porque puedes duplicar operaciones.

## 4) Propuesta tecnica (arquitectura simple)

## 4.1 Archivos sugeridos

- `apps/api_gateway/core/settings.py`
- `apps/api_gateway/core/http_client.py`
- `apps/api_gateway/core/proxy.py` (refactor)
- `apps/api_gateway/routes/vehicles.py` (ajustes minimos)
- `apps/api_gateway/tests/test_proxy.py` (nuevo)

## 4.2 Settings centralizados

Define variables de entorno con defaults razonables:

- `VEHICLES_SERVICE_BASE_URL`
- `HTTP_CONNECT_TIMEOUT`
- `HTTP_READ_TIMEOUT`
- `HTTP_WRITE_TIMEOUT`
- `HTTP_POOL_TIMEOUT`
- `HTTP_MAX_CONNECTIONS`
- `HTTP_MAX_KEEPALIVE_CONNECTIONS`

Beneficio: no hardcodear valores sensibles a entorno.

## 4.3 Cliente HTTP compartido

Crear en startup:

- `Timeout(connect=..., read=..., write=..., pool=...)`
- `Limits(max_connections=..., max_keepalive_connections=...)`
- `app.state.http_client = httpx.AsyncClient(timeout=timeout, limits=limits)`

Cerrar en shutdown:

- `await app.state.http_client.aclose()`

## 4.4 Rediseño de `forward_request`

En lugar de una funcion limitada a `json_body`, la idea es soportar:

- metodo (`GET`, `POST`, etc.),
- path,
- query params,
- headers filtrados,
- body (`json` o `content`),
- timeout opcional por request (override).

Tambien:

- construir URL con cuidado de slashes,
- tomar el `http_client` compartido,
- mapear excepciones por tipo,
- devolver response con headers permitidos.

## 5) Plan de implementacion paso a paso

## Paso 1 - Configuracion

1. Crea `settings.py`.
2. Mueve `VEHICLES_SERVICE_BASE_URL` ahi.
3. Agrega constantes de timeout/limits.

Validacion:

- la app levanta sin variables de entorno configuradas.

## Paso 2 - HTTP client compartido

1. Agrega startup/shutdown en `main.py`.
2. Inicializa y guarda `AsyncClient` en `app.state`.
3. Usa ese cliente en `/health/services` (no crees cliente nuevo ahi).

Validacion:

- endpoint de health sigue funcionando.

## Paso 3 - Helpers de headers

En `proxy.py`, crea:

- `HOP_BY_HOP_HEADERS = {...}`
- `filter_request_headers(...)`
- `filter_response_headers(...)`

Validacion:

- `host`, `connection`, `transfer-encoding` no se reenvian.

## Paso 4 - Forward request v2

1. Refactoriza la firma para aceptar `Request` de FastAPI o parametros explicitos de headers/params/body.
2. Reenvia query params.
3. Reenvia body apropiadamente (`json` si es JSON; `content` para raw).
4. Aplica filtrado de headers.

Validacion:

- `GET /api/v1/vehicles/{user_id}?page=1` llega a upstream con query.

## Paso 5 - Manejo de errores correcto

Mapeo recomendado:

- `httpx.ConnectError` -> 502 (`Upstream unavailable`)
- `httpx.ReadTimeout` / `httpx.WriteTimeout` / `httpx.PoolTimeout` -> 504 (`Upstream timeout`)
- `httpx.HTTPError` -> 502

Validacion:

- simulando timeout, la API responde 504.

## Paso 6 - Logging estructurado

Loguea por request:

- metodo,
- URL upstream,
- status,
- duracion en ms,
- request-id / correlation-id.

Tip:

- no loguees payloads sensibles completos.

Validacion:

- revisa logs y confirma que puedes seguir una request end-to-end.

## Paso 7 - Tests

Casos minimos a cubrir:

1. Propaga metodo/path/params.
2. Propaga JSON body en POST.
3. Filtra hop-by-hop headers.
4. Mapea `ConnectError` a 502.
5. Mapea timeout a 504.
6. Preserva `status_code` y `content-type` del upstream.

Herramientas:

- `pytest`
- `httpx.MockTransport` o monkeypatch del cliente.

## Paso 8 - Retry (opcional, iteracion 2)

Implementa solo para `GET`/`HEAD`:

- 1-2 reintentos maximo,
- backoff corto (100ms -> 250ms),
- solo en errores transitorios (timeout/connect).

No aplicar a `POST` por defecto.

## 5.1) Paso a paso hands-on (comandos + cambios exactos)

Esta seccion es la version "hazlo conmigo". Sigue cada bloque en orden.

## Bloque A - Preparacion

1. Crea una rama para trabajar seguro:

```bash
git checkout -b feat/api-gateway-forward-request-v2
```

1. Levanta tu entorno actual y guarda un baseline:

```bash
pytest -q
```

Si falla algo aqui, anotalo. Te sirve para saber si rompiste algo luego o ya venia roto.

## Bloque B - Commit 1 (settings + cliente compartido)

Objetivo: dejar de crear `AsyncClient` por request.

1. Crea `apps/api_gateway/core/settings.py` con constantes:

- URL base de vehicles
- timeouts (connect/read/write/pool)
- limits de conexiones

1. Crea `apps/api_gateway/core/**http_client.py**` con dos funciones:

- `build_http_client() -> httpx.AsyncClient`
- `close_http_client(client: httpx.AsyncClient) -> Awaitable[None]`

1. En `main.py`:

- importa `build_http_client` y `close_http_client`,
- agrega eventos startup/shutdown,
- guarda cliente en `app.state.http_client`,
- en `/health/services` usa ese cliente en lugar de crear uno nuevo.

Validacion manual:

```bash
uvicorn apps.api_gateway.main:app --reload
curl -s http://127.0.0.1:8000/health/services
```

Cuando pase, crea commit:

```bash
git add apps/api_gateway/core/settings.py apps/api_gateway/core/http_client.py apps/api_gateway/main.py
git commit -m "Add shared HTTP client lifecycle for API gateway"
```

## Bloque C - Commit 2 (forward_request v2)

Objetivo: proxy mas fiel y robusto.

1. Refactoriza `apps/api_gateway/core/proxy.py`:

- agrega set `HOP_BY_HOP_HEADERS`,
- agrega `filter_request_headers`,
- agrega `filter_response_headers`,
- refactoriza `forward_request` para aceptar `Request`,
- propaga `query params`,
- soporta body JSON y raw,
- mapea excepciones de `httpx` a 502/504.

1. Ajusta `routes/vehicles.py`:

- endpoints reciben `request: Request`,
- pasan request a `forward_request`.

Validacion manual:

```bash
curl -i "http://127.0.0.1:8000/api/v1/vehicles/abc?page=1"
curl -i -X POST "http://127.0.0.1:8000/api/v1/vehicles" -H "content-type: application/json" -d '{"brand":"Mazda"}'
```

Commit:

```bash
git add apps/api_gateway/core/proxy.py apps/api_gateway/routes/vehicles.py
git commit -m "Refactor gateway proxy to forward params, headers, and map upstream errors"
```

## Bloque D - Commit 3 (tests del proxy)

Objetivo: cubrir los casos importantes antes de seguir.

1. Crea `apps/api_gateway/tests/test_proxy.py`.
2. Casos minimos que debes implementar:

- reenvio de query params,
- reenvio de JSON body,
- filtrado de hop-by-hop headers,
- `ConnectError -> 502`,
- timeout -> 504,
- preserva status y content-type.

1. Ejecuta:

```bash
pytest apps/api_gateway/tests/test_proxy.py -q
```

1. Si todo verde, commit:

```bash
git add apps/api_gateway/tests/test_proxy.py
git commit -m "Add proxy tests for forwarding behavior and upstream failures"
```

## Bloque E - Commit 4 (logging + retry opcional)

Objetivo: observabilidad y resiliencia controlada.

1. Logging:

- usa `logging.getLogger("api_gateway.proxy")`,
- registra metodo, url, status, duracion, request-id.

1. Retry opcional (solo GET/HEAD):

- max 2 intentos,
- backoff corto (ejemplo: 100ms y 250ms),
- solo ante timeout/connect.

1. Ejecuta test suite:

```bash
pytest -q
```

1. Commit:

```bash
git add apps/api_gateway/core/proxy.py
git commit -m "Add structured proxy logging and safe retries for idempotent requests"
```

## Bloque F - Verificacion final (definicion de terminado)

Marca task como terminada solo si:

- no hay `AsyncClient(...)` dentro de `forward_request`,
- `health/services` usa cliente compartido,
- errores de red devuelven 502/504 correctamente,
- params y headers llegan bien al upstream,
- tests de proxy pasan,
- logs de proxy incluyen duracion y request id.

## 5.2) Guia ultra detallada (archivo por archivo)

Esta seccion es para ejecutar sin dudas. Aqui tienes que escribir en cada archivo, en que orden y que comprobar en cada punto.

## Paso 1 detallado - `core/settings.py`

Ruta: `apps/api_gateway/core/settings.py`

Que debes crear:

```python
import os

VEHICLES_SERVICE_BASE_URL = os.getenv("VEHICLES_SERVICE_BASE_URL", "http://localhost:8001")

HTTP_CONNECT_TIMEOUT = float(os.getenv("HTTP_CONNECT_TIMEOUT", "2.0"))
HTTP_READ_TIMEOUT = float(os.getenv("HTTP_READ_TIMEOUT", "5.0"))
HTTP_WRITE_TIMEOUT = float(os.getenv("HTTP_WRITE_TIMEOUT", "5.0"))
HTTP_POOL_TIMEOUT = float(os.getenv("HTTP_POOL_TIMEOUT", "2.0"))

HTTP_MAX_CONNECTIONS = int(os.getenv("HTTP_MAX_CONNECTIONS", "100"))
HTTP_MAX_KEEPALIVE_CONNECTIONS = int(os.getenv("HTTP_MAX_KEEPALIVE_CONNECTIONS", "20"))
```

Por que asi:

- `float/int` desde `os.getenv` evita comparar strings por error.
- defaults te permiten correr en local sin configurar nada.

Como validar:

- levanta app sin variables y confirma que no truena importando settings.

## Paso 2 detallado - `core/http_client.py`

Ruta: `apps/api_gateway/core/http_client.py`

Que debes crear:

```python
import httpx

from apps.api_gateway.core.settings import (
    HTTP_CONNECT_TIMEOUT,
    HTTP_MAX_CONNECTIONS,
    HTTP_MAX_KEEPALIVE_CONNECTIONS,
    HTTP_POOL_TIMEOUT,
    HTTP_READ_TIMEOUT,
    HTTP_WRITE_TIMEOUT,
)


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


async def close_http_client(client: httpx.AsyncClient) -> None:
    await client.aclose()
```

Errores tipicos:

- olvidar `pool` timeout,
- usar valores demasiado bajos y provocar 504 falsos.

## Paso 3 detallado - `main.py` con lifecycle

Que debes cambiar en `apps/api_gateway/main.py`:

1. importar settings y cliente:

```python
from apps.api_gateway.core.http_client import build_http_client, close_http_client
from apps.api_gateway.core.settings import VEHICLES_SERVICE_BASE_URL
```

1. crear startup/shutdown:

```python
@app.on_event("startup")
async def on_startup() -> None:
    app.state.http_client = build_http_client()


@app.on_event("shutdown")
async def on_shutdown() -> None:
    await close_http_client(app.state.http_client)
```

1. health usando cliente compartido:

```python
response = await app.state.http_client.get(f"{VEHICLES_SERVICE_BASE_URL}/health")
```

Check rapido:

- inicia uvicorn,
- pega a `/health/services`,
- para servidor con Ctrl+C y confirma que no lanza warning de conexiones abiertas.

## Paso 4 detallado - `core/proxy.py` version robusta

Objetivo: mover de "proxy minimo" a "proxy util en produccion".

### 4.1 Imports y constantes

Debes tener imports de:

- `logging`,
- `time`,
- `httpx`,
- `Request`, `Response`, `HTTPException`.

Constante de hop-by-hop:

```python
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
```

### 4.2 Helpers de filtrado

Implementa dos helpers:

```python
def filter_request_headers(headers: dict[str, str]) -> dict[str, str]:
    return {k: v for k, v in headers.items() if k.lower() not in HOP_BY_HOP_HEADERS}


def filter_response_headers(headers: dict[str, str]) -> dict[str, str]:
    return {k: v for k, v in headers.items() if k.lower() not in HOP_BY_HOP_HEADERS}
```

Nota:

- FastAPI entrega headers case-insensitive, pero filtra con `k.lower()` siempre.

### 4.3 Firma recomendada de `forward_request`

Firma sugerida:

```python
async def forward_request(
    request: Request,
    method: str,
    base_url: str,
    path: str,
    json_body: dict[str, Any] | None = None,
) -> Response:
```

Si luego quieres soportar raw body, agrega `raw_body: bytes | None = None`.

### 4.4 Logica interna recomendada

Orden exacto:

1. construir URL segura (`base_url.rstrip("/") + "/" + path.lstrip("/")`),
2. extraer `params = dict(request.query_params)`,
3. filtrar headers de entrada,
4. medir tiempo con `time.perf_counter()`,
5. llamar `request.app.state.http_client.request(...)`,
6. mapear excepciones a 502/504,
7. filtrar headers de respuesta,
8. devolver `Response(...)`.

### 4.5 Mapeo de errores

Regla simple:

- `ConnectError` => 502,
- `ReadTimeout/WriteTimeout/PoolTimeout` => 504,
- resto de `HTTPError` => 502.

Mensajes seguros (sin detalle interno):

- `"Upstream unavailable"`
- `"Upstream timeout"`
- `"Gateway upstream error"`

## Paso 5 detallado - `routes/vehicles.py`

Debes ajustar endpoints para recibir `Request` y pasarlo al proxy:

```python
from fastapi import APIRouter, Request

@router.post("")
async def create_vehicle(request: Request, payload: dict[str, Any]):
    return await forward_request(
        request=request,
        method="POST",
        base_url=VEHICLES_SERVICE_BASE_URL,
        path="/api/v1/vehicles",
        json_body=payload,
    )
```

Haz lo mismo con el GET.

Por que:

- asi `forward_request` puede leer query params y headers originales.

## Paso 6 detallado - pruebas manuales utiles

Con gateway y vehicles corriendo:

```bash
curl -i "http://127.0.0.1:8000/api/v1/vehicles/u1?page=1&limit=10"
curl -i -X POST "http://127.0.0.1:8000/api/v1/vehicles" -H "content-type: application/json" -d '{"brand":"Mazda","model":"3"}'
```

Que debes observar:

- status code igual al de upstream,
- `content-type` correcto,
- query params presentes en upstream,
- sin errores de conexion en logs.

## Paso 7 detallado - tests automatizados minimos

Archivo: `apps/api_gateway/tests/test_proxy.py`

Casos recomendados (nombre orientativo):

- `test_forward_get_with_query_params`
- `test_forward_post_json_body`
- `test_filters_hop_by_hop_headers`
- `test_connect_error_returns_502`
- `test_timeout_returns_504`

Si no tienes fixtures de app aun, empieza unit testeando helpers (`filter_*`) y luego sube a integración ligera.

## Paso 8 detallado - troubleshooting (debug rapido)

- `AttributeError: 'State' object has no attribute 'http_client'`
  - no se ejecuto startup o no asignaste `app.state.http_client`.
- siempre responde 502 aunque el upstream vive
  - revisa URL base, puerto y slash en path (`//api`).
- responde 504 muy rapido
  - timeouts demasiado bajos.
- upstream no recibe `Authorization`
  - lo estas filtrando por accidente en `filter_request_headers`.
- response sin `content-type`
  - estas devolviendo solo `media_type`; prueba pasar headers filtrados completos.

## Paso 9 detallado - criterios para "listo para PR"

Checklist estricto:

- Cliente HTTP compartido activo en startup/shutdown.
- `forward_request` no instancia clientes.
- Query params y headers se propagan.
- Hop-by-hop filtrados en request y response.
- Errores de red diferenciados (502/504).
- Logs con metodo, URL, status y duracion.
- Tests minimos pasando.

## 6) Pseudocodigo de referencia

No copies esto literal. Es una guia mental de como debe quedar el flujo:

```python
async def forward_request(request, base_url, path, *, json_body=None, raw_body=None):
    url = join_url(base_url, path)
    headers = filter_request_headers(request.headers)
    params = dict(request.query_params)

    start = monotonic()
    try:
        response = await request.app.state.http_client.request(
            method=request.method,
            url=url,
            headers=headers,
            params=params,
            json=json_body,
            content=raw_body,
        )
    except httpx.ConnectError as exc:
        raise HTTPException(status_code=502, detail="Upstream unavailable") from exc
    except (httpx.ReadTimeout, httpx.WriteTimeout, httpx.PoolTimeout) as exc:
        raise HTTPException(status_code=504, detail="Upstream timeout") from exc
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Gateway error") from exc
    finally:
        duration_ms = ...
        logger.info(...)

    return Response(
        content=response.content,
        status_code=response.status_code,
        headers=filter_response_headers(response.headers),
    )
```

## 7) Checklist de calidad antes de merge

- No se crea `AsyncClient` por request.
- Se usan timeouts por etapa (`connect/read/write/pool`).
- Se filtran headers hop-by-hop (entrada y salida).
- Se propagan params y body correctamente.
- Errores de red mapeados a 502/504.
- Logs incluyen request-id y duracion.
- Tests de proxy en verde.
- `/health/services` usa cliente compartido.

## 8) Errores comunes y como evitarlos

- Dejar `except Exception` demasiado amplio: oculta causa real.
- Reenviar `Host` original: rompe algunos upstreams.
- Hardcodear timeouts unicos para todo.
- Reintentar `POST` sin estrategia de idempotencia.
- Forzar siempre `application/json` aunque el upstream devuelva otro tipo.

## 9) Roadmap corto (si quieres llevarlo mas lejos)

1. Correlation ID middleware global.
2. Metricas Prometheus (latencia, errores por upstream).
3. Circuit breaker para upstream inestable.
4. Rate limiting por ruta.
5. Caching en GET de lectura frecuente (si aplica negocio).

---

Si quieres, en el siguiente paso te puedo preparar una guia "hands-on" por commit:

- commit 1: settings + startup/shutdown,
- commit 2: proxy v2,
- commit 3: tests,
- commit 4: logging y retry opcional.

