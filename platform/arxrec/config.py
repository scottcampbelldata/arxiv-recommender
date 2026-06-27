"""Central configuration loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

REPO_ROOT = Path(__file__).resolve().parent.parent
load_dotenv(REPO_ROOT / ".env")


@dataclass(frozen=True)
class Settings:
    pg_host: str = field(default_factory=lambda: os.getenv("PGHOST", "localhost"))
    pg_port: int = field(default_factory=lambda: int(os.getenv("PGPORT", "5432")))
    pg_db: str = field(default_factory=lambda: os.getenv("PGDATABASE", "arxiv_recs"))
    pg_user: str = field(default_factory=lambda: os.getenv("PGUSER", "arxrec_app"))
    pg_pw: str = field(default_factory=lambda: os.getenv("PGPASSWORD", ""))
    seed: int = field(default_factory=lambda: int(os.getenv("RANDOM_SEED", "20260625")))
    api_host: str = field(default_factory=lambda: os.getenv("ARXREC_API_HOST", "127.0.0.1"))
    api_port: int = field(default_factory=lambda: int(os.getenv("ARXREC_API_PORT", "8820")))
    default_k: int = field(default_factory=lambda: int(os.getenv("ARXREC_DEFAULT_K", "10")))
    log_level: str = field(default_factory=lambda: os.getenv("ARXREC_LOG_LEVEL", "INFO"))
    cors_origins: str = field(
        default_factory=lambda: os.getenv(
            "ARXREC_CORS_ORIGINS",
            "http://localhost:3000,http://127.0.0.1:3000",
        )
    )
    openalex_mailto: str = field(default_factory=lambda: os.getenv("OPENALEX_MAILTO", ""))
    repo_root: Path = REPO_ROOT
    data_raw: Path = REPO_ROOT / "data" / "raw"
    data_processed: Path = REPO_ROOT / "data" / "processed"
    data_models: Path = REPO_ROOT / "data" / "models"

    @property
    def dsn(self) -> str:
        return (
            f"postgresql://{self.pg_user}:{self.pg_pw}"
            f"@{self.pg_host}:{self.pg_port}/{self.pg_db}"
        )

    @property
    def sqlalchemy_url(self) -> str:
        return (
            f"postgresql+psycopg://{self.pg_user}:{self.pg_pw}"
            f"@{self.pg_host}:{self.pg_port}/{self.pg_db}"
        )


SETTINGS = Settings()
