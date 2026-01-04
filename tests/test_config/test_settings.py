import os
import pytest
from src.config.settings import Settings


def test_settings_loads_from_environment(monkeypatch):
    """Test that Settings loads configuration from environment variables."""
    monkeypatch.setenv("DISCORD_TOKEN", "test_token_123")
    monkeypatch.setenv("COMMAND_PREFIX", "t!")
    monkeypatch.setenv("DEFAULT_SPAWN_THRESHOLD", "100")

    settings = Settings()

    assert settings.discord_token == "test_token_123"
    assert settings.command_prefix == "t!"
    assert settings.default_spawn_threshold == 100


def test_settings_validates_required_fields():
    """Test that Settings raises error if required fields missing."""
    # Clear DISCORD_TOKEN if it exists
    if "DISCORD_TOKEN" in os.environ:
        del os.environ["DISCORD_TOKEN"]

    with pytest.raises(ValueError, match="DISCORD_TOKEN"):
        Settings()


def test_settings_has_default_values(monkeypatch):
    """Test that Settings provides sensible defaults."""
    monkeypatch.setenv("DISCORD_TOKEN", "test_token")

    settings = Settings()

    assert settings.database_path == "data/hooper_two.db"
    assert settings.image_cache_dir == "data/images"
    assert settings.br_rate_limit_per_minute == 20
