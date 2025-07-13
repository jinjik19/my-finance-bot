import urllib

from pydantic import PostgresDsn, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
    )

    # --- Telegram ---
    bot_token: str
    allowed_telegram_ids: list[int]

    # --- DB connection parts ---
    postgres_user: str
    postgres_password: str
    postgres_host: str
    postgres_db: str
    postgres_port: int = 5432
    database_url: PostgresDsn | None = None

    # --- DB connection parts ---
    metabase_url: str | None = None

    @model_validator(mode='after')
    def assemble_db_connection(self) -> 'Settings':
        """Assembles the database_url from its parts."""
        encoded_password = urllib.parse.quote(self.postgres_password)
        self.database_url = f"postgresql+asyncpg://{self.postgres_user}:{encoded_password}@{self.postgres_host}:{self.postgres_port}/{self.postgres_db}"

        return self

settings = Settings()
