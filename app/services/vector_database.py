import logging
import os

from langchain_community.document_loaders import (
    PyPDFLoader,
    TextLoader,
    UnstructuredImageLoader,
    UnstructuredWordDocumentLoader,
)
from langchain_community.vectorstores import Chroma
from langchain_text_splitters import (
    HTMLHeaderTextSplitter,
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

from app.settings import settings
from app.database import engine
from external_models import get_embeddings


def vectors_embedding(file_path: str, document_id: str, user_id: str):
    file_type = os.path.splitext(file_path)[-1].lower()

    # 1. Route to the correct Loader AND Splitter
    match file_type:
        case ".md":
            loader = TextLoader(file_path)
            headers_to_split_on = [
                ("#", "Header 1"),
                ("##", "Header 2"),
                ("###", "Header 3"),
            ]
            raw_text = loader.load()[0].page_content
            docs = MarkdownHeaderTextSplitter(
                headers_to_split_on=headers_to_split_on
            ).split_text(raw_text)

        case ".html":
            headers_to_split_on = [("h1", "Header 1"), ("h2", "Header 2")]
            splitter = HTMLHeaderTextSplitter(headers_to_split_on=headers_to_split_on)
            docs = splitter.split_text_from_file(file_path)

        case ".pdf" | ".txt" | ".rst" | ".doc" | ".docx" | ".png" | ".jpg":
            if file_type == ".pdf":
                loader = PyPDFLoader(file_path)
            elif file_type in (".txt", ".rst"):
                loader = TextLoader(file_path)
            elif file_type in [".doc", ".docx"]:
                loader = UnstructuredWordDocumentLoader(file_path)
            else:
                loader = UnstructuredImageLoader(file_path)

            docs = loader.load()

        case _:
            raise ValueError(f"Unsupported file type: {file_type}")

    splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    chunks = splitter.split_documents(docs)

    # 2. Inject Metadata
    for chunk in chunks:
        # Markdown splitters create 'metadata', standard splitters retain existing metadata
        if "source" not in chunk.metadata:
            chunk.metadata["source"] = file_path
        chunk.metadata["document_id"] = str(document_id)

    # 3. Embed and Store
    embedding_service = settings.services.embedding_model

    embeddings_model = get_embeddings(**embedding_service.model_dump())

    Chroma.from_documents(
        client=engine.chroma_client,
        documents=chunks,
        embedding=embeddings_model,
        collection_name=f"user-{user_id}",
    )


def delete_vectors(user_id: str, document_id: str):
    """
    Deletes vectors from a user's Chroma collection based on the document_id metadata.
    """
    # 1. Initialize the same embedding model used for insertion
    embeddings_model = get_embeddings(**settings.services.embedding_model.model_dump())

    # 2. Connect to the existing Chroma collection for this user
    vectorstore = Chroma(
        client=engine.chroma_client,
        collection_name=f"user-{user_id}",
        embedding_function=embeddings_model,
    )

    # 3. Delete documents using a metadata filter ('where' clause)
    try:
        vectorstore.delete(where={"document_id": str(document_id)})
    except Exception as e:
        logging.error(e)
