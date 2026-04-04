from pydantic_core import ValidationError
from app.core.database import engine
from app.models.jobs import Base

def create_tables():
    try:
        Base.metadata.create_all(bind=engine)
    except Exception as e:
        raise ValidationError('Error creating tables')