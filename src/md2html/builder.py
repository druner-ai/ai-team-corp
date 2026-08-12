"""HtmlBuilder: assembles the final HTML document."""

from md2html.css import get_all_css


class HtmlBuilder:
    """Builds a complete standalone HTML document from rendered Markdown."""

    def build(self, html_body: str, title: str, css: str | None = None) -> str:
        """Assemble the full HTML document.

        Args:
            html_body: Rendered HTML body content.
            title: Text for the <title> tag.
            css: CSS to embed in <style> tag. If None, uses default CSS.

        Returns:
            Complete HTML document as string.
        """
        if css is None:
            css = get_all_css()

        return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<title>{self._escape_html(title)}</title>
<style>
{css}
</style>
</head>
<body>
{html_body}
</body>
</html>"""

    @staticmethod
    def _escape_html(text: str) -> str:
        """Escape special HTML characters in text.

        Args:
            text: Raw text to escape.

        Returns:
            HTML-escaped string.
        """
        return (
            text.replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;")
            .replace("'", "&#39;")
        )
