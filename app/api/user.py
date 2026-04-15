from typing import Annotated

from sqlmodel import Session, select

from app.api.database import User, UserCreate, UserPublic, get_session
from fastapi import APIRouter, Depends, HTTPException, status
from app.dependencies import get_sys_settings
from pwdlib import PasswordHash
from fastapi.security import OAuth2AuthorizationCodeBearer, OAuth2PasswordRequestForm
import jwt


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
    user = User(**user)
    session.add(user)
    session.commit()
    return user


def authenticate_user(
    session: Session,
    username_or_email: str,
    password: str,
):
    statement = select(User).where(
        (User.username == username_or_email) | (User.email == username_or_email)
    )
    user = session.exec(statement).first()
    if user and password_hash.verify(password, user.password):
        return user
    password_hash.hash(get_sys_settings().dummy_pwd)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username, email, or password.",
        headers={"WWW-Authenticate": "bearer"},
    )


@router.post("/token")
def users_login(
    session: Annotated[Session, Depends(get_session)],
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
):
    user = authenticate_user(session, form_data.username, form_data.password)
