from typing import Annotated
import uuid

from fastapi import (
    APIRouter,
    Depends,
    HTTPException,
    UploadFile,
    BackgroundTasks,
    status,
)
from sqlmodel import Session, select
from app.api.denpendencies import get_cur_user, get_session
from app.database.models import Document, DocumentPublic, DocumentStatus, User
from app.services.document_service import (
    delte_file_from_disk,
    save_file_to_disk,
    process_and_embed_document,
)
from app.services.vector_database import delete_vectors

router = APIRouter()


def verify_file(file: UploadFile):
    if len(file) == 0:
        return False


@router.post("/upload")
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
            prohibited_files.append(file.filename)
            continue
        doc = Document(filename=file.filename, file_path="", user_id=user.id)
        session.add(doc)
        session.commit()
        try:
            doc.file_path = await save_file_to_disk(file, doc.id)
            doc.upload_status = DocumentStatus.PROCESSING
        except Exception:
            prohibited_files.append(file.filename)
            doc.upload_status = DocumentStatus.FAILED
        session.add(doc)
        session.commit()
        processing_docs.append(doc.id)
        background_task.add_task(
            process_and_embed_document, doc.file_path, doc.id, user.id
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


@router.get("", response_model=list[DocumentPublic])
async def get_document_list(
    session: Annotated[Session, Depends(get_session)],
    user: Annotated[User, Depends(get_cur_user)],
):
    statement = select(Document).where(Document.user_id == user.id)
    docs = session.exec(statement).all()
    return docs


@router.get("/{doc_id}")
async def get_document_status(
    doc_id: uuid.UUID,
    session: Annotated[Session, Depends(get_session)],
    user: Annotated[User, Depends(get_cur_user)],
):
    statement = select(Document).where(Document.id == doc_id)
    doc = session.exec(statement).first()
    if not doc or doc.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document can not be found."
        )
    return {"id": doc.id, "status": doc.upload_status}


@router.delete("/{doc_id}")
async def delete_document(
    doc_id: uuid.UUID,
    session: Annotated[Session, Depends(get_session)],
    user: Annotated[User, Depends(get_cur_user)],
):
    statement = select(Document).where(Document.id == doc_id)
    doc = session.exec(statement).first()
    if not doc or doc.user_id != user.id:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document can not be found."
        )
    delete_vectors(user.id, doc.id)
    delte_file_from_disk(document=doc)
    session.delete(doc)
    session.commit()
    return {"message": "Document has been deleted.", "status": status.HTTP_200_OK}
