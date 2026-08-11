import pytest
from sqlalchemy.ext.asyncio import AsyncSession
from src.services.id_generator import generate_unique_id

@pytest.mark.asyncio
async def test_generates_unique_id(db_session: AsyncSession):
    id1 = await generate_unique_id(db_session)
    id2 = await generate_unique_id(db_session)
    assert len(id1) == 7
    assert id1 != id2