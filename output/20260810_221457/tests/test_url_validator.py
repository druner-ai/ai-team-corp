import pytest
from fastapi import HTTPException
from src.utils.url_validator import validate_url

def test_valid_url():
    assert validate_url("https://example.com") == "https://example.com"

def test_invalid_url():
    with pytest.raises(HTTPException):
        validate_url("")
    with pytest.raises(HTTPException):
        validate_url("ftp://example.com")