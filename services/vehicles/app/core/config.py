from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    service_name: str = "vehicles-service"
    api_version: str = "v1"

    model_config = SettingsConfigDict(env_prefix="VEHICLES_", env_file=".env")


settings = Settings()
