# Guía: X-Request-ID, logs unificados y campos del proxy (nivel principiante)

Esta guía está pensada si **empiezas en backend** o en **FastAPI**. Incluye:

- Un **glosario** de términos (qué significan y por qué aparecen aquí).
- **Ejemplos de código** que puedes usar como plantilla (adaptando rutas de import a tu proyecto).
- Pasos **ordenados** y **por qué** va cada cosa en ese orden.

**Al final sabrás implementar:**

1. Cabecera **`X-Request-ID`** + un ID guardado **por petición** (sin mezclar usuarios).
2. Que **Loguru** añada automáticamente `request_id` a **cada** línea de log.
3. Que los logs del **servidor** (Uvicorn) pasen por el **mismo formato** que tu app (Loguru).
4. Que los logs del **proxy** lleven siempre los campos: `event`, `duration_ms`, `upstream_status`, `path`, `method`.

> **Antes:** configura Loguru una vez al arrancar (ver [README_LOGGING.md](./README_LOGGING.md)).

---

## Cómo leer esta guía

| Orden | Sección | Para qué sirve |
|-------|---------|----------------|
| 1 | [Glosario](#glosario-términos-que-van-a-salir) | Entender palabras nuevas sin buscar en Google cada dos líneas. |
| 2 | [Idea general](#idea-general-en-30-segundos) | Ver el “mapa mental” antes del código. |
| 3 | [Implementación](#implementación-paso-a-paso-con-ejemplos) | Copiar/adaptar archivos en orden. |
| 4 | [Validar](#cómo-validar-que-funciona) | Comprobar que no hay errores típicos. |

---

## Glosario (términos que van a salir)

### Web y HTTP

| Término | Explicación simple |
|--------|---------------------|
| **Cliente** | Quien hace la petición: navegador, app móvil, `curl`, otro microservicio. |
| **Servidor** | Tu programa que **escucha** en un puerto y **responde** (aquí: el API Gateway). |
| **Request (petición)** | Lo que envía el cliente: método (`GET`, `POST`…), URL, **cabeceras**, cuerpo opcional. |
| **Response (respuesta)** | Lo que devuelve el servidor: **código de estado** (200, 404…), **cabeceras**, cuerpo. |
| **Cabecera / header** | Metadato en la petición o respuesta, p. ej. `Authorization`, `Content-Type`, o **`X-Request-ID`**. Las cabeceras `X-...` suelen ser **convenciones** (no estándar HTTP oficial, pero muy usadas). |
| **Upstream (aguas arriba)** | En un **gateway**, el servicio **al que reenvías** el tráfico (p. ej. “servicio de vehículos”). Tu gateway es “delante”; el otro está “arriba” en la cadena. |

### Tu stack (FastAPI)

| Término | Explicación simple |
|--------|---------------------|
| **FastAPI** | Framework para escribir APIs en Python: defines rutas (`@app.get`, `@router.post`…) y funciones que se ejecutan cuando llega una petición. |
| **Uvicorn** | **Servidor ASGI** que ejecuta tu app FastAPI. Es quien abre el puerto, recibe HTTP y llama a FastAPI. También escribe **logs propios** (arranque, acceso…). |
| **ASGI** | Contrato moderno entre servidor (Uvicorn) y aplicación (FastAPI): mensajes asíncronos. No necesitas memorizarlo; solo saber que **Uvicorn + FastAPI** encajan aquí. |
| **Middleware** | Código que se ejecuta **alrededor** de cada petición: **antes** de tu ruta y **después** (cuando ya hay respuesta). Sirve para cosas transversales: IDs, seguridad, medir tiempo. Analogía: un filtro por donde pasa **toda** el agua. |
| **Lifespan** | Bloque `lifespan` en FastAPI: código que corre **al arrancar** la app (abrir conexiones, configurar logs) y **al apagar** (cerrar recursos). Es el sitio típico para `configure_logging()` **una vez**. |

### Concurrencia y contexto

| Término | Explicación simple |
|--------|---------------------|
| **Async / `await`** | Forma de no bloquear el hilo mientras esperas red, disco, etc. FastAPI y `httpx` async encajan con esto. |
| **Corrutina** | Función async que puede pausarse en un `await`. Muchas corrutinas pueden convivir en el mismo proceso. |
| **Variable global** | Una sola variable compartida por **todo** el proceso. **Mala idea** para “el ID del request actual” porque muchas peticiones pisan la misma variable al mismo tiempo. |
| **`ContextVar` (variable de contexto)** | Variable cuyo valor depende del **contexto de ejecución actual** (la petición async que está corriendo ahora). Es la forma correcta de tener “un `request_id` por petición”. |
| **Token (en `contextvars`)** | Objeto opaco que devuelve `.set(...)`. Sirve para **volver atrás** con `.reset(token)` y dejar el contexto como estaba. |

### Logging en Python

| Término | Explicación simple |
|--------|---------------------|
| **`logging` (biblioteca estándar)** | Sistema de logs de Python “clásico”: `logging.getLogger("nombre").info(...)`. **Uvicorn usa esto** internamente. |
| **Loguru** | Librería de logging más cómoda (`from loguru import logger`). **Tu app** puede usarla. El reto es **unificar** ambos mundos. |
| **Handler** | En `logging` estándar: objeto que **recibe** un mensaje de log y hace algo (escribir a consola, archivo…). Vamos a crear un handler que **reenvía** a Loguru. |
| **Sink (Loguru)** | Destino del log: en tu caso suele ser `sys.stderr` (consola). `logger.add(sys.stderr, ...)` “añade un sink”. |
| **`extra` (Loguru)** | Diccionario de **campos extra** en cada línea de log (útil para JSON y para buscar en Datadog/Cloud Logging). El **patcher** y **`bind`** rellenan cosas aquí. |
| **Patcher** | Función que Loguru llama **antes** de formatear cada mensaje. Sirve para meter `request_id` en `extra` automáticamente. |
| **`bind`** | `logger.bind(campo=valor)` devuelve un logger que **siempre** incluirá esos campos en `extra`. Ideal para `event`, `path`, etc. |

---

## Idea general (en 30 segundos)

1. **Middleware:** en cada petición HTTP decides un string `request_id` (del header o uno nuevo) y lo guardas en un **`ContextVar`**.
2. **Loguru patcher:** cada vez que alguien hace `logger.info(...)`, Loguru copia el `request_id` del contexto al campo `extra` → aparece en consola/JSON.
3. **InterceptHandler:** los logs de Uvicorn pasan por `logging` estándar; tú rediriges esos mensajes a Loguru → **mismo formato** que tu código.
4. **Proxy:** en vez de escribir el path a mano en el texto del mensaje, usas **`bind`** con los cinco campos fijos → logs **estructurados** y fáciles de filtrar.

```
Cliente  --HTTP-->  Uvicorn  -->  Middleware (pone request_id)
                              -->  FastAPI (rutas, proxy)
                              -->  Respuesta + cabecera X-Request-ID
```

---

## Implementación paso a paso (con ejemplos)

Sigue el **orden**: cada bloque asume que el anterior existe.

---

### Paso A — `core/request_context.py` (solo contexto, sin Loguru)

**Por qué sin Loguru:** evitas **imports circulares** (`loguru_config` → `request_context` → algo → `middleware` → `loguru_config`). Este archivo solo conoce `contextvars` y `uuid`.

**Qué hace:** guarda el ID actual de la petición y permite restaurarlo.

**Ejemplo completo:**

```python
# apps/api_gateway/core/request_context.py
from __future__ import annotations

import uuid
from contextvars import ContextVar, Token

# Valor por defecto: None = "no estamos dentro de un request HTTP todavía"
_request_id: ContextVar[str | None] = ContextVar("request_id", default=None)


def get_request_id() -> str | None:
    """Lo usa el patcher de Loguru (y tu código si lo necesitas)."""
    return _request_id.get()


def set_request_id(value: str) -> Token[str | None]:
    """Devuelve un token para poder hacer reset después."""
    return _request_id.set(value)


def reset_request_id(token: Token[str | None]) -> None:
    """Vuelve el ContextVar al valor que tenía antes de este request."""
    _request_id.reset(token)


def generate_request_id() -> str:
    """ID único si el cliente no mandó uno."""
    return str(uuid.uuid4())
```

**Lectura rápida:**

- `ContextVar("request_id", default=None)` crea la “caja” llamada `request_id`.
- `set` + `reset` evitan que el ID del usuario A “contamine” al usuario B.

---

### Paso B — `middleware/request_id.py` (middleware HTTP)

**Qué es un middleware aquí:** una clase que implementa `dispatch`: recibe `request`, llama a `call_next(request)` (sigue la cadena: más middlewares o la ruta), y devuelve `response`.

**Ejemplo completo:**

```python
# apps/api_gateway/middleware/request_id.py
from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from apps.api_gateway.core.request_context import (
    generate_request_id,
    reset_request_id,
    set_request_id,
)

HEADER_NAME = "X-Request-ID"


class RequestIDMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        raw = request.headers.get("x-request-id")
        if raw is None or not raw.strip():
            rid = generate_request_id()
        else:
            rid = raw.strip()

        token = set_request_id(rid)
        try:
            response = await call_next(request)
            response.headers[HEADER_NAME] = rid
            return response
        finally:
            reset_request_id(token)
```

**Notas para novatos:**

- `call_next` es “sigue con FastAPI hasta la ruta y vuelve con la respuesta”.
- El `finally` **siempre** corre, aunque falle la ruta: por eso el `reset` va ahí.
- Repetir `X-Request-ID` en la **respuesta** ayuda al cliente a correlacionar logs cliente/servidor.

**`middleware/__init__.py` (opcional):**

```python
from apps.api_gateway.middleware.request_id import RequestIDMiddleware

__all__ = ["RequestIDMiddleware"]
```

---

### Paso C — Registrar el middleware en `main.py`

**Dónde:** después de crear `app = FastAPI(...)`, **antes** o después de `include_router` según tu estilo; lo importante es que exista el `app`.

**Ejemplo:**

```python
from apps.api_gateway.middleware.request_id import RequestIDMiddleware

app = FastAPI(title="Rideglory API Gateway", lifespan=lifespan)

app.add_middleware(RequestIDMiddleware)

app.include_router(vehicles_router)
```

**Qué significa “envolver”:** Starlette va apilando middlewares. Si más adelante añades otro, lee la doc o prueba: el orden importa si dos middlewares tocan lo mismo. Para `request_id`, suele bastar que esté registrado **una vez** y temprano en tu lista.

---

### Paso D — Patcher de Loguru en `core/loguru_config.py`

**Problema que resuelves:** `logger.info("hola")` **no** mira el `ContextVar` solo. El **patcher** copia `get_request_id()` a `record["extra"]["request_id"]` en **cada** línea.

**Ejemplo (fragmento; intégralo dentro de tu `configure_logging` existente):**

```python
import logging
import sys

from loguru import logger

from apps.api_gateway.core.request_context import get_request_id
from apps.api_gateway.core.settings import LOG_JSON, LOG_LEVEL


def _patch_request_id(record: dict) -> None:
    rid = get_request_id()
    # Siempre define la clave para que {extra[request_id]} no reviente en modo texto
    record["extra"]["request_id"] = rid if rid is not None else "-"


def configure_logging() -> None:
    # 1) Patcher primero (antes de remove/add)
    logger.configure(patcher=_patch_request_id)

    logger.remove()

    if LOG_JSON:
        logger.add(sys.stderr, level=LOG_LEVEL, serialize=True)
    else:
        logger.add(
            sys.stderr,
            level=LOG_LEVEL,
            format=(
                "<green>{time:DD/MM/YYYY HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{extra[request_id]}</cyan> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                "<level>{message}</level>"
            ),
        )

    # ... aquí irá el intercept de Uvicorn (Paso E)
```

**Términos:**

- `record` es un **dict** con datos de la línea de log; `extra` es donde van tus campos personalizados.

---

### Paso E — Interceptar `logging` (Uvicorn) hacia Loguru

**Problema:** Uvicorn no usa `from loguru import logger`; usa `logging`. Sin puente, verías **otro formato** o otro manejo.

**Solución:** un `Handler` que en `emit` manda el mensaje a Loguru. Patrón recomendado por la documentación de Loguru (simplificado):

```python
class InterceptHandler(logging.Handler):
    def emit(self, record: logging.LogRecord) -> None:
        try:
            level = logger.level(record.levelname).name
        except ValueError:
            level = str(record.levelno)

        depth = 2
        frame = logging.currentframe()
        while frame is not None and frame.f_code.co_filename == logging.__file__:
            frame = frame.f_back
            depth += 1

        logger.opt(depth=depth, exception=record.exc_info).log(
            level, record.getMessage()
        )
```

**Después** de `logger.add(...)`, redirige los loggers de librería:

```python
_STD_LEVEL = getattr(logging, LOG_LEVEL, logging.INFO)


def _setup_stdlib_interception() -> None:
    intercept = InterceptHandler()
    for name in ("uvicorn", "uvicorn.error", "uvicorn.access", "fastapi"):
        log = logging.getLogger(name)
        log.handlers = [intercept]
        log.setLevel(_STD_LEVEL)
        log.propagate = False
```

Y dentro de `configure_logging()` llamas `_setup_stdlib_interception()` al final.

**Por qué `setLevel`:** muchos loggers de Uvicorn quedan en un nivel que **silencia INFO**; entonces “no ves” el access log aunque tu Loguru esté en INFO.

**Por qué `propagate = False`:** si el mensaje **también** sube al logger raíz con otro handler, puedes tener **duplicados**.

---

### Paso F — Campos fijos en el proxy (`core/proxy.py`)

**Objetivo:** cada log del proxy incluya en `extra`:

| Campo | Qué es |
|-------|--------|
| `event` | Nombre del tipo de evento (`proxy_upstream_success`, `proxy_upstream_error`, …). |
| `duration_ms` | Cuánto tardó la operación en milisegundos. |
| `upstream_status` | Código HTTP del servicio aguas arriba (`200`, `404`…), o `None` si ni siquiera hubo respuesta. |
| `path` | Path del upstream que llamaste (tu `params.path`). |
| `method` | Método HTTP (`GET`, `POST`…). |

**Ejemplo de patrón con `bind`:**

```python
from loguru import logger

log = logger.bind(service="api_gateway", component="proxy")


def log_proxy_success(*, params, duration_ms: float, upstream_status: int) -> None:
    log.bind(
        event="proxy_upstream_success",
        duration_ms=duration_ms,
        upstream_status=upstream_status,
        path=params.path,
        method=params.method.value,
    ).info("proxy_upstream_success")


def log_proxy_error(*, params, duration_ms: float, error_type: str) -> None:
    log.bind(
        event="proxy_upstream_error",
        duration_ms=duration_ms,
        upstream_status=None,
        path=params.path,
        method=params.method.value,
    ).warning("proxy_upstream_error error_type={error_type}", error_type=error_type)
```

**Novato:** el **string** del mensaje puede ser corto; lo importante para buscar en producción son los **campos** (`event`, `path`, …) en JSON.

**Cómo obtener `duration_ms`:** guarda `start = time.perf_counter()` al entrar en `forward_request` y antes de loguear haz `(time.perf_counter() - start) * 1000` (redondeado como prefieras).

---

## Orden correcto dentro de `configure_logging()`

Resumen para no equivocarte:

1. `logger.configure(patcher=...)`
2. `logger.remove()`
3. `logger.add(...)` (tu sink único)
4. `_setup_stdlib_interception()` (Uvicorn → Loguru)

**Y en el arranque de la app:** que `configure_logging()` se ejecute en el **`lifespan`** (como ya explica [README_LOGGING.md](./README_LOGGING.md)), **antes** de atender tráfico serio.

---

## Cómo validar que funciona

### Checklist

- [ ] Sin enviar cabecera: la **respuesta** trae `X-Request-ID` y en los logs (texto o JSON) aparece el **mismo** valor en `request_id`.
- [ ] Enviando `X-Request-ID: prueba-123`: el servidor **repite** `prueba-123` en la respuesta (si esa es tu política).
- [ ] Ves líneas de acceso / Uvicorn con el **mismo estilo** que tus `logger.info` de aplicación.
- [ ] Con `LOG_LEVEL=INFO` ves logs de `uvicorn.access` (si no, revisa `setLevel`).
- [ ] Un log del proxy en JSON muestra los cinco campos.

### Comandos útiles

```bash
export LOG_JSON=true
export LOG_LEVEL=INFO
# Arranca tu gateway (ejemplo):
# uvicorn apps.api_gateway.main:app --reload --port 8000

curl -v http://localhost:8000/api/health/services
curl -v -H "X-Request-ID: mi-id-fijo" http://localhost:8000/api/health/services
```

Mira la salida en la **consola** donde corre Uvicorn o `docker logs` si usas contenedor.

---

## Errores comunes (tabla rápida)

| Síntoma | Qué revisar |
|---------|-------------|
| IDs mezclados entre requests | `reset_request_id(token)` en `finally` del middleware. |
| No ves INFO de Uvicorn | `setLevel` en los loggers `uvicorn.*`. |
| Logs duplicados | `propagate=True` o handlers viejos en el root. |
| Error de formato `{extra[request_id]}` | Patcher no pone `request_id` cuando es `None` (usa `"-"`). |
| ImportError circular | `request_context` no debe importar Loguru ni el middleware no debe importar `loguru_config` si eso crea ciclo. |

---

## Buenas prácticas mínimas

- Limita tamaño y caracteres de `X-Request-ID` si la API es pública (evita cabeceras gigantes).
- No pongas datos sensibles en el ID; es para **trazabilidad**, no seguridad.
- Documenta qué significa `upstream_status=None` en errores (sin respuesta HTTP).

---

## Relación con otros documentos

| Archivo | Contenido |
|---------|-----------|
| [README_LOGGING.md](./README_LOGGING.md) | Loguru base, Docker, variables `LOG_JSON` / `LOG_LEVEL`. |
| [README.md](./README.md) | Diseño del proxy y mejoras generales del gateway. |
| **Este archivo** | Request ID, contexto, Uvicorn+Loguru, campos del proxy. |

---

## Resumen en una frase

**El middleware guarda un ID por petición en un `ContextVar`, Loguru lo copia al `extra` con un patcher, Uvicorn entra por un `InterceptHandler`, y el proxy usa `bind` para logs estructurados.**
