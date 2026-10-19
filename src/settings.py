from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    POSTGRES_HOST: str = "127.0.0.1"
    POSTGRES_PORT: int = 5432
    POSTGRES_DB: str = ""
    POSTGRES_USER: str = ""
    POSTGRES_PASSWORD: str = ""

    DATABASE_DSN: str = ""

    REDIS_SERVER: str = "127.0.0.1"
    REDIS_PORT: int = 6379
    CACHE_LIFETIME: int = 5

    REQUEST_SCHEDULE: int = 60

    model_config = SettingsConfigDict(env_file=".env")


settings = Settings()
