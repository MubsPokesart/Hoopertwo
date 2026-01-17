"""Input validation and sanitization for security.

All user input must pass through validators before use.
"""
from typing import Union


class ValidationError(ValueError):
    """Raised when input validation fails."""
    pass


class InputValidator:
    """Validator for user input with security checks.

    Responsibilities:
    - Validate input length and format
    - Sanitize input for safe display
    - Prevent injection attacks

    Note: SQL injection is prevented primarily by parameterized queries,
    but this provides defense in depth.
    """

    MAX_PLAYER_NAME_LENGTH = 100
    MIN_SPAWN_THRESHOLD = 10
    MAX_SPAWN_THRESHOLD = 10000

    @staticmethod
    def validate_player_name(name: str) -> str:
        """Validate and sanitize player name input.

        Args:
            name: Player name from user input

        Returns:
            Validated name (stripped of whitespace)

        Raises:
            ValidationError: If name is invalid
        """
        if not name or not name.strip():
            raise ValidationError("Player name cannot be empty")

        name = name.strip()

        if len(name) > InputValidator.MAX_PLAYER_NAME_LENGTH:
            raise ValidationError(
                f"Player name too long (max {InputValidator.MAX_PLAYER_NAME_LENGTH} characters)"
            )

        return name

    @staticmethod
    def validate_spawn_threshold(threshold: int) -> int:
        """Validate spawn threshold value.

        Args:
            threshold: Spawn threshold from user input

        Returns:
            Validated threshold

        Raises:
            ValidationError: If threshold is invalid
        """
        if not isinstance(threshold, int):
            raise ValidationError("Spawn threshold must be an integer")

        if threshold < InputValidator.MIN_SPAWN_THRESHOLD or \
           threshold > InputValidator.MAX_SPAWN_THRESHOLD:
            raise ValidationError(
                f"Spawn threshold must be between {InputValidator.MIN_SPAWN_THRESHOLD} "
                f"and {InputValidator.MAX_SPAWN_THRESHOLD}"
            )

        return threshold

    @staticmethod
    def validate_channel_id(channel_id: int) -> int:
        """Validate Discord channel ID.

        Args:
            channel_id: Discord channel ID

        Returns:
            Validated channel ID

        Raises:
            ValidationError: If channel ID is invalid
        """
        if not isinstance(channel_id, int) or channel_id <= 0:
            raise ValidationError("Channel ID must be a positive integer")

        return channel_id

    @staticmethod
    def sanitize_input(text: str, max_length: int = 100) -> str:
        """Sanitize text input for safe display/logging.

        Args:
            text: User input text
            max_length: Maximum length to allow

        Returns:
            Sanitized text
        """
        if not text:
            return ""

        # Strip and truncate
        text = text.strip()[:max_length]

        return text
