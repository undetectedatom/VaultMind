from typing import Annotated

from fastapi import Depends, FastAPI
from app.api.upload import router as upload_router

app = FastAPI(dependencies=[])
app.include_router(upload_router, prefix="/api", dependencies=[])
