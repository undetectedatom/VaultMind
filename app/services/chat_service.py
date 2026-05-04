import uuid

from langchain_chroma import Chroma
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage

from app.database.engine import chroma_client
from app.database.models import ChatMessage
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
) -> tuple[str, list[str]]:
    """Executes the RAG pipeline: Retrieve -> Augment -> Generate"""

    # 1. Identify the latest user query
    # We sort chronologically to ensure the newest message is at the end
    chat_history = sorted(chat_history, key=lambda x: x.created_at)
    latest_query = chat_history[-1].content

    # 2. Retrieve (Search Vector DB)
    embedding_config = settings.services.embedding_model.model_dump()
    embeddings_model = get_embeddings(**embedding_config)

    vectorstore = Chroma(
        client=chroma_client,
        collection_name=f"user-{user_id}",
        embedding_function=embeddings_model,
    )

    # Get top 4 most relevant chunks
    retrieved_docs = vectorstore.similarity_search(latest_query, k=4)

    # Extract text and sources
    context_text = "\n\n---\n\n".join([doc.page_content for doc in retrieved_docs])
    sources = list(
        set([doc.metadata.get("source", "Unknown Document") for doc in retrieved_docs])
    )

    # 3. Augment (Build the Prompt Payload)
    system_instruction = (
        "You are a helpful, professional assistant. Use the following retrieved context "
        "to answer the user's question. If the context does not contain the answer, "
        "rely on your own knowledge but clarify that it is not in the provided documents.\n\n"
        f"CONTEXT:\n{context_text}"
    )

    messages = [SystemMessage(content=system_instruction)]

    # Append historical messages (excluding the very last one which we add next)
    for msg in chat_history[:-1]:
        if msg.role == "user":
            messages.append(HumanMessage(content=msg.content))
        elif msg.role == "assistant":
            messages.append(AIMessage(content=msg.content))

    # Append the latest query
    messages.append(HumanMessage(content=latest_query))

    # 4. Generate (Call the LLM)
    # We use the first generation model defined in rag_config.json (llama3 in your case)
    generation_config = settings.services.generation_models[0].model_dump()
    llm = get_chat_model(**generation_config)

    response = llm.invoke(messages)

    return response.content, sources
