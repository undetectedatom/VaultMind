import uuid

from langchain_chroma import Chroma
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.database import engine
from app.database.models import ChatMessage
from app.settings import settings
from app.services.hyde_service import generate_hypothetical_document
from external_models import get_chat_model, get_embeddings


async def generate_title(query: str) -> str:
    """Uses the fast 'router' model to generate a short chat title."""
    router_config = settings.services.router_model.model_dump()
    llm = get_chat_model(**router_config, temperature=0.5)

    prompt = f"Generate a very concise, 3 to 5 word title for this query. Do not use quotes or punctuation. Query: {query}"
    response = llm.invoke(prompt)
    return response.content.strip()


async def knowledge_query(
    chat_history: list[ChatMessage], user_id: uuid.UUID
) -> tuple[str, list[str], dict]:
    """Executes the RAG pipeline: Retrieve -> Augment -> Generate

    Returns (answer, sources, metadata) where metadata contains
    HyDE and routing info for evaluation/logging.
    """
    metadata = {}

    # 1. Identify the latest user query
    chat_history = sorted(chat_history, key=lambda x: x.created_at)
    latest_query = chat_history[-1].content

    # 2. Setup embeddings and vectorstore
    embedding_config = settings.services.embedding_model.model_dump()
    embeddings_model = get_embeddings(**embedding_config)

    vectorstore = Chroma(
        client=engine.chroma_client,
        collection_name=f"user-{user_id}",
        embedding_function=embeddings_model,
    )

    # 3. HyDE: Generate hypothetical document for retrieval
    search_text = latest_query
    if settings.hyde.enabled:
        router_config = settings.services.router_model.model_dump()
        router_llm = get_chat_model(
            **router_config, temperature=settings.hyde.temperature
        )
        search_text = await generate_hypothetical_document(latest_query, router_llm)
        metadata["hyde_document"] = search_text

    # 4. Retrieve
    if settings.routing.enabled:
        results = vectorstore.similarity_search_with_relevance_scores(
            search_text, k=4
        )
        retrieved_docs = [doc for doc, _ in results]
        scores = [score for _, score in results]
        confidence = sum(scores) / len(scores) if scores else 0.0
        metadata["retrieval_scores"] = scores
        metadata["retrieval_confidence"] = confidence
    else:
        retrieved_docs = vectorstore.similarity_search(search_text, k=4)

    # Extract text and sources
    context_text = "\n\n---\n\n".join([doc.page_content for doc in retrieved_docs])
    sources = list(
        set(
            [
                doc.metadata.get("source", "Unknown Document")
                for doc in retrieved_docs
            ]
        )
    )

    # 5. Model routing
    if settings.routing.enabled:
        from app.services.routing_service import select_generation_model

        selected_model, route_reason = select_generation_model(
            confidence=confidence,
            generation_models=settings.services.generation_models,
            confidence_threshold=settings.routing.confidence_threshold,
        )
        metadata["route_reason"] = route_reason
        metadata["selected_model"] = selected_model.model
        generation_config = selected_model.model_dump()
    else:
        generation_config = settings.services.generation_models[-1].model_dump()

    llm = get_chat_model(**generation_config)

    # 6. Augment
    system_instruction = (
        "You are a helpful, professional assistant. Use the following retrieved context "
        "to answer the user's question. If the context does not contain the answer, "
        "rely on your own knowledge but clarify that it is not in the provided documents.\n\n"
        f"CONTEXT:\n{context_text}"
    )

    messages = [SystemMessage(content=system_instruction)]

    for msg in chat_history[:-1]:
        if msg.role == "user":
            messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            messages.append(AIMessage(content=msg.content))

    messages.append(HumanMessage(content=latest_query))

    # 7. Generate
    response = llm.invoke(messages)

    return response.content, sources, metadata
