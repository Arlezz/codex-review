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
        _model = SentenceTransformer(os.getenv("EMBEDDING_MODEL", "all-MiniLM-L6-v2"))
    return _model


def _get_chroma():
    global _chroma
    if _chroma is None:
        _chroma = PersistentClient(path=os.getenv("CHROMA_DB_PATH", "./chroma_db"))
    return _chroma
