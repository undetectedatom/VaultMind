import enum
from datetime import datetime, timezone
from typing import Annotated
import uuid

from sqlmodel import Field, Relationship, SQLModel


class UserBase(SQLModel):
    username: Annotated[str, Field(index=True, unique=True)]
    email: Annotated[str, Field(index=True, unique=True)]


class User(UserBase, table=True):
    id: Annotated[uuid.UUID, Field(default_factory=uuid.uuid4, primary_key=True)]
    documents: list["Document"] = Relationship(back_populates="user")
    password: str


class UserPublic(UserBase):
    id: uuid.UUID


class UserCreate(UserBase):
    password: str


class DocumentStatus(str, enum.Enum):
    PENDING = "pending"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"


class DocumentBase(SQLModel):
    filename: Annotated[str, Field(index=True)]
    uploaded_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    upload_status: DocumentStatus = DocumentStatus.PENDING


class Document(DocumentBase, table=True):
    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    file_path: str
    user_id: Annotated[uuid.UUID, Field(foreign_key="user.id")]
    user: User = Relationship(back_populates="documents")


class DocumentPublic(DocumentBase):
    id: uuid.UUID
    usesr_id: uuid.UUID
