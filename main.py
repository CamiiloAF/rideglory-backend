from fastapi import FastAPI

app = FastAPI(title="Rideglory Backend")


@app.get("/")
async def root() -> dict[str, str]:
    return {
        "message": "Use apps/api_gateway/main.py or services/<service>/app/main.py entrypoints."
    }