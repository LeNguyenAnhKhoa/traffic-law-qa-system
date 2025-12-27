import os
# Limit ONNX Runtime threads to prevent excessive RAM usage
os.environ["OMP_NUM_THREADS"] = "1" 
os.environ["ONNXRUNTIME_INTRA_OP_NUM_THREADS"] = "1"
import logging
from typing import List, Dict, Any
from pathlib import Path

from qdrant_client import QdrantClient, models
from fastembed import TextEmbedding, SparseTextEmbedding
from src.config import settings

logger = logging.getLogger(__name__)


# Configuration
QDRANT_URL = settings.QDRANT_URL
QDRANT_API_KEY = settings.QDRANT_API_KEY
COLLECTION_NAME = "traffic_law_qa_system"
DENSE_MODEL_NAME = settings.DENSE_MODEL_NAME
SPARSE_MODEL_NAME = settings.SPARSE_MODEL_NAME



class QdrantService:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
            
        logger.info(f"Connecting to Qdrant at {QDRANT_URL}...")
        self.client = QdrantClient(
            url=QDRANT_URL,
            api_key=QDRANT_API_KEY
        )
        
        # Initialize embedding models
        logger.info("Loading embedding models...")
        self.dense_model = TextEmbedding(DENSE_MODEL_NAME)
        self.sparse_model = SparseTextEmbedding(SPARSE_MODEL_NAME)
        logger.info("Embedding models loaded successfully")
        
        self._initialized = True
    
    def hybrid_search(self, query: str, limit: int = 100) -> List[Dict[str, Any]]:
        """
        Perform hybrid search combining dense and sparse vectors with RRF fusion.
        
        Args:
            query: The search query
            limit: Number of results to return
            
        Returns:
            List of search results with payload and scores
        """
        # Generate embeddings for the query
        dense_vector = list(self.dense_model.query_embed(query))[0]
        sparse_vector = list(self.sparse_model.query_embed(query))[0]
        
        # Stage 1: Parallel prefetch (dense + sparse)
        hybrid_query = [
            models.Prefetch(
                query=dense_vector.tolist(),
                using="dense",
                limit=limit
            ),
            models.Prefetch(
                query=models.SparseVector(
                    indices=sparse_vector.indices.tolist(),
                    values=sparse_vector.values.tolist()
                ),
                using="sparse",
                limit=limit
            ),
        ]
        
        # Stage 2: Fusion with RRF
        fusion_query = models.Prefetch(
            prefetch=hybrid_query,
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=limit,
        )
        
        # Execute the query
        response = self.client.query_points(
            collection_name=COLLECTION_NAME,
            prefetch=fusion_query,
            query=models.FusionQuery(fusion=models.Fusion.RRF),
            limit=limit,
            with_payload=True,
        )
        
        results = []
        for point in response.points:
            results.append({
                "id": point.id,
                "score": point.score,
                "payload": point.payload
            })
        
        logger.info(f"Hybrid search returned {len(results)} results for query limit {limit}")
        return results


# Singleton instance
qdrant_service = QdrantService()
