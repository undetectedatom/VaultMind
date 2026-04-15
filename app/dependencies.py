from functools import lru_cache
import os
from typing import Annotated
from pathlib import Path
from fastapi import Depends
from pydantic_settings import BaseSettings, SettingsConfigDict


class SysSettings(BaseSettings):
    temp_file: str
    vector_database: str
    dummy_pwd: str = "dummy_pwd"
    model_config = SettingsConfigDict(env_file=os.path.join(os.getcwd(), ".env"))


@lru_cache
def get_sys_settings():
    return SysSettings()


SysDataPathDep = Annotated[SysSettings, Depends(SysSettings)]
