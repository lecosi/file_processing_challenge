from fastapi import FastAPI
from app.api.routers import router as api_router
from app.core.init_db import create_tables

app = FastAPI(title="File Sales challenge")

@app.on_event("startup")
def on_startup():
    create_tables()

app.include_router(api_router, prefix="/api/v1")