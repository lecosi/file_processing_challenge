from contextlib import asynccontextmanager
from fastapi import FastAPI
from app.api.routers import router as api_router
from app.core.init_db import create_tables


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_tables()
    yield


app = FastAPI(title="File Sales challenge", lifespan=lifespan)

app.include_router(api_router, prefix="/api/v1")