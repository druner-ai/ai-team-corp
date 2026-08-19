"""Converter: orchestrates the Markdown-to-HTML conversion process."""

import re
from pathlib import Path

from md2html.builder import HtmlBuilder
from md2html.reader import FileReader
from md2html.renderer import MarkdownRenderer
from md2html.writer import FileWriter


def extract_title(markdown_text: str) -> str:
    """Extract the first H1 heading from Markdown text.

    Args:
        markdown_text: Raw Markdown content.

    Returns:
        Title text from first H1, or "Untitled" if none found.
    """
    # Match lines starting with # (not ##) followed by space and text
    match = re.search(r"^#\s+(.+)$", markdown_text, re.MULTILINE)
    if match:
        return match.group(1).strip()
    return "Untitled"


def determine_output_path(input_path: Path, output_path: Path | None) -> Path:
    """Determine the output HTML file path.

    Args:
        input_path: Path to the input Markdown file.
        output_path: Explicit output path from CLI, or None.

    Returns:
        Resolved output path.
    """
    if output_path is not None:
        return output_path
    return input_path.with_suffix(".html")


def convert(input_path: Path, output_path: Path | None, title: str | None) -> None:
    """Orchestrate the full conversion: read → render → build → write.

    Args:
        input_path: Path to input Markdown file.
        output_path: Explicit output path, or None for default.
        title: Explicit title, or None to extract from Markdown.
    """
    reader = FileReader(max_size_mb=50)
    renderer = MarkdownRenderer()
    builder = HtmlBuilder()
    writer = FileWriter()

    # Read input
    md_content = reader.read(input_path)

    # Determine title
    if title is None:
        title = extract_title(md_content)

    # Render Markdown to HTML body
    html_body = renderer.render(md_content)

    # Build full HTML document
    html_document = builder.build(html_body, title=title)

    # Determine output path
    resolved_output = determine_output_path(input_path, output_path)

    # Write output
    writer.write(resolved_output, html_document)
