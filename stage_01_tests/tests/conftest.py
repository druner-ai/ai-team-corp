import sys
from pathlib import Path

# Ensure src is in path (pytest.ini should handle it, but just in case)
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

import pytest
from md2html.cli import main


@pytest.fixture
def run_cli(capsys):
    """Fixture to run CLI main with given arguments and capture output."""
    def _run(args):
        import sys as _sys
        original_argv = _sys.argv
        try:
            _sys.argv = ["md2html"] + args
            try:
                main()
                exit_code = 0
            except SystemExit as e:
                exit_code = e.code if e.code is not None else 0
        finally:
            _sys.argv = original_argv
        captured = capsys.readouterr()
        return exit_code, captured.out, captured.err
    return _run


@pytest.fixture
def sample_md_content():
    return """# Hello World

This is a paragraph.

## Subheading

- item 1
- item 2
"""


@pytest.fixture
def sample_md_file(tmp_path, sample_md_content):
    """Create a temporary .md file with sample content."""
    md_file = tmp_path / "test.md"
    md_file.write_text(sample_md_content, encoding="utf-8")
    return md_file
