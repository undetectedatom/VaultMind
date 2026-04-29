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
    chat_sessions: list["ChatSession"] = Relationship(back_populates="user")
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
    comment: str = ""


class DocumentPublic(DocumentBase):
    id: uuid.UUID
    user_id: uuid.UUID


class ChatSession(SQLModel, table=True):
    id: uuid.UUID
    user_id: Annotated[uuid.UUID, Field(foreign_key="user.id")]
    user: User = Relationship(back_populates="chat_sessions")
    chat_messages: list["ChatMessage"] = Relationship(back_populates="chat_session")
    title: str


class ChatMessage(SQLModel, table=True):
    id: uuid.UUID
    session_id: Annotated[uuid.UUID, Field(foreign_key="chat_session.id")]
    session: ChatSession = Relationship(back_populates="chat_messages")
    role: str
    content: str
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ChatRequest(SQLModel):
    query: str


class ChatResponse(SQLModel):
    answer: str
    sources: list[str]
    session_id: uuid.UUID
