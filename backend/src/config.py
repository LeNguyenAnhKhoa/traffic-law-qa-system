import os
from pathlib import Path
from typing import List, Union
from pydantic_settings import BaseSettings, SettingsConfigDict

# Calculate paths
BACKEND_DIR = Path(__file__).parent.parent
ROOT_DIR = BACKEND_DIR.parent

class Settings(BaseSettings):
    # Server
    BACKEND_PORT: int = 8000
    SERVER_API_KEY: Union[str, None] = None
    API_VERSION: str = "v0"
    
    # OpenAI
    OPENAI_API_KEY: str
    OPENAI_MODEL: str = "gpt-4.1-mini"
    
    # Qdrant
    QDRANT_URL: str = "http://localhost:6335"
    QDRANT_API_KEY: Union[str, None] = None
    
    # Reranker & Search
    RERANKER_MODEL: str = "gpt-4.1-mini"
    HYBRID_SEARCH_TOP_K: int = 40
    RERANK_TOP_K: int = 5
    
    # Embedding models
    DENSE_MODEL_NAME: str = "jinaai/jina-embeddings-v3"
    SPARSE_MODEL_NAME: str = "Qdrant/bm25"
    
    # Constants
    ERROR_MESSAGE: str = "We are facing an issue, please try after sometimes."

    model_config = SettingsConfigDict(
        env_file=[
            os.path.join(ROOT_DIR, ".env"), 
            os.path.join(BACKEND_DIR, ".env")
        ],
        env_file_encoding='utf-8',
        extra='ignore'
    )

settings = Settings()

