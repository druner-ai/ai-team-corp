"""FileReader: reads input Markdown file with validation."""

from pathlib import Path

from md2html.errors import Md2HtmlError


class FileReader:
    """Reads and validates input Markdown files."""

    def __init__(self, max_size_mb: int = 50) -> None:
        self._max_size_bytes = max_size_mb * 1024 * 1024

    def read(self, path: Path) -> str:
        """Read file content with validation.

        Args:
            path: Path to the input Markdown file.

        Returns:
            File content as string.

        Raises:
            Md2HtmlError: If file not found, not readable, or too large.
        """
        if not path.exists():
            raise Md2HtmlError(f"Error: file not found: {path}", exit_code=1)

        if not path.is_file():
            raise Md2HtmlError(f"Error: file not found: {path}", exit_code=1)

        # Check size before reading
        try:
            file_size = path.stat().st_size
        except PermissionError:
            raise Md2HtmlError(f"Error: cannot read file: {path}", exit_code=1)

        if file_size > self._max_size_bytes:
            raise Md2HtmlError(f"Error: file too large", exit_code=1)

        try:
            return path.read_text(encoding="utf-8")
        except PermissionError:
            raise Md2HtmlError(f"Error: cannot read file: {path}", exit_code=1)
        except Exception:
            raise Md2HtmlError(f"Error: cannot read file: {path}", exit_code=1)
