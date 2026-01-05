import pytest
from src.utils.text_normalizer import TextNormalizer


def test_normalize_removes_accents():
    """Test that accents are removed from text."""
    assert TextNormalizer.normalize("Nikola Jokić") == "nikola jokic"
    assert TextNormalizer.normalize("Luka Dončić") == "luka doncic"


def test_normalize_removes_dots():
    """Test that dots are removed."""
    assert TextNormalizer.normalize("J.R. Smith") == "jr smith"
    assert TextNormalizer.normalize("C.J. McCollum") == "cj mccollum"


def test_normalize_removes_dashes():
    """Test that dashes are normalized to spaces."""
    assert TextNormalizer.normalize("Karl-Anthony Towns") == "karl anthony towns"
    assert TextNormalizer.normalize("Michael Kidd-Gilchrist") == "michael kidd gilchrist"


def test_normalize_is_case_insensitive():
    """Test that normalization is case insensitive."""
    assert TextNormalizer.normalize("LEBRON JAMES") == "lebron james"
    assert TextNormalizer.normalize("LeBron James") == "lebron james"
    assert TextNormalizer.normalize("lebron james") == "lebron james"


def test_normalize_handles_multiple_spaces():
    """Test that extra spaces are collapsed."""
    assert TextNormalizer.normalize("Kevin   Durant") == "kevin durant"
    assert TextNormalizer.normalize("  Stephen Curry  ") == "stephen curry"


def test_normalize_handles_apostrophes():
    """Test that apostrophes are removed."""
    assert TextNormalizer.normalize("DeAndre' Bembry") == "deandre bembry"
    assert TextNormalizer.normalize("O'Neal") == "oneal"
