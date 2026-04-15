import os
from aiofiles.tempfile import NamedTemporaryFile
from fastapi import Depends, APIRouter, BackgroundTasks, UploadFile
from app.api.convert import file_embedding
from app.dependencies import SysSettings, get_sys_settings

router = APIRouter()


# This is cpu bounded, so I use a blocking function here. This allows a separate worker thread for BackgroundTasks.
def process_data(files, vector_database):
    try:
        file_embedding(files, vector_database)
    finally:
        for file in files:
            os.remove(file)


# I need a well rounded api routing design.
@router.post("/upload")
async def file_upload(
    files: list[UploadFile],
    background_task: BackgroundTasks,
    sys_path: SysSettings = Depends(get_sys_settings),
):

    temp_files = []
    for file in files:
        async with NamedTemporaryFile(
            "wb", dir=sys_path.temp_file, delete=False
        ) as buffer:
            while chunk := await file.read(1024 * 1024):
                await buffer.write(chunk)
            await buffer.flush()
            temp_files.append(buffer.name)
        background_task.add_task(process_data, temp_files, sys_path.vector_database)

    return {"message": "Upload started"}
