"""Tests for MarkdownRenderer: conversion of various Markdown elements."""
import pytest
from md2html.renderer import MarkdownRenderer


@pytest.fixture
def renderer():
    return MarkdownRenderer()


# ASSERT-10
def test_fenced_code_block_with_language(renderer):
    """ASSERT-10: система ДОЛЖНА преобразовывать блок кода в тройных обратных кавычках в HTML-элемент с тегом `<pre>` и подсветкой синтаксиса через CSS-классы Pygments, если язык указан."""
    md = "```python\nprint('hello')\n```"
    html = renderer.render(md)
    assert "<pre>" in html
    assert "<code" in html
    # Pygments adds class="codehilite" or similar
    assert "codehilite" in html or "highlight" in html


def test_fenced_code_without_language(renderer):
    """Code block without language still produces <pre><code>."""
    md = "```\nplain text\n```"
    html = renderer.render(md)
    assert "<pre>" in html
    assert "<code>" in html


# ASSERT-11
def test_table_conversion(renderer):
    """ASSERT-11: система ДОЛЖНА преобразовывать таблицу в Markdown в HTML-элемент с тегом `<table>`, содержащий `<thead>` и `<tbody>`."""
    md = """| Header 1 | Header 2 |
|----------|----------|
| Cell 1   | Cell 2   |"""
    html = renderer.render(md)
    assert "<table>" in html
    assert "<thead>" in html
    assert "<tbody>" in html


# ASSERT-12
def test_blockquote_conversion(renderer):
    """ASSERT-12: система ДОЛЖНА преобразовывать цитату (строка, начинающаяся с `>`) в HTML-элемент с тегом `<blockquote>`."""
    md = "> This is a quote"
    html = renderer.render(md)
    assert "<blockquote>" in html


# ASSERT-13
def test_ordered_list(renderer):
    """ASSERT-13: система ДОЛЖНА преобразовывать нумерованный список в HTML-элемент с тегом `<ol>`."""
    md = "1. First\n2. Second"
    html = renderer.render(md)
    assert "<ol>" in html
    assert "<li>" in html


def test_unordered_list(renderer):
    """ASSERT-13: ненумерованный список — с тегом `<ul>`."""
    md = "- item\n- another"
    html = renderer.render(md)
    assert "<ul>" in html
    assert "<li>" in html
