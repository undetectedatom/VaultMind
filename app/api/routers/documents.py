from typing import Annotated

from fastapi import APIRouter, Depends, UploadFile, BackgroundTasks
from sqlmodel import Session
from app.api.denpendencies import get_cur_user, get_session
from app.database.models import Document, DocumentStatus, User
from app.services.document_service import save_file_to_disk, process_and_embed_document

router = APIRouter()


def verify_file(file: UploadFile):
    if len(file) == 0:
        return False


@router.post("upload")
async def file_upload(
    files: list[UploadFile],
    background_task: BackgroundTasks,
    session: Annotated[Session, Depends(get_session)],
    user: Annotated[User, Depends(get_cur_user)],
):
    processing_docs = []
    prohibited_files = []
    for file in files:
        if not verify_file():
            prohibited_files.append(file)
            continue
        doc = Document(filename=file.filename, file_path="", user_id=user.id)
        session.add(doc)
        session.commit()
        doc.file_path = await save_file_to_disk(file, doc.id)
        doc.upload_status = DocumentStatus.PROCESSING
        session.add(doc)
        session.commit()
        processing_docs.append(doc.id)
        background_task.add_task(
            process_and_embed_document,
            doc.file_path,
        )
    if not prohibited_files:
        return {
            "message": "Files upload successfully.",
            "processing_documents": processing_docs,
        }
    return {
        "message": "One or several files upload failed.",
        "processing_documents": processing_docs,
        "failed_files": prohibited_files,
    }
