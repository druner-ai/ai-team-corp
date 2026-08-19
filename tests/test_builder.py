"""Tests for HtmlBuilder: HTML document structure, CSS inlining, DOCTYPE."""
import pytest
from md2html.builder import HtmlBuilder


@pytest.fixture
def builder():
    return HtmlBuilder()


# ASSERT-09
def test_css_inlined_in_style_tag(builder):
    """ASSERT-09: система ДОЛЖНА встраивать все CSS-правила внутри тега `<style>` в `<head>` выходного HTML, не создавая внешних `.css`-файлов и не ссылаясь на внешние ресурсы."""
    html = builder.build("<p>Body</p>", title="Test", css=".test { color: red; }")
    assert "<style>" in html
    assert ".test { color: red; }" in html
    # No external stylesheet links
    assert '<link rel="stylesheet"' not in html


def test_no_external_resources(builder):
    """ASSERT-09: выходной HTML не должен содержать ссылок на внешние ресурсы."""
    html = builder.build("<p>Body</p>", title="Test", css="body { margin: 0; }")
    # No http/https references in head
    head_start = html.find("<head>")
    head_end = html.find("</head>")
    head_content = html[head_start:head_end]
    assert "http://" not in head_content
    assert "https://" not in head_content


# ASSERT-15 (partial: DOCTYPE and first line)
def test_first_line_doctype(builder):
    """ASSERT-15: первая строка файла начинается с `<!DOCTYPE html>`."""
    html = builder.build("<p>Body</p>", title="Test", css="")
    first_line = html.splitlines()[0].strip()
    assert first_line == "<!DOCTYPE html>"


def test_html_structure(builder):
    """Проверка базовой структуры: <html>, <head>, <title>, <body>."""
    html = builder.build("<p>Body</p>", title="My Title", css="")
    assert "<html" in html
    assert "<head>" in html
    assert "<title>My Title</title>" in html
    assert "<body>" in html
    assert "<p>Body</p>" in html


def test_meta_charset(builder):
    """Выходной HTML должен содержать <meta charset="utf-8">."""
    html = builder.build("<p>Body</p>", title="Test", css="")
    assert '<meta charset="utf-8">' in html
