import asyncio
import uuid

from langchain_chroma import Chroma
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.database import engine
from app.database.models import ChatMessage
from app.services.complexity_service import evaluate_complexity_with_llm
from app.services.hyde_service import generate_hypothetical_document
from app.services.vector_database import get_bm25_retriever
from app.settings import settings
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
    """Executes the RAG pipeline with Async Parallelization and Caching"""
    metadata = {}

    chat_history = sorted(chat_history, key=lambda x: x.created_at)
    latest_query = chat_history[-1].content

    embedding_config = settings.services.embedding_model.model_dump()
    embeddings_model = get_embeddings(**embedding_config)

    vectorstore = Chroma(
        client=engine.chroma_client,
        collection_name=f"user-{user_id}",
        embedding_function=embeddings_model,
    )

    # --- 1. ASYNC PARALLEL EXECUTION (HyDE + Complexity) ---
    search_text = latest_query
    query_complexity = 0.5

    if settings.routing.enabled or settings.hyde.enabled:
        router_config = settings.services.router_model.model_dump()
        router_llm = get_chat_model(
            **router_config, temperature=settings.hyde.temperature
        )

        # Define tasks (but don't wait for them yet)
        task_hyde = (
            generate_hypothetical_document(chat_history, latest_query, router_llm)
            if settings.hyde.enabled
            else None
        )
        task_complexity = (
            evaluate_complexity_with_llm(latest_query, router_llm)
            if settings.routing.enabled
            else None
        )

        # Filter out None tasks and run them concurrently!
        tasks = [t for t in [task_hyde, task_complexity] if t is not None]

        if tasks:
            results = await asyncio.gather(*tasks)

            # Map results back based on what was enabled
            idx = 0
            if settings.hyde.enabled:
                search_text = results[idx]
                metadata["hyde_document"] = search_text
                idx += 1
            if settings.routing.enabled:
                query_complexity = results[idx]
                metadata["llm_complexity_score"] = query_complexity

    # --- 2. HYBRID RETRIEVAL (Using Cache for BM25) ---
    vector_docs = []
    retrieval_confidence = 1.0

    if settings.routing.enabled:
        results = vectorstore.similarity_search_with_relevance_scores(search_text, k=4)
        vector_docs = [doc for doc, _ in results]
        scores = [score for _, score in results]
        retrieval_confidence = max(scores) if scores else 0.0
        metadata["retrieval_confidence"] = retrieval_confidence
    else:
        vector_docs = vectorstore.similarity_search(search_text, k=4)

    # Fetch BM25 from our blazingly fast RAM cache
    bm25_retriever = get_bm25_retriever(vectorstore)
    bm25_docs = bm25_retriever.invoke(search_text)

    # Apply Reciprocal Rank Fusion (RRF)
    doc_scores = {}

    def add_to_fusion(docs, weight=60):
        for rank, doc in enumerate(docs):
            doc_hash = doc.page_content
            if doc_hash not in doc_scores:
                doc_scores[doc_hash] = {"doc": doc, "score": 0.0}
            doc_scores[doc_hash]["score"] += 1.0 / (weight + rank)

    add_to_fusion(vector_docs)
    add_to_fusion(bm25_docs)

    reranked_results = sorted(
        doc_scores.values(), key=lambda x: x["score"], reverse=True
    )
    retrieved_docs = [item["doc"] for item in reranked_results[:4]]

    context_text = "\n\n---\n\n".join([doc.page_content for doc in retrieved_docs])
    sources = list(
        set([doc.metadata.get("source", "Unknown Document") for doc in retrieved_docs])
    )

    # --- 3. DYNAMIC ROUTING ---
    if settings.routing.enabled:
        from app.services.routing_service import select_generation_model

        # We now pass both the LLM complexity and the DB confidence!
        selected_model, route_reason = select_generation_model(
            query=latest_query,  # Changed to match the new signature you will write
            retrieval_confidence=retrieval_confidence,
            generation_models=settings.services.generation_models,
        )
        metadata["route_reason"] = route_reason
        metadata["selected_model"] = selected_model.model
        generation_config = selected_model.model_dump()
    else:
        generation_config = settings.services.generation_models[-1].model_dump()

    llm = get_chat_model(**generation_config)
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

    # Changed to ainvoke for full async performance
    response = await llm.ainvoke(messages)

    return response.content, sources, metadata
