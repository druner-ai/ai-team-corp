"""Custom exceptions for md2html."""


class Md2HtmlError(Exception):
    """Base exception for md2html with exit code."""

    def __init__(self, message: str, exit_code: int = 1) -> None:
        super().__init__(message)
        self.message = message
        self.exit_code = exit_code
