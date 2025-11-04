import os
from functools import lru_cache
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parents[2]
ENV_FILE = BASE_DIR / ".env"
if ENV_FILE.exists():
    load_dotenv(ENV_FILE)
else:
    load_dotenv()


class Settings:

    project_name: str = "Sleepy Panda API"
    secret_key: str = os.getenv("SECRET_KEY", "change-me")
    jwt_algorithm: str = os.getenv("JWT_ALGORITHM", "HS256")
    access_token_expire_minutes: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))

    smtp_server: str = os.getenv("SMTP_SERVER", "smtp.gmail.com")
    smtp_port: int = int(os.getenv("SMTP_PORT", "587"))
    email_sender: str | None = os.getenv("EMAIL_SENDER")
    email_password: str | None = os.getenv("EMAIL_PASSWORD")

    database_url: str | None = os.getenv("DATABASE_URL")

    ml_model_dir: Path = BASE_DIR / "ml_model"

    def require(self, value: Any, message: str) -> Any:
        if value is None:
            raise RuntimeError(message)
        return value


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
