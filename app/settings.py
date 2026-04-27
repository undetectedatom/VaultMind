from functools import lru_cache
import os
from pydantic_settings import BaseSettings, SettingsConfigDict


class SysSettings(BaseSettings):
    temp_file: str
    vector_database: str
    user_documents: str
    dummy_pwd: str = "dummy_pwd"
    token_secret_key: str
    token_encryption_algorithm: str
    provider: str
    service_url: str
    service_model: str
    api_key: str
    model_config = SettingsConfigDict(env_file=os.path.join(os.getcwd(), ".env"))


@lru_cache
def get_sys_settings():
    return SysSettings()
