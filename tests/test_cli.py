"""Tests for CLI layer: argument parsing, exit codes, error messages."""
import os
import stat
from pathlib import Path
from html.parser import HTMLParser

import pytest


class TitleFinder(HTMLParser):
    """Simple parser to extract <title> text."""
    def __init__(self):
        super().__init__()
        self.in_title = False
        self.title = None

    def handle_starttag(self, tag, attrs):
        if tag == "title":
            self.in_title = True

    def handle_data(self, data):
        if self.in_title:
            self.title = data

    def handle_endtag(self, tag):
        if tag == "title":
            self.in_title = False


def get_html_title(html_path):
    """Extract <title> text from an HTML file."""
    parser = TitleFinder()
    parser.feed(html_path.read_text(encoding="utf-8"))
    return parser.title


# ASSERT-01
def test_successful_conversion_creates_html_next_to_input(run_cli, sample_md_file):
    """ASSERT-01: система ДОЛЖНА завершаться с кодом 0 и создавать файл с расширением .html рядом с входным файлом при передаче валидного .md-файла без дополнительных флагов."""
    exit_code, out, err = run_cli([str(sample_md_file)])
    assert exit_code == 0
    assert out == ""
    assert err == ""
    expected_html = sample_md_file.with_suffix(".html")
    assert expected_html.exists()
    # Check that it's a valid HTML file (first line DOCTYPE)
    content = expected_html.read_text(encoding="utf-8")
    assert content.lstrip().startswith("<!DOCTYPE html>")


# ASSERT-02
def test_no_arguments_shows_help_and_exit_code_2(run_cli):
    """ASSERT-02: система ДОЛЖНА завершаться с кодом 2 и печатать текст справки в stdout при вызове без аргументов."""
    exit_code, out, err = run_cli([])
    assert exit_code == 2
    assert "usage:" in out.lower() or "usage:" in out  # help text
    assert err == ""


# ASSERT-03
def test_file_not_found_error(run_cli, tmp_path):
    """ASSERT-03: система ДОЛЖНА завершаться с кодом 1 и печатать в stderr строку, начинающуюся с `Error: file not found:`, при передаче пути к несуществующему файлу."""
    nonexistent = tmp_path / "nonexistent.md"
    exit_code, out, err = run_cli([str(nonexistent)])
    assert exit_code == 1
    assert out == ""
    assert err.startswith("Error: file not found:")


# ASSERT-04
def test_file_not_readable_error(run_cli, tmp_path):
    """ASSERT-04: система ДОЛЖНА завершаться с кодом 1 и печатать в stderr строку, начинающуюся с `Error: cannot read file:`, при передаче пути к файлу без прав на чтение."""
    unreadable = tmp_path / "unreadable.md"
    unreadable.write_text("content")
    # Remove read permissions
    unreadable.chmod(0o000)
    try:
        exit_code, out, err = run_cli([str(unreadable)])
        assert exit_code == 1
        assert out == ""
        assert err.startswith("Error: cannot read file:")
    finally:
        # Restore permissions so tmp_path cleanup works
        unreadable.chmod(0o644)


# ASSERT-05
def test_output_flag_creates_file_at_specified_path(run_cli, sample_md_file, tmp_path):
    """ASSERT-05: система ДОЛЖНА создавать выходной файл по пути, заданному флагом `-o`, если этот флаг передан."""
    output_path = tmp_path / "custom_output.html"
    exit_code, out, err = run_cli([str(sample_md_file), "-o", str(output_path)])
    assert exit_code == 0
    assert out == ""
    assert err == ""
    assert output_path.exists()
    # Ensure default output next to input is NOT created
    default_output = sample_md_file.with_suffix(".html")
    assert not default_output.exists()


# ASSERT-06
def test_title_flag_sets_html_title(run_cli, sample_md_file, tmp_path):
    """ASSERT-06: система ДОЛЖНА использовать значение флага `--title` в качестве содержимого тега `<title>` выходного HTML, если флаг передан."""
    output_path = tmp_path / "titled.html"
    exit_code, out, err = run_cli([str(sample_md_file), "-o", str(output_path), "--title", "My Custom Title"])
    assert exit_code == 0
    title = get_html_title(output_path)
    assert title == "My Custom Title"


# ASSERT-14
def test_file_too_large_error(run_cli, tmp_path):
    """ASSERT-14: система ДОЛЖНА завершаться с кодом 1 и печатать в stderr строку, начинающуюся с `Error: file too large`, если размер входного файла превышает 50 МБ."""
    large_file = tmp_path / "large.md"
    # Create a sparse file of 51 MB without writing actual data
    with open(large_file, "wb") as f:
        f.seek(51 * 1024 * 1024 - 1)
        f.write(b"\0")
    exit_code, out, err = run_cli([str(large_file)])
    assert exit_code == 1
    assert out == ""
    assert err.startswith("Error: file too large")
