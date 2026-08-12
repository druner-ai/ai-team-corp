"""MarkdownRenderer: converts Markdown to HTML body."""

import markdown


class MarkdownRenderer:
    """Renders Markdown content to HTML using Python-Markdown with extensions."""

    def __init__(self) -> None:
        self._md = markdown.Markdown(
            extensions=[
                "fenced_code",
                "tables",
                "codehilite",
                "toc",
            ],
            extension_configs={
                "codehilite": {
                    "css_class": "codehilite",
                    "guess_lang": False,
                },
            },
        )

    def render(self, markdown_text: str) -> str:
        """Convert Markdown text to HTML body.

        Args:
            markdown_text: Raw Markdown content.

        Returns:
            HTML string (body content only).
        """
        # Reset the parser for each render to avoid state leakage
        self._md.reset()
        return self._md.convert(markdown_text)
