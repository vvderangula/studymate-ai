"""Strongly-typed application settings loaded from environment variables."""

from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    """Application settings.

    Values are read from environment variables or a local ``.env`` file.
    """

    # Application
    app_name: str = "StudyMate AI"
    environment: str = "development"
    debug: bool = True

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    # Logging
    log_level: str = "INFO"

    # CORS
    cors_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]

    # File uploads
    upload_dir: str = "storage/uploads"
    max_upload_size_mb: int = 25

    # Processed chunk storage
    chunks_dir: str = "storage/chunks"

    # Database
    database_path: str = "storage/studymate.db"

    # Text chunking
    chunk_size: int = 1000
    chunk_overlap: int = 200

    # Vector store
    chroma_dir: str = "storage/chroma"
    retrieval_top_k: int = 4

    # Study tools (quiz / notes) use broader context than chat.
    study_tools_top_k: int = 8

    # Hugging Face
    hf_api_key: str = ""
    embedding_model_name: str = "sentence-transformers/all-MiniLM-L6-v2"
    llm_model_name: str = "meta-llama/Llama-3.1-8B-Instruct"
    llm_max_tokens: int = 512
    llm_temperature: float = 0.2

    @field_validator("cors_origins", mode="before")
    @classmethod
    def split_cors_origins(cls, value: object) -> object:
        """Allow CORS origins to be provided as a comma-separated string."""

        if isinstance(value, str):
            return [origin.strip() for origin in value.split(",") if origin.strip()]
        return value

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )


settings = Settings()
