import logging
from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pwdlib import PasswordHash
from sqlmodel import Session, select

from app.database import User, UserCreate, UserPublic, get_session
from app.settings import Token, get_sys_settings

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


def authenticate_user(
    session: Session,
    username_or_email: str,
    password: str,
):
    statement = select(User).where(
        (User.username == username_or_email) | (User.email == username_or_email)
    )
    user = session.exec(statement).first()
    if user:
        if password_hash.verify(password, user.password):
            return user
    else:
        password_hash.verify(password, get_sys_settings().dummy_pwd)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Incorrect username, email, or password.",
        headers={"WWW-Authenticate": "bearer"},
    )


def create_token(data_dict: dict, expires_delta: timedelta = timedelta(minutes=30)):
    data_dict = data_dict.copy()
    expires = datetime.now(timezone.utc) + expires_delta
    data_dict.update({"exp": expires})
    encoded_jwt = jwt.encode(
        data_dict,
        get_sys_settings().token_secret_key,
        algorithm=get_sys_settings().token_encryption_algorithm,
    )
    return encoded_jwt


@router.post("/token")
def users_login(
    session: Annotated[Session, Depends(get_session)],
    form_data: Annotated[OAuth2PasswordRequestForm, Depends()],
):
    user = authenticate_user(session, form_data.username, form_data.password)
    access_token = create_token({"sub": user.username})
    return Token(access_token=access_token, token_type="bearer")


# Extract token from HTTP header
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")


async def get_cur_user(
    token: Annotated[str, Depends(oauth2_scheme)],
    session: Annotated[Session, Depends(get_session)],
):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(
            token,
            get_sys_settings().token_secret_key,
            algorithms=get_sys_settings().token_encryption_algorithm,
        )
        username = payload["sub"]
        statement = select(User).where(User.username == username)
        user = session.exec(statement).first()
        return user

    except Exception as e:
        logging.error(e)
        raise credentials_exception


@router.get("/test", response_model=UserPublic)
def get_info_test(user: Annotated[User, Depends(get_cur_user)]):
    return user
