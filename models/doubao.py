import requests
from typing import List
from langchain_core.embeddings import Embeddings


class DoubaoMultimodalEmbeddings(Embeddings):
    """Custom LangChain embedding class for Doubao Multimodal Vision Endpoint."""

    def __init__(
        self, api_key: str, api_url: str, endpoint_id: str, dimensions: int = 2048
    ):
        self.api_key = api_key
        self.api_url = api_url
        self.endpoint_id = endpoint_id
        self.dimensions = dimensions

    def embed_documents(self, texts: List[str]) -> List[List[float]]:
        embeddings = []
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {self.api_key}",
        }

        for text in texts:
            payload = {
                "model": self.endpoint_id,
                "input": [{"type": "text", "text": text}],
                "dimensions": self.dimensions,
                "encoding_format": "float",
            }

            response = requests.post(self.api_url, headers=headers, json=payload)
            response.raise_for_status()

            data = response.json()

            # Handle both Dictionary and List response formats
            if isinstance(data["data"], list):
                # Standard OpenAI format
                vector = data["data"][0]["embedding"]
            else:
                # Current Volcengine Multimodal format
                vector = data["data"]["embedding"]

            embeddings.append(vector)

        return embeddings

    def embed_query(self, text: str) -> List[float]:
        return self.embed_documents([text])[0]
