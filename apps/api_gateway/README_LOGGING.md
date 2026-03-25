# Guía: logs con Loguru + Docker (stdout)

Esta guía explica **cómo implementar logging de forma correcta** en el API Gateway usando **Loguru**, y **cómo configurar Docker** para que los logs vayan a **stdout/stderr** y el contenedor/orquestador los recolecte bien.

Está pensada para nivel junior: conceptos primero, luego pasos concretos.

---

## Parte A — Conceptos (léelo una vez)

### A.1 ¿Qué es stdout?

- **stdout** = salida estándar: el flujo de texto “normal” del proceso.
- Cuando ejecutas la app en terminal, muchos mensajes que ves salen por ahí.
- En **Docker/Kubernetes**, lo habitual es: la aplicación escribe logs a **stdout** (y errores a **stderr**). Docker **captura** esa salida y la guarda en su motor de logging. No hace falta escribir archivos `.log` dentro del contenedor para tener logs en producción.

### A.2 ¿Por qué un solo lugar de configuración?

Si llamas `logger.add(...)` en muchos archivos:

- se duplican líneas por evento,
- cambian niveles/formatos sin querer,
- es difícil desactivar o cambiar el sink en tests.

**Regla:** configura Loguru **una vez** al arrancar la app (por ejemplo en el `lifespan` de FastAPI o en un módulo importado desde ahí).

### A.3 Niveles típicos

| Nivel    | Uso habitual                                      |
|----------|---------------------------------------------------|
| `DEBUG`  | Detalle para depurar (no en prod ruidoso)         |
| `INFO`   | Flujo normal: request proxy OK, health, etc.      |
| `WARNING`| Algo raro pero recuperable (retry, degradación)   |
| `ERROR`  | Fallo que impide completar la operación           |

### A.4 Qué no loguear nunca

- Tokens completos (`Authorization`, cookies de sesión).
- Contraseñas, secretos, API keys.
- Cuerpos completos de requests si pueden llevar datos personales (PII), salvo política explícita y enmascarado.

---

## Parte B — Implementación paso a paso (Loguru)

Sigue los pasos en orden. Asumes que `loguru` ya está en `requirements.txt` (en este repo ya está).

### Paso B.1 — Variables de entorno para logging

En `apps/api_gateway/core/settings.py` (o donde centralices config), agrega constantes leídas del entorno:

```python
import os

LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
LOG_JSON = os.getenv("LOG_JSON", "false").lower() in ("1", "true", "yes")
```

- **`LOG_LEVEL`:** `DEBUG`, `INFO`, `WARNING`, `ERROR`.
- **`LOG_JSON`:** en producción suele ir `true` para que cada línea sea JSON (fácil de indexar en Datadog, Cloud Logging, ELK, etc.). En local puedes dejar `false` para texto legible.

**Validación:** sin definir nada, `LOG_LEVEL` debe ser `INFO` y `LOG_JSON` false.

---

### Paso B.2 — Módulo único de configuración

Crea el archivo:

`apps/api_gateway/core/loguru_config.py`

Responsabilidad de este archivo:

1. `logger.remove()` — quita el handler por defecto de Loguru (evita duplicados si vuelves a configurar).
2. `logger.add(sys.stderr, ...)` — **stderr** es lo habitual para logs de aplicación; Docker recolecta stdout y stderr por igual en muchos setups, pero muchos equipos prefieren **stderr** para no mezclar con salida “datos” en stdout.
3. Nivel desde `LOG_LEVEL`.
4. Formato:
   - si `LOG_JSON`: usa `serialize=True` en `logger.add` (Loguru emite JSON por línea),
   - si no: usa un `format=` legible con tiempo, nivel, módulo, mensaje.

Ejemplo mínimo (ajústalo a tu gusto):

```python
import sys

from loguru import logger

from apps.api_gateway.core.settings import LOG_JSON, LOG_LEVEL


def configure_logging() -> None:
    logger.remove()

    if LOG_JSON:
        logger.add(
            sys.stderr,
            level=LOG_LEVEL,
            serialize=True,
        )
    else:
        logger.add(
            sys.stderr,
            level=LOG_LEVEL,
            format=(
                "<green>{time:YYYY-MM-DD HH:mm:ss.SSS}</green> | "
                "<level>{level: <8}</level> | "
                "<cyan>{name}</cyan>:<cyan>{function}</cyan>:<cyan>{line}</cyan> | "
                "<level>{message}</level>"
            ),
        )
```

**Importante:** no importes `configure_logging` desde módulos que se carguen antes de tiempo de forma circular; lo más seguro es llamarlo solo desde `main.py` al inicio del `lifespan`.

---

### Paso B.3 — Invocar la configuración al arrancar FastAPI

En `apps/api_gateway/main.py`, dentro del `lifespan`, **antes** de crear recursos (HTTP client):

```python
from apps.api_gateway.core.loguru_config import configure_logging

@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    app.state.http_client = build_http_client()
    try:
        yield
    finally:
        await close_http_client(app.state.http_client)
```

**Por qué aquí:** se ejecuta una vez por proceso worker. Si usas varios workers de Uvicorn, cada uno configurará su logger (correcto).

**Validación:** levanta la app y comprueba que ves logs de arranque o un log de prueba (siguiente paso).

---

### Paso B.4 — Logger en el proxy (patrón escalable)

En `apps/api_gateway/core/proxy.py` (u otro módulo de negocio):

- No llames `logger.add`.
- Usa un logger con contexto fijo del componente:

```python
from loguru import logger

log = logger.bind(service="api_gateway", component="proxy")
```

En cada operación importante:

```python
import time

start = time.perf_counter()
# ... await http_client.request(...)
duration_ms = round((time.perf_counter() - start) * 1000, 2)

log.info(
    "proxy_upstream_success method={method} path={path} status={status} duration_ms={duration_ms}",
    method=params.method.value,
    path=params.path,
    status=resp.status_code,
    duration_ms=duration_ms,
)
```

En errores:

```python
log.warning(
    "proxy_upstream_error method={method} path={path} error_type={error_type} duration_ms={duration_ms}",
    method=params.method.value,
    path=params.path,
    error_type=type(exc).__name__,
    duration_ms=duration_ms,
)
```

**Opcional avanzado:** middleware en FastAPI que hace `logger.contextualize(request_id=...)` leyendo `X-Request-ID` para que todos los logs de esa request lleven el mismo id.

---

### Paso B.5 — Alinear logs de Uvicorn (opcional)

Uvicorn usa el `logging` estándar de Python. Tus logs con Loguru pueden verse distintos.

Opciones:

1. **Dejarlo así** al principio (más simple): verás dos estilos de línea.
2. **Interceptar** `logging` hacia Loguru (patrón oficial en docs de Loguru): un solo formato.

Si más adelante unificas, busca en la documentación de Loguru: *“Entangling with standard logging”* / intercept handler.

---

### Paso B.6 — Uvicorn y access logs

Al ejecutar en Docker suele usarse:

```bash
uvicorn apps.api_gateway.main:app --host 0.0.0.0 --port 8000 --log-level info
```

- Los **access logs** (cada HTTP entrante al gateway) los escribe Uvicorn.
- Tus **logs de negocio** (proxy) los escribe Loguru a stderr.

Ambos fluyen al recolector de Docker si no rediriges nada raro.

---

## Parte C — Docker paso a paso (alineado con stdout/stderr)

No hay Dockerfile en el repo al momento de escribir esta guía; estos pasos te dejan uno listo para el gateway.

### Paso C.1 — Dockerfile mínimo para el API Gateway

Crea en la raíz del backend (o en `apps/api_gateway/`, según prefieras el contexto de build) un archivo `Dockerfile.api_gateway` ejemplo:

```dockerfile
FROM python:3.13-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY apps ./apps

EXPOSE 8000

# Logs: la app escribe a stderr (Loguru) y Uvicorn también; Docker los captura.
CMD ["uvicorn", "apps.api_gateway.main:app", "--host", "0.0.0.0", "--port", "8000", "--log-level", "info"]
```

**Claves:**

- **`PYTHONUNBUFFERED=1`:** evita que Python retenga prints/logs en buffer; en contenedor los ves al instante (importante para `docker logs`).
- **No redirigas** la salida a archivos dentro del contenedor para el caso básico: deja que todo vaya a consola (stdout/stderr).

**Build y run local:**

```bash
docker build -f Dockerfile.api_gateway -t rideglory-api-gateway .
docker run --rm -p 8000:8000 \
  -e LOG_LEVEL=INFO \
  -e LOG_JSON=true \
  -e VEHICLES_SERVICE_BASE_URL=http://host.docker.internal:8001 \
  rideglory-api-gateway
```

En Linux, `host.docker.internal` a veces no existe; usa IP del host o red Docker (`--add-host=host.docker.internal:host-gateway` en Docker moderno).

---

### Paso C.2 — docker-compose (gateway + vehicles)

Ejemplo esquemático `docker-compose.yml` en la raíz del backend:

```yaml
services:
  api_gateway:
    build:
      context: .
      dockerfile: Dockerfile.api_gateway
    ports:
      - "8000:8000"
    environment:
      LOG_LEVEL: INFO
      LOG_JSON: "true"
      VEHICLES_SERVICE_BASE_URL: http://vehicles:8001
    depends_on:
      - vehicles

  vehicles:
    build:
      context: .
      dockerfile: Dockerfile.vehicles   # cuando exista
    ports:
      - "8001:8001"
```

**Logs en compose:**

```bash
docker compose logs -f api_gateway
docker compose logs -f --tail=100 api_gateway
```

Todo lo que la app escriba a stdout/stderr aparece ahí.

---

### Paso C.3 — Driver de logging (producción)

Docker por defecto usa el driver `json-file`, que guarda stdout/stderr del contenedor en el host.

Para verificar:

```bash
docker inspect --format='{{.HostConfig.LogConfig.Type}}' <container_id>
```

En Kubernetes/cloud, el recolector (Fluent Bit, Datadog, etc.) suele leer esos logs o el runtime los envía al proveedor. **No necesitas** rotación de archivos dentro del contenedor para el caso estándar.

---

### Paso C.4 — Checklist “Docker + logs OK”

- [ ] `PYTHONUNBUFFERED=1` en la imagen.
- [ ] Loguru configurado **una vez** al arrancar (`lifespan`).
- [ ] Sink a `sys.stderr` (o stdout, pero sé consistente).
- [ ] En prod/staging: `LOG_JSON=true` para una línea JSON por evento.
- [ ] `docker logs <container>` muestra logs sin retraso raro.
- [ ] No se loguean secretos ni bodies sensibles completos.

---

## Parte D — Referencia rápida de variables

| Variable       | Ejemplo   | Descripción                          |
|----------------|-----------|--------------------------------------|
| `LOG_LEVEL`    | `INFO`    | Nivel mínimo de Loguru               |
| `LOG_JSON`     | `true`    | Salida JSON por línea (prod)         |
| `LOG_LEVEL` (uvicorn) | vía flag `--log-level` | Logs del servidor ASGI |

---

## Parte E — Siguientes mejoras (cuando domines lo básico)

1. Middleware `X-Request-ID` + contextualización en Loguru.
2. Interceptar `logging` estándar para unificar con Uvicorn.
3. Campos fijos en cada log de proxy: `event`, `duration_ms`, `upstream_status`, `path`, `method`.
4. Métricas (Prometheus) aparte de logs; no sustituyen al otro.

**Guía detallada paso a paso (implementación manual):** [README_REQUEST_ID_AND_LOG_UNIFICATION.md](./README_REQUEST_ID_AND_LOG_UNIFICATION.md).

---

## Resumen en una frase

**Configura Loguru una vez, escribe a stderr en formato JSON en prod, activa `PYTHONUNBUFFERED` en Docker, y deja que Docker capture stdout/stderr sin archivos dentro del contenedor.**

Si quieres que esta guía viva enlazada desde el README principal del gateway, agrega una línea en `apps/api_gateway/README.md` apuntando a este archivo.
