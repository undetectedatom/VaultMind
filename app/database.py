from typing import Annotated

from pydantic import BaseModel
from sqlmodel import Field, Session, SQLModel, create_engine, select

sqlite_file_name = "database.db"
connect_args = {"check_same_thread": False}
engine = create_engine(f"sqlite:///{sqlite_file_name}", connect_args=connect_args)


def create_db_and_tables():
    SQLModel.metadata.create_all(engine)


def get_session():
    with Session(engine) as session:
        yield session


class UserBase(SQLModel):
    username: Annotated[str, Field(index=True, unique=True)]
    email: Annotated[str, Field(index=True, unique=True)]


class User(UserBase, table=True):
    id: Annotated[int | None, Field(primary_key=True)] = None
    password: str


class UserPublic(UserBase):
    id: int


class UserCreate(UserBase):
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


if __name__ == "__main__":
    create_db_and_tables()
