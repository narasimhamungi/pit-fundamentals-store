from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")
    log_level: str = "INFO"
    log_file: str = "logs/pit_fundamentals_store.log"
    sec_user_agent: str = "pit-fundamentals-store YourName your.email@example.com"
    sec_request_delay_seconds: float = 0.25
    sec_timeout_seconds: float = 30.0
    sec_base_url: str = "https://data.sec.gov"
    sec_archives_url: str = "https://www.sec.gov/Archives/edgar/data"
    postgres_host: str = "localhost"
    # 5433, matching docker-compose.yml's host-side mapping — not the
    # container-internal 5432. Kept out of sync deliberately: this avoids
    # colliding with marketdata-lakehouse's own docker-compose postgres,
    # which maps host 5432. Override via POSTGRES_PORT if your setup
    # differs (e.g. a Postgres server outside Docker on the standard port).
    postgres_port: int = 5433
    postgres_db: str = "pit_fundamentals"
    postgres_user: str = "pit_user"
    postgres_password: str = "pit_password"
    historical_start_year: int = 2010
    historical_end_year: int = 2026
    sample_ciks: str = "320193"
    tickers: str = ""
    schema_path: str | None = None

    @property
    def database_url(self) -> str:
        return f"postgresql://{self.postgres_user}:{self.postgres_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

    @property
    def ciks(self) -> list[int]:
        return [int(x.strip()) for x in self.sample_ciks.split(",") if x.strip().isdigit()]

    @property
    def ticker_list(self) -> list[str]:
        return [t.strip() for t in self.tickers.split(",") if t.strip()]


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()