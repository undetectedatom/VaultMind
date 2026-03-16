from typing import Annotated

from fastapi import Depends, FastAPI
from app.api.upload import router as upload_router

app = FastAPI()
app.include_router(upload_router, prefix="/api")
