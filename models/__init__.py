from langchain_core.embeddings import Embeddings


def get_embeddings(
    provider: str,
    service_model: str,
    service_url: str | None = None,
    api_key: str | None = None,
    **kwargs,
) -> Embeddings:
    if provider == "doubao":
        from models.doubao import DoubaoMultimodalEmbeddings

        return DoubaoMultimodalEmbeddings(
            api_key, service_url, endpoint_id=service_model
        )

    elif provider == "openai":
        from langchain_openai import OpenAIEmbeddings

        if not api_key:
            raise ValueError("OpenAI provider requires an 'api_key'.")
        return OpenAIEmbeddings(api_key=api_key, model=service_model)

    elif provider == "ollama":
        from langchain_community.embeddings import OllamaEmbeddings

        host = service_url or "http://localhost:11434"
        return OllamaEmbeddings(base_url=host, model=service_model)

    else:
        raise ValueError(f"Unsupported embedding provider: '{provider}'")
