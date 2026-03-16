import random

from fastapi import APIRouter, Form
from pydantic import BaseModel


router = APIRouter()


class User(BaseModel):
    name: str
    role: str
    email_addr: str


class UserPublic(User):
    id: int


@router.post("/user/login")
async def login(
    name: str = Form(...), role: str = Form(...), email_addr: str = Form(...)
):
    user_public = UserPublic(
        name=name,
        role=role,
        email_addr=email_addr,
        id=random.randint(100_000_000, 999_999_999),
    )
    return user_public
