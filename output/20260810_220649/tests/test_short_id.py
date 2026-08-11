import re
from app.core.short_id import generate_short_id

def test_generate_short_id_length():
    sid = generate_short_id(7)
    assert len(sid) == 7
    assert re.fullmatch(r'[a-zA-Z0-9]{7}', sid) is not None

def test_uniqueness():
    ids = {generate_short_id(7) for _ in range(100)}
    assert len(ids) == 100  # extremely unlikely to collide