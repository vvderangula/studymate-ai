"""Application settings.

Only secrets and per-deployment values belong in ``.env``:

    MONGODB_URI, GEMINI_API_KEY, JWT_SECRET_KEY, ENVIRONMENT, CORS_ORIGINS

Everything else is a product decision and lives here as a code default.
(Any field can still be overridden by an environment variable of the same
name when debugging, but none of them need to be.)
"""

from typing import Annotated

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict

_DEFAULT_JWT_SECRET = "studymate-dev-secret-change-in-production"
_DEV_ENVIRONMENTS = {"development", "dev", "local", "test", "testing"}


class Settings(BaseSettings):
    """Strongly-typed settings, read from the environment or ``.env``."""

    # ---- From .env: secrets and per-deployment values -------------------
    environment: str = "development"
    mongodb_uri: str = ""
    gemini_api_key: str = ""
    jwt_secret_key: str = _DEFAULT_JWT_SECRET
    cors_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    # People who get the admin role when they sign in (comma-separated).
    admin_emails: Annotated[list[str], NoDecode] = []

    # ---- Code defaults ----------------------------------------------------
    app_name: str = "StudyMate AI"
    log_level: str = "INFO"

    # Database name used when MONGODB_URI does not name one.
    mongodb_db: str = "studymate"

    # Uploaded PDF files and the local vector index stay on disk.
    upload_dir: str = "storage/uploads"
    max_upload_size_mb: int = 25
    chroma_dir: str = "storage/chroma"

    # Text chunking and retrieval
    chunk_size: int = 1000
    chunk_overlap: int = 200
    retrieval_top_k: int = 4
    study_tools_top_k: int = 8  # quizzes and notes use broader context

    # Auth
    jwt_algorithm: str = "HS256"
    jwt_expire_days: int = 7

    # AI providers: "gemini" (default) or "huggingface"
    embedding_provider: str = "gemini"
    llm_provider: str = "gemini"
    gemini_embedding_model: str = "gemini-embedding-001"
    gemini_embedding_dimensions: int = 768
    gemini_llm_model: str = "gemini-2.5-flash"
    llm_max_tokens: int = 2048
    llm_temperature: float = 0.2

    # Hugging Face (only used when a provider above is "huggingface")
    hf_api_key: str = ""
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    llm_model_name: str = "meta-llama/Llama-3.1-8B-Instruct"

    @property
    def debug(self) -> bool:
        """Debug mode follows the environment."""

        return self.environment.lower() in _DEV_ENVIRONMENTS

    def role_for(self, email: str) -> str:
        """"admin" for emails listed in ADMIN_EMAILS, otherwise "user"."""

        return "admin" if email.strip().lower() in self.admin_emails else "user"

    @field_validator("admin_emails", mode="before")
    @classmethod
    def split_admin_emails(cls, value: object) -> object:
        """Comma-separated, case-insensitive."""

        if isinstance(value, str):
            return [email.strip().lower() for email in value.split(",") if email.strip()]
        if isinstance(value, list):
            return [str(email).strip().lower() for email in value]
        return value

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, value: object) -> object:
        """Allow CORS origins to be provided as a comma-separated string."""

        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    @model_validator(mode="after")
    def require_real_jwt_secret(self) -> "Settings":
        """Refuse to start outside development with the public default secret."""

        if (
            self.environment.lower() not in _DEV_ENVIRONMENTS
            and self.jwt_secret_key == _DEFAULT_JWT_SECRET
        ):
            raise ValueError(
                "JWT_SECRET_KEY must be set to a private random value when "
                f"ENVIRONMENT={self.environment}. Generate one with: "
                'python -c "import secrets; print(secrets.token_urlsafe(48))"'
            )
        return self

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",  # old .env files with retired keys still load
    )


settings = Settings()
