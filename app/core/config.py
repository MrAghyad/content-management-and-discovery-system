from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import computed_field

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8")

    # App
    app_name: str = "CMS"
    app_host: str = "0.0.0.0"
    app_port: int = 8000
    debug: bool = False

    # DB settings
    db_user: str
    db_pass: str
    db_host: str
    db_port: int
    db_name: str

    # Auth
    jwt_secret: str
    jwt_issuer: str = "cms"
    jwt_audience: str = "cms-clients"
    jwt_expires_minutes: int = 60

    # OpenSearch (Discovery)
    os_host: str
    os_username: str
    os_password: str
    os_index: str = "contents"

    # Redis (Discovery cache / general)
    redis_url: str = "redis://localhost:6379/0"
    celery_broker_url: str
    celery_result_backend: str
    cache_ttl_seconds: int = 120

    @computed_field
    @property
    def database_url(self) -> str:
        return (
            f"postgresql+asyncpg://{self.db_user}:{self.db_pass}"
            f"@{self.db_host}:{self.db_port}/{self.db_name}"
        )

settings = Settings()
