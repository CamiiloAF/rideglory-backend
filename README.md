# Rideglory Backend

FastAPI microservices scaffold using Clean Architecture.

## Suggested structure

```text
rideglory-backend/
├── apps/
│   └── api_gateway/
│       └── main.py
├── services/
│   └── vehicles/
│       ├── app/
│       │   ├── main.py
│       │   ├── dependencies/
│       │   │   └── container.py
│       │   ├── api/
│       │   │   └── v1/
│       │   │       └── routes/
│       │   │           └── vehicles.py
│       │   ├── application/
│       │   │   └── use_cases/
│       │   │       └── create_vehicle.py
│       │   ├── domain/
│       │   │   ├── entities/
│       │   │   │   └── vehicle.py
│       │   │   └── repositories/
│       │   │       └── vehicle_repository.py
│       │   ├── infrastructure/
│       │   │   └── repositories/
│       │   │       └── in_memory_vehicle_repository.py
│       │   └── core/
│       │       └── config.py
│       └── tests/
├── shared/
│   ├── kernel/
│   │   └── exceptions.py
│   └── contracts/
│       └── events.py
└── main.py
```

## Architecture layers

- `domain`: enterprise business rules, entities, repository contracts.
- `application`: use cases and business orchestration.
- `infrastructure`: implementations (DB, message broker, external APIs).
- `api`: FastAPI routes, request/response schemas, dependency wiring.
- `core`: settings and service-level utilities.

## Run examples

Vehicles service:

```bash
uvicorn services.vehicles.app.main:app --reload --port 8001
```

API gateway:

```bash
uvicorn apps.api_gateway.main:app --reload --port 8000
```

## What the API gateway does

The gateway is the single entrypoint clients call. It can:

- centralize cross-cutting concerns (auth, logging, rate limits),
- aggregate health from downstream services,
- proxy requests to internal services so clients do not call each service directly.

In this scaffold, the gateway currently proxies vehicle operations to the vehicles service.

### Quick local demo

1. Start vehicles service on `:8001`.
2. Start gateway on `:8000`.
3. Call gateway health:

```bash
curl http://localhost:8000/health/services
```

4. Create vehicle through gateway:

```bash
curl -X POST http://localhost:8000/api/v1/vehicles \
  -H "Content-Type: application/json" \
  -d '{"plate":"ABC-123","brand":"Mazda"}'
```

5. Get vehicles by user through gateway:

```bash
curl http://localhost:8000/api/v1/vehicles/<user_id>
```

You can override downstream URL with:

```bash
export VEHICLES_SERVICE_BASE_URL=http://localhost:8001
```
