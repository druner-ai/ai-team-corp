"""CLI entry point for md2html."""

import argparse
import sys
from pathlib import Path

from md2html.converter import convert
from md2html.errors import Md2HtmlError


def build_parser() -> argparse.ArgumentParser:
    """Build the argument parser for md2html.

    Returns:
        Configured ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        prog="md2html",
        description="Convert Markdown to standalone HTML",
    )
    parser.add_argument(
        "input",
        nargs="?",
        help="Path to input Markdown file",
    )
    parser.add_argument(
        "-o", "--output",
        type=Path,
        default=None,
        help="Path to output HTML file (default: <input>.html)",
    )
    parser.add_argument(
        "--title",
        type=str,
        default=None,
        help="Custom title for the HTML document",
    )
    return parser


def main() -> None:
    """Main entry point for the md2html CLI."""
    parser = build_parser()

    # If no arguments provided, print help and exit with code 2
    if len(sys.argv) == 1:
        parser.print_help()
        sys.exit(2)

    args = parser.parse_args()

    # If input is not provided after parsing (shouldn't happen with nargs='?',
    # but handle gracefully)
    if args.input is None:
        parser.print_help()
        sys.exit(2)

    input_path = Path(args.input)

    try:
        convert(
            input_path=input_path,
            output_path=args.output,
            title=args.title,
        )
    except Md2HtmlError as e:
        print(e.message, file=sys.stderr)
        sys.exit(e.exit_code)
