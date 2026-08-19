"""FileWriter: writes output HTML file."""

from pathlib import Path


class FileWriter:
    """Writes HTML content to a file with UTF-8 encoding without BOM."""

    def write(self, path: Path, content: str) -> None:
        """Write content to file.

        Args:
            path: Output file path.
            content: HTML content to write.
        """
        # Ensure parent directory exists
        path.parent.mkdir(parents=True, exist_ok=True)
        # Write UTF-8 without BOM (default in Python)
        path.write_text(content, encoding="utf-8")
