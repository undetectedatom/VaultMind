from typing import Annotated
import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from app.api.denpendencies import get_cur_user, get_session
from app.database.models import (
    ChatMessage,
    ChatRequest,
    ChatSession,
    NewChatResponse,
    User,
)
from app.services.chat_service import generate_title, knowledge_query

router = APIRouter()


def check_session(
    db_session: Session, chat_session_id: uuid.UUID | str, user_id: uuid.UUID | str
):
    # Authorization
    # We must authorize both session id and user id, preventing anomalous user query
    statement = select(ChatSession).where(
        (ChatSession.id == uuid.UUID(chat_session_id))
        & (ChatSession.user_id == uuid.UUID(user_id))
    )
    chat_session = db_session.exec(statement).first()
    if not chat_session:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Session not found, please open a new session.",
        )
    return chat_session


async def get_history(
    db_session: Session, chat_session_id: uuid.UUID | str, limit: int = 10
):
    statement = (
        select(ChatMessage)
        .where(ChatMessage.session_id == uuid.UUID(chat_session_id))
        .order_by(ChatMessage.created_at.desc())
        .limit(limit)
    )
    return db_session.exec(statement).all()


@router.post("")
async def create_new_session(
    chat_request: ChatRequest,
    user: Annotated[User, Depends(get_cur_user)],
    db_session: Annotated[Session, Depends(get_session)],
):
    chat_session = ChatSession(user=user, title="")
    chat_session.title = await generate_title(chat_request.query)
    db_session.add(chat_session)
    user_msg = ChatMessage(
        session_id=chat_session.id, role="user", content=chat_request.query
    )
    db_session.add(user_msg)
    answer, sources = await knowledge_query([user_msg])
    return NewChatResponse(
        answer=answer,
        sources=sources,
        session_id=chat_session.id,
        title=chat_session.title,
    )


@router.post("/{chat_session_id}")
async def chat_in_session(
    chat_request: ChatRequest,
    chat_session_id: str,
    user: Annotated[User, Depends(get_cur_user)],
    db_session: Annotated[Session, Depends(get_session)],
):

    check_session(db_session, chat_session_id, user.id)

    chat_message = ChatMessage(session_id=chat_session_id)
    db_session.add(chat_message)
    db_session.commit()

    chat_history = await get_history(db_session, chat_session_id)
    knowledge_query(chat_history)


@router.get("")
async def get_chat_sessions(
    user: Annotated[User, Depends(get_cur_user)],
    db_session: Annotated[Session, Depends(get_session)],
):
    pass


@router.get("/{session_id}")
async def get_chat_history(
    session_id: str,
    user: Annotated[User, Depends(get_cur_user)],
    db_session: Annotated[Session, Depends(get_session)],
):
    pass
