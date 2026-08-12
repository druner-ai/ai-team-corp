"""CSS utilities: base styles and Pygments CSS."""

from pygments.formatters import HtmlFormatter


# Base CSS for the HTML document
BASE_CSS = """
body {
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    line-height: 1.6;
    max-width: 800px;
    margin: 0 auto;
    padding: 2rem;
    color: #333;
}

h1, h2, h3, h4, h5, h6 {
    margin-top: 1.5em;
    margin-bottom: 0.5em;
    font-weight: 600;
    line-height: 1.25;
}

h1 { font-size: 2em; border-bottom: 1px solid #eee; padding-bottom: 0.3em; }
h2 { font-size: 1.5em; border-bottom: 1px solid #eee; padding-bottom: 0.3em; }
h3 { font-size: 1.25em; }

p { margin: 0 0 1em; }

a { color: #0366d6; text-decoration: none; }
a:hover { text-decoration: underline; }

blockquote {
    margin: 0;
    padding: 0 1em;
    color: #6a737d;
    border-left: 0.25em solid #dfe2e5;
}

table {
    border-collapse: collapse;
    width: 100%;
    margin: 1em 0;
}

thead {
    background-color: #f6f8fa;
}

th, td {
    border: 1px solid #dfe2e5;
    padding: 6px 13px;
    text-align: left;
}

th {
    font-weight: 600;
}

tr:nth-child(even) {
    background-color: #f6f8fa;
}

ul, ol {
    padding-left: 2em;
    margin: 0 0 1em;
}

li { margin: 0.25em 0; }

img {
    max-width: 100%;
    height: auto;
}

pre {
    background-color: #f6f8fa;
    border-radius: 6px;
    padding: 16px;
    overflow: auto;
    font-size: 85%;
    line-height: 1.45;
}

code {
    font-family: "SFMono-Regular", Consolas, "Liberation Mono", Menlo, monospace;
    font-size: 85%;
}

:not(pre) > code {
    background-color: rgba(27,31,35,0.05);
    border-radius: 3px;
    padding: 0.2em 0.4em;
}
"""


def get_pygments_css() -> str:
    """Get CSS for Pygments syntax highlighting.

    Returns:
        CSS string for code highlighting.
    """
    formatter = HtmlFormatter(style="default")
    return formatter.get_style_defs(".codehilite")


def get_all_css() -> str:
    """Get combined CSS: base styles + Pygments highlighting.

    Returns:
        Complete CSS string for the HTML document.
    """
    return BASE_CSS + "\n" + get_pygments_css()
