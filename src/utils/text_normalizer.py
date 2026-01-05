"""Text normalization utilities for player name matching.

Handles case, accents, punctuation, and whitespace normalization
to enable flexible player name recognition.
"""
import unicodedata
import re


class TextNormalizer:
    """Utility class for normalizing text for comparison.

    Responsibilities:
    - Remove accents (Jokić → Jokic)
    - Remove dots (J.R. → JR)
    - Normalize dashes to spaces (Karl-Anthony → Karl Anthony)
    - Lowercase everything
    - Collapse multiple spaces
    """

    @staticmethod
    def normalize(text: str) -> str:
        """Normalize text for comparison.

        Args:
            text: Input text to normalize

        Returns:
            Normalized text (lowercase, no accents/punctuation, collapsed spaces)
        """
        # Remove accents using Unicode normalization
        text = unicodedata.normalize('NFKD', text)
        text = ''.join(c for c in text if not unicodedata.combining(c))

        # Convert to lowercase
        text = text.lower()

        # Remove dots and apostrophes
        text = text.replace('.', '')
        text = text.replace("'", '')

        # Convert dashes to spaces
        text = text.replace('-', ' ')

        # Collapse multiple spaces to single space
        text = re.sub(r'\s+', ' ', text)

        # Strip leading/trailing whitespace
        text = text.strip()

        return text
