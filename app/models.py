from sqlalchemy import Column, Integer, String, DateTime, func
from app.database import Base


class URL(Base):
    __tablename__ = "urls"

    id = Column(Integer, primary_key=True, index=True)
    short_code = Column(String, unique=True, index=True, nullable=False)
    original_url = Column(String, nullable=False)
    created_at = Column(DateTime, server_default=func.now())
    last_visited_at = Column(DateTime, nullable=True)
    visits = Column(Integer, default=0)
