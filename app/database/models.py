import enum
from datetime import datetime, timezone
from typing import Annotated

from sqlmodel import Field, Relationship, SQLModel


class UserBase(SQLModel):
    username: Annotated[str, Field(index=True, unique=True)]
    email: Annotated[str, Field(index=True, unique=True)]


class User(UserBase, table=True):
    id: Annotated[int | None, Field(primary_key=True)] = None
    documents: list["Document"] = Relationship(back_populates="user")
    password: str


class UserPublic(UserBase):
    id: int


class UserCreate(UserBase):
    password: str


class DocumentStatus(str, enum.Enum):
    PROCESSING = "processing"
    STORED = "stored"
    FAILED = "failed"


class Document(SQLModel, table=True):
    id: Annotated[int | None, Field(primary_key=True)] = None
    filename: Annotated[str, Field(index=True)]
    user_id: Annotated[int, Field(foreign_key="user.id")]
    user: User = Relationship(back_populates="documents")
    vector_namespace: str
    uploaded_at: Annotated[
        datetime, Field(default_factory=lambda: datetime.now(timezone.utc))
    ]
    upload_status: DocumentStatus = DocumentStatus.PROCESSING
