# 📝 Text/Markdown (.txt, .md): TextLoader or UnstructuredMarkdownLoader
# 🌐 HTML (.html): BSHTMLLoader
# 📕 PDF (.pdf): PyPDFLoader
# 📘 Word (.doc, .docx): UnstructuredWordDocumentLoader
# 🖼️ Images (.jpg, .png): UnstructuredImageLoader (which handles basic OCR)
import os
from typing import Iterator
from langchain_google_genai import GoogleGenerativeAIEmbeddings
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_core.documents import Document
from langchain_community.document_loaders import (
    UnstructuredMarkdownLoader,
    BSHTMLLoader,
    PyPDFLoader,
    UnstructuredWordDocumentLoader,
    UnstructuredImageLoader,
)
from langchain_community.vectorstores import Chroma


def file_embedding(files: list[str], vector_database: str) -> Chroma:
    generators: list[Iterator[Document]] = []
    for file in files:
        match os.path.splitext(file)[-1]:
            case ".pdf":
                loader = PyPDFLoader(file)
            case ".md" | ".txt":
                loader = UnstructuredMarkdownLoader(file)
            case ".html":
                loader = BSHTMLLoader(file)
            case ".doc" | ".docx":
                loader = UnstructuredWordDocumentLoader(file)
            case ".png" | ".jpg":
                loader = UnstructuredImageLoader(file)
        generators.append(loader.lazy_load())
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    embeddings_model = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")
    docs: list[Document] = []
    for generator in generators:
        docs.extend(text_splitter.split_documents(generator))
    db = Chroma.from_documents(
        documents=docs,
        embedding=embeddings_model,
        persist_directory=vector_database,
    )
    # we also need to save data into local files and many other pending opeartions here.
    return db
