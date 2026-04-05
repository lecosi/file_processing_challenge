from app.core.database import engine
from app.models.base import Base

# Importar todos los modelos para que Base.metadata los conozca
import app.models.jobs   # noqa: F401
import app.models.sales  # noqa: F401


def create_tables():
    Base.metadata.create_all(bind=engine)