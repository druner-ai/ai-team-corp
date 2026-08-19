"""Tests for FileWriter: UTF-8 encoding, no BOM, DOCTYPE first line."""
import pytest
from md2html.writer import FileWriter


@pytest.fixture
def writer():
    return FileWriter()


# ASSERT-15
def test_output_utf8_no_bom(writer, tmp_path):
    """ASSERT-15: система ДОЛЖНА записывать выходной файл в кодировке UTF-8 без BOM."""
    output_path = tmp_path / "output.html"
    content = "<!DOCTYPE html>\n<html>\n</html>"
    writer.write(output_path, content)
    with open(output_path, "rb") as f:
        raw = f.read()
    # No BOM (EF BB BF)
    assert not raw.startswith(b"\xef\xbb\xbf")
    # Decode as UTF-8
    decoded = raw.decode("utf-8")
    assert decoded == content


def test_first_line_doctype_in_file(writer, tmp_path):
    """ASSERT-15: первая строка файла начинается с `<!DOCTYPE html>`."""
    output_path = tmp_path / "output.html"
    content = "<!DOCTYPE html>\n<html>\n</html>"
    writer.write(output_path, content)
    with open(output_path, "r", encoding="utf-8") as f:
        first_line = f.readline().strip()
    assert first_line == "<!DOCTYPE html>"
