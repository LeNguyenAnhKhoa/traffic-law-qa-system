import os

from dotenv import load_dotenv, find_dotenv

load_dotenv(find_dotenv())

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

SERVER_API_KEY = os.getenv("SERVER_API_KEY")

PORT = int(os.getenv("BACKEND_PORT", "8000"))

# Qdrant configuration
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6335")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")

OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-4.1-mini")

API_VERSION = "v0"

ERROR_MESSAGE = "We are facing an issue, please try after sometimes."

# Reranker configuration
RERANKER_MODEL = os.getenv("RERANKER_MODEL", "gpt-4.1-mini")
HYBRID_SEARCH_TOP_K = int(os.getenv("HYBRID_SEARCH_TOP_K", "40"))
RERANK_TOP_K = int(os.getenv("RERANK_TOP_K", "5"))

# Embedding models
DENSE_MODEL_NAME = os.getenv("DENSE_MODEL_NAME", "jinaai/jina-embeddings-v3")
SPARSE_MODEL_NAME = os.getenv("SPARSE_MODEL_NAME", "Qdrant/bm25")
