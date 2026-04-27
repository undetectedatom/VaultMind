import logging
import os
import uuid

import aiofiles
from fastapi import UploadFile
from langchain_community.document_loaders import (
    BSHTMLLoader,
    PyPDFLoader,
    UnstructuredImageLoader,
    UnstructuredMarkdownLoader,
    UnstructuredWordDocumentLoader,
)
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.database.models import Document
from app.settings import get_sys_settings


async def save_file_to_disk(file: UploadFile, document_id: uuid.UUID | str):
    try:
        file_path = os.path.join(
            get_sys_settings().user_documents, f"{document_id}_{file.filename}"
        )
        async with aiofiles.open(file_path, "wb") as out_file:
            while chunk := await file.read(1024 * 1024):
                await out_file.write(chunk)
        return file_path
    except Exception as e:
        logging.error(e)
        raise e


def delete_file_from_disk(document: Document):
    try:
        if os.path.exists(document.file_path):
            os.remove(document.file_path)
    except Exception as e:
        logging.error(e)
        raise e


async def process_and_embed_document(file_path, document_id, user_id):
    file_type = os.path.splitext(file_path)[-1]
    match file_type:
        case ".pdf":
            loader = PyPDFLoader(file_path)
        case ".md" | ".txt":
            loader = UnstructuredMarkdownLoader(file_path)
        case ".html":
            loader = BSHTMLLoader(file_path)
        case ".doc" | ".docx":
            loader = UnstructuredWordDocumentLoader(file_path)
        case ".png" | ".jpg":
            loader = UnstructuredImageLoader(file_path)
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    embeddings_model = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
    chunks = text_splitter.split_documents(loader.lazy_load())
    for chunk in chunks:
        chunk.metadata["document_id"] = str(document_id)
