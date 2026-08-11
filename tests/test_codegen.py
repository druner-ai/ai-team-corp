from src.app.utils.codegen import generate_code


def test_generate_code_length_default():
    code = generate_code()
    assert len(code) == 6


def test_generate_code_length_custom():
    code = generate_code(8)
    assert len(code) == 8


def test_generate_code_characters():
    import string

    allowed = string.digits + string.ascii_lowercase + string.ascii_uppercase
    for length in range(4, 12):
        code = generate_code(length)
        assert len(code) == length
        assert all(c in allowed for c in code)
