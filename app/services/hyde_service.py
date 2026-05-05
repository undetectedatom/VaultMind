from langchain_core.language_models.chat_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage

HYDE_SYSTEM_PROMPT = (
    "You are an expert technical document writer. Given a question, write a detailed, "
    "factual answer paragraph as if it were excerpted from a technical document. "
    "Do not speculate or add disclaimers. Write 3-5 sentences of concrete, "
    "domain-specific content. Do not mention that this is hypothetical or fabricated."
)


async def generate_hypothetical_document(
    query: str,
    llm: BaseChatModel,
) -> str:
    """Generate a hypothetical answer document for HyDE retrieval."""
    messages = [
        SystemMessage(content=HYDE_SYSTEM_PROMPT),
        HumanMessage(content=query),
    ]
    response = llm.invoke(messages)
    return response.content.strip()
