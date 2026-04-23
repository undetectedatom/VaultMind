from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from pwdlib import PasswordHash
from sqlmodel import Session, select

from app.api.denpendencies import get_cur_user, get_session
from app.database.models import User, UserCreate, UserPublic

router = APIRouter()


password_hash = PasswordHash.recommended()


@router.post(
    "/register", response_model=UserPublic, status_code=status.HTTP_201_CREATED
)
def register_user(user: UserCreate, session: Annotated[Session, Depends(get_session)]):
    statement = select(User).where(
        (User.username == user.username) | (User.email == user.email)
    )
    existing_user = session.exec(statement).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this username or email already exists.",
        )
    user.password = password_hash.hash(user.password)
    db_user = User.model_validate(user)
    session.add(db_user)
    session.commit()
    return db_user


@router.get("/test", response_model=UserPublic)
def get_info_test(user: Annotated[User, Depends(get_cur_user)]):
    return user
