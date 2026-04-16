from contextlib import asynccontextmanager
import logging

from fastapi import FastAPI
from app.database import create_db_and_tables
from app.api.upload import router as upload_router
from app.api.user import router as user_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    logging.info("Data table created")
    yield


app = FastAPI(dependencies=[], lifespan=lifespan)
app.include_router(upload_router, prefix="/api", dependencies=[])
app.include_router(user_router)
