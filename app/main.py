from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from app.database.engine import create_db_and_tables
from app.api.routers import api_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    # logging.info("Data table created")
    yield


app = FastAPI(dependencies=[], lifespan=lifespan)
app.include_router(api_router, prefix="/api", dependencies=[])
