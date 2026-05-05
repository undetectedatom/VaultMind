from pydantic import BaseModel

# ------- RAG Data Schema -------
# Wrappers for use in global settings and downstream RAG pipelines


class ServiceModel(BaseModel):
    provider: str
    base_url: str
    api_key: str
    model: str
    context_window: int | None = None
    dimension: int | None = None


class Service(BaseModel):
    embedding_model: ServiceModel
    router_model: ServiceModel
    generation_models: list[ServiceModel]


# ------- Configuration Schema -------
# Utilities for convenient JSON-based configuration loading and validation


class ModelSpec(BaseModel):
    context_window: int | None = None
    dimension: int | None = None


class ServiceProvider(BaseModel):
    base_url: str
    api_key: str | None = None
    models: dict[str, ModelSpec]


class Role(BaseModel):
    provider: str
    model: str


class Activities(BaseModel):
    embedding: Role
    router: Role
    generation: list[Role]


class HyDEConfig(BaseModel):
    enabled: bool = True
    temperature: float = 0.0


class RoutingConfig(BaseModel):
    enabled: bool = True
    confidence_threshold: float = 0.5


class AppConfig(BaseModel):
    providers: dict[str, ServiceProvider]
    activities: Activities
    hyde: HyDEConfig = HyDEConfig()
    routing: RoutingConfig = RoutingConfig()
