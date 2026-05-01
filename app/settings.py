from functools import lru_cache
import json
import os
import secrets
from app.schemas.external_model import (
    Service,
    ServiceModel,
    Role,
    AppConfig,
)
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    vector_database_path: str
    user_documents_path: str
    token_secret_key: str
    token_encryption_algorithm: str
    dummy_pwd: str = secrets.token_urlsafe(32)
    rag_config_path: str = "rag_config.json"

    doubao_api_key: str | None = None
    openai_api_key: str | None = None

    services: Service | None = None

    model_config = SettingsConfigDict(
        env_file=os.path.join(os.getcwd(), ".env"), extra="ignore"
    )

    def model_post_init(self, __context):
        if not os.path.exists(self.rag_config_path):
            return

        with open(self.rag_config_path, "r") as f:
            raw_config = AppConfig(**json.load(f))

        # Inject API keys into the raw config
        for provider_name, provider_data in raw_config.providers.items():
            env_api_key = getattr(self, f"{provider_name}_api_key", None)
            if env_api_key:
                provider_data.api_key = env_api_key

        def resolve_model(role: Role) -> ServiceModel:
            provider = raw_config.providers[role.provider]
            specs = provider.models[role.model]
            return ServiceModel(
                base_url=provider.base_url,
                api_key=provider.api_key or "",
                model=role.model,
                context_window=specs.context_window,
                dimension=specs.dimension,
            )

        self.services = Service(
            embedding_model=resolve_model(raw_config.activities.embedding),
            router_model=resolve_model(raw_config.activities.router),
            generation_models=[
                resolve_model(role) for role in raw_config.activities.generation
            ],
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()


supported_files = set((".md", ".html", ".pdf", ".txt", ".doc", ".docx", ".png", ".jpg"))
