"""ASSERT-02: маскирование в логах — полные реквизиты 13–34 символа заменяются маской."""

import logging
import io
import pytest
from app.utils.logging_filter import MaskingFilter


class TestMaskingFilter:
    @pytest.fixture
    def log_stream(self):
        """Перехватывает логи в StringIO."""
        stream = io.StringIO()
        handler = logging.StreamHandler(stream)
        handler.setLevel(logging.INFO)
        handler.addFilter(MaskingFilter())
        logger = logging.getLogger("test_masking")
        logger.setLevel(logging.INFO)
        logger.addHandler(handler)
        yield stream
        logger.removeHandler(handler)

    def test_masks_card_number_in_log(self, log_stream):
        """ASSERT-02: 16-значный номер карты маскируется в логе."""
        logger = logging.getLogger("test_masking")
        logger.info("Processing card 4111111111111111")
        output = log_stream.getvalue()
        assert "4111111111111111" not in output
        assert "4111********1111" in output

    def test_masks_iban_in_log(self, log_stream):
        """ASSERT-02: IBAN (22 символа) маскируется в логе."""
        logger = logging.getLogger("test_masking")
        logger.info("Processing IBAN DE89370400440532013000")
        output = log_stream.getvalue()
        assert "DE89370400440532013000" not in output
        assert "DE89****************3000" in output

    def test_does_not_mask_short_numbers(self, log_stream):
        """Короткие числа (менее 13 символов) не маскируются."""
        logger = logging.getLogger("test_masking")
        logger.info("Bik: 044525225")
        output = log_stream.getvalue()
        assert "044525225" in output

    def test_masks_13_char_sequence(self, log_stream):
        """ASSERT-02: последовательность ровно 13 символов маскируется."""
        logger = logging.getLogger("test_masking")
        logger.info("Card: 4222222222222")
        output = log_stream.getvalue()
        assert "4222222222222" not in output
        assert "4222*****2222" in output

    def test_masks_34_char_sequence(self, log_stream):
        """ASSERT-02: последовательность ровно 34 символа маскируется."""
        logger = logging.getLogger("test_masking")
        logger.info("IBAN: AB12345678901234567890123456789012")
        output = log_stream.getvalue()
        assert "AB12345678901234567890123456789012" not in output
        assert "AB12**************************9012" in output
