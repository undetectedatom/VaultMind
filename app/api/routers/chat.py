from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel import Session, select
from app.api.denpendencies import get_cur_user, get_session
from app.database.models import ChatMessage, ChatRequest, ChatSession, User
from app.services.chat_service import generate_query

router = APIRouter()


@router.post("")
def chat(
    chat_request: ChatRequest,
    user: Annotated[User, Depends(get_cur_user())],
    db_session: Annotated[Session, get_session()],
):
    if chat_request.session_id:
        # We must make sure both session id and user id, preventing anomalous user query
        statement = select(ChatSession).where(
            (ChatSession.id == chat_request.session_id)
            & (ChatSession.user_id == user.id)
        )
        chat_session = db_session.exec(statement).first()
        if not chat_session:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Session not found, please open a new session.",
            )
    else:
        chat_session = ChatSession(user=user, title="")
        db_session.add(chat_session)
        db_session.commit()
    user_msg = ChatMessage(
        session_id=chat_session.id, role="user", content=chat_request.query
    )
    db_session.add(user_msg)
    db_session.commit()
    statement = (
        select(ChatMessage)
        .where(ChatMessage.session_id == chat_session.id)
        .order_by(ChatMessage.created_at.desc())
        .limit(10)
    )
    chat_history = db_session.exec(statement).all()
    generate_query(chat_history)
