from fastapi import APIRouter
from pydantic import BaseModel


router = APIRouter()


class User(BaseModel):
    user_id: int
    name: str
    role: str
