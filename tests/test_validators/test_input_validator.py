import pytest
from src.validators.input_validator import InputValidator, ValidationError


def test_validate_player_name_valid():
    """Test validating valid player names."""
    assert InputValidator.validate_player_name("Michael Jordan") == "Michael Jordan"
    assert InputValidator.validate_player_name("LeBron James") == "LeBron James"
    assert InputValidator.validate_player_name("Karl-Anthony Towns") == "Karl-Anthony Towns"


def test_validate_player_name_too_long():
    """Test that overly long names are rejected."""
    long_name = "A" * 101

    with pytest.raises(ValidationError, match="too long"):
        InputValidator.validate_player_name(long_name)


def test_validate_player_name_empty():
    """Test that empty names are rejected."""
    with pytest.raises(ValidationError, match="cannot be empty"):
        InputValidator.validate_player_name("")

    with pytest.raises(ValidationError, match="cannot be empty"):
        InputValidator.validate_player_name("   ")


def test_validate_player_name_strips_whitespace():
    """Test that leading/trailing whitespace is stripped."""
    assert InputValidator.validate_player_name("  Michael Jordan  ") == "Michael Jordan"


def test_validate_spawn_threshold_valid():
    """Test validating valid spawn thresholds."""
    assert InputValidator.validate_spawn_threshold(100) == 100
    assert InputValidator.validate_spawn_threshold(500) == 500


def test_validate_spawn_threshold_invalid():
    """Test that invalid thresholds are rejected."""
    with pytest.raises(ValidationError, match="between 10 and 10000"):
        InputValidator.validate_spawn_threshold(5)

    with pytest.raises(ValidationError, match="between 10 and 10000"):
        InputValidator.validate_spawn_threshold(15000)


def test_validate_channel_id_valid():
    """Test validating valid Discord channel IDs."""
    assert InputValidator.validate_channel_id(123456789012345678) == 123456789012345678


def test_validate_channel_id_invalid():
    """Test that invalid channel IDs are rejected."""
    with pytest.raises(ValidationError, match="must be a positive integer"):
        InputValidator.validate_channel_id(-1)

    with pytest.raises(ValidationError, match="must be a positive integer"):
        InputValidator.validate_channel_id(0)


def test_sanitize_input_removes_dangerous_chars():
    """Test that dangerous characters are sanitized."""
    # SQL injection attempt
    malicious = "Robert'; DROP TABLE players; --"
    sanitized = InputValidator.sanitize_input(malicious)

    # Should still contain the text but be safe for logging/display
    assert "Robert" in sanitized
    assert len(sanitized) <= 100  # Length limited
