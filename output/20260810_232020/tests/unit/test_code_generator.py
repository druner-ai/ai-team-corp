"""
Unit tests for short code generation.
"""

import pytest
from app.services.code_generator import CodeGenerator


class TestCodeGenerator:
    """Tests for CodeGenerator."""

    def test_generate_default_length(self):
        """Generated code should have the default length."""
        generator = CodeGenerator(code_length=6)
        code = generator.generate(0)
        assert len(code) == 6

    def test_generate_custom_length(self):
        """Generated code should respect custom length."""
        generator = CodeGenerator(code_length=8)
        code = generator.generate(0)
        assert len(code) == 8

    def test_generate_different_inputs(self):
        """Different inputs should produce different codes."""
        generator = CodeGenerator(code_length=6)
        code1 = generator.generate(1)
        code2 = generator.generate(2)
        assert code1 != code2

    def test_generate_same_input_same_output(self):
        """Same input should produce same output (deterministic)."""
        generator = CodeGenerator(code_length=6)
        code1 = generator.generate(100)
        code2 = generator.generate(100)
        assert code1 == code2

    def test_generate_valid_base62(self):
        """Generated code should only contain base62 characters."""
        from app.utils.base62 import BASE62_ALPHABET

        generator = CodeGenerator(code_length=6)
        for i in range(100):
            code = generator.generate(i)
            for char in code:
                assert char in BASE62_ALPHABET, f"Invalid char '{char}' in code '{code}'"

    def test_generate_zero(self):
        """Zero should produce a padded code."""
        generator = CodeGenerator(code_length=6)
        code = generator.generate(0)
        # First char should be '0' (base62 of 0)
        assert code[0] == "0"
        assert len(code) == 6

    def test_generate_large_number(self):
        """Large numbers should produce valid codes."""
        generator = CodeGenerator(code_length=6)
        code = generator.generate(999999999)
        assert len(code) == 6

    def test_generate_with_retry_success(self):
        """generate_with_retry should succeed when code is available."""
        generator = CodeGenerator(code_length=6)

        def is_taken(code: str) -> bool:
            return False  # No codes are taken

        code = generator.generate_with_retry(0, is_taken)
        assert len(code) == 6

    def test_generate_with_retry_failure(self):
        """generate_with_retry should raise after max retries."""
        generator = CodeGenerator(code_length=6)

        def is_taken(code: str) -> bool:
            return True  # All codes are taken

        with pytest.raises(RuntimeError, match="Failed to generate"):
            generator.generate_with_retry(0, is_taken)