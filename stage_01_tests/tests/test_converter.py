"""Tests for converter orchestration: title extraction, output path logic."""
import pytest
from md2html.converter import extract_title, determine_output_path


# ASSERT-07
def test_title_from_first_h1():
    """ASSERT-07: система ДОЛЖНА использовать текст первого заголовка первого уровня (`# …`) входного Markdown в качестве содержимого тега `<title>`, если флаг `--title` не передан и такой заголовок существует."""
    md = "# Main Title\n\nSome text.\n# Another H1"
    assert extract_title(md) == "Main Title"


def test_title_from_h1_with_whitespace():
    """ASSERT-07: заголовок с пробелами после #."""
    md = "#    Spaced Title   \n\ncontent"
    assert extract_title(md) == "Spaced Title"


# ASSERT-08
def test_title_default_untitled():
    """ASSERT-08: система ДОЛЖНА использовать строку `Untitled` в качестве содержимого тега `<title>`, если флаг `--title` не передан и во входном файле нет заголовков первого уровня."""
    md = "No H1 here\n\n## Subheading"
    assert extract_title(md) == "Untitled"


def test_title_default_untitled_empty():
    """ASSERT-08: пустой Markdown."""
    assert extract_title("") == "Untitled"


# Tests for output path logic
def test_output_path_default(tmp_path):
    """Default output path replaces .md with .html."""
    input_path = tmp_path / "doc.md"
    expected = tmp_path / "doc.html"
    assert determine_output_path(input_path, None) == expected


def test_output_path_custom(tmp_path):
    """Custom output path is used as-is."""
    input_path = tmp_path / "doc.md"
    custom = tmp_path / "out/custom.html"
    assert determine_output_path(input_path, custom) == custom
