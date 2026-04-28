import logging
import os
import uuid

import aiofiles
from fastapi import UploadFile

from app.database.models import Document
from app.settings import sys_settings


async def save_file_to_disk(file: UploadFile, document_id: uuid.UUID | str):
    try:
        file_path = os.path.join(
            sys_settings.user_documents, f"{document_id}_{file.filename}"
        )
        async with aiofiles.open(file_path, "wb") as out_file:
            while chunk := await file.read(1024 * 1024):
                await out_file.write(chunk)
        return file_path
    except Exception as e:
        logging.error(e)
        raise e


def delete_file_from_disk(document: Document):
    try:
        if os.path.exists(document.file_path):
            os.remove(document.file_path)
    except Exception:
        pass
