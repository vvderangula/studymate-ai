"""Unit tests for application settings."""

from app.core.config.settings import Settings


def test_default_settings_have_expected_values() -> None:
    """Defaults should be populated for a development environment."""

    settings = Settings()

    assert settings.app_name == "StudyMate AI"
    assert settings.max_upload_size_mb == 25
    assert settings.embedding_model_name


def test_cors_origins_accepts_comma_separated_string() -> None:
    """A comma-separated string should be split into a clean list."""

    settings = Settings(cors_origins="http://a.com, http://b.com ,")

    assert settings.cors_origins == ["http://a.com", "http://b.com"]


def test_cors_origins_accepts_list() -> None:
    """A list value should be preserved as-is."""

    origins = ["http://a.com", "http://b.com"]
    settings = Settings(cors_origins=origins)

    assert settings.cors_origins == origins
