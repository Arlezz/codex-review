import os

from chromadb import PersistentClient
from dotenv import load_dotenv
from sentence_transformers import SentenceTransformer

load_dotenv()

_model = None
_chroma = None


def _get_model():
    global _model
    if _model is None:
        _model = SentenceTransformer(os.getenv("EMBEDDING_MODEL"))
    return _model


def _get_chroma():
    global _chroma
    if _chroma is None:
        _chroma = PersistentClient(path=os.getenv("CHROMA_DB_PATH", "./chroma_db"))
    return _chroma


def _get_chroma_metadata() -> dict:
    return {
        "hnsw:space": "cosine",
        # "hnsw:ef_construction": 200,
        # "hnsw:m": 16,
    }
