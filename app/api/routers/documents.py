from typing import Annotated

from fastapi import APIRouter, Depends, UploadFile
from sqlmodel import Session

from app.api.denpendencies import get_cur_user, get_session
from app.database.models import User

router = APIRouter()


@router.post("upload")
def file_upload(
    files: list[UploadFile],
    session: Annotated[Session, Depends(get_session)],
    user: Annotated[User, Depends(get_cur_user)],
):
    session.add()
