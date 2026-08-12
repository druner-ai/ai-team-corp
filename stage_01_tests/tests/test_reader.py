"""Tests for FileReader: file existence, permissions, size limit."""
import pytest
from md2html.reader import FileReader
from md2html.errors import Md2HtmlError


@pytest.fixture
def reader():
    return FileReader(max_size_mb=50)


# ASSERT-03
def test_read_nonexistent_file_raises(reader, tmp_path):
    """ASSERT-03: при передаче пути к несуществующему файлу поднимается Md2HtmlError с сообщением 'file not found'."""
    path = tmp_path / "missing.md"
    with pytest.raises(Md2HtmlError) as exc_info:
        reader.read(path)
    assert "file not found" in str(exc_info.value).lower()
    assert exc_info.value.exit_code == 1


# ASSERT-04
def test_read_unreadable_file_raises(reader, tmp_path):
    """ASSERT-04: при передаче пути к файлу без прав на чтение поднимается Md2HtmlError с сообщением 'cannot read file'."""
    path = tmp_path / "unreadable.md"
    path.write_text("content")
    path.chmod(0o000)
    try:
        with pytest.raises(Md2HtmlError) as exc_info:
            reader.read(path)
        assert "cannot read file" in str(exc_info.value).lower()
        assert exc_info.value.exit_code == 1
    finally:
        path.chmod(0o644)


# ASSERT-14
def test_read_file_too_large_raises(reader, tmp_path):
    """ASSERT-14: если размер файла превышает лимит, поднимается Md2HtmlError с сообщением 'file too large'."""
    path = tmp_path / "large.md"
    # Create a sparse file of 51 MB
    with open(path, "wb") as f:
        f.seek(51 * 1024 * 1024 - 1)
        f.write(b"\0")
    with pytest.raises(Md2HtmlError) as exc_info:
        reader.read(path)
    assert "file too large" in str(exc_info.value).lower()
    assert exc_info.value.exit_code == 1


def test_read_valid_file_returns_content(reader, tmp_path):
    """Успешное чтение возвращает содержимое файла."""
    path = tmp_path / "valid.md"
    content = "# Hello"
    path.write_text(content, encoding="utf-8")
    result = reader.read(path)
    assert result == content
