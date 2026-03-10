from typing import Annotated
import os
import aiofiles
from fastapi import APIRouter, UploadFile

router = APIRouter()
DATA_PATH = "~/data/static/app/"


@router.post("/upload")
async def file_upload(files: list[UploadFile]):
    for file in files:
        async with aiofiles.open(
            os.path.join(DATA_PATH, file.filename), "wb"
        ) as buffer:
            while chunk := await file.read(1024 * 1024):
                await buffer.write(chunk)
    return
