import os
# Giới hạn số luồng cho ONNX Runtime để tránh ngốn RAM quá nhanh
os.environ["OMP_NUM_THREADS"] = "1" 
os.environ["ONNXRUNTIME_INTRA_OP_NUM_THREADS"] = "1"

import json
import logging
import uuid
import os
from typing import List, Dict, Any
from dotenv import load_dotenv

from qdrant_client import QdrantClient, models
# Đã xóa SentenceSplitter vì không còn sử dụng chunking

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("import_vectors.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6335")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = "traffic_law_qa_system"
DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "traffic_laws.json")

# 1. Cập nhật Model Jina AI v3
DENSE_MODEL_NAME = "jinaai/jina-embeddings-v3"
DENSE_VECTOR_SIZE = 1024 # Jina v3 mặc định là 1024
SPARSE_MODEL_NAME = "Qdrant/bm25"

def main():
    # 1. Connect to Qdrant
    logger.info(f"Connecting to Qdrant at {QDRANT_URL}...")
    client = QdrantClient(
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY
    )
    
    # 2. Create Collection
    collection_exists = False
    try:
        client.get_collection(COLLECTION_NAME)
        collection_exists = True
    except Exception:
        pass

    if not collection_exists:
        logger.info(f"Creating collection {COLLECTION_NAME}...")
        client.create_collection(
            collection_name=COLLECTION_NAME,
            vectors_config={
                "dense": models.VectorParams(
                    distance=models.Distance.COSINE,
                    size=DENSE_VECTOR_SIZE,
                ),
            },
            sparse_vectors_config={
                "sparse": models.SparseVectorParams(
                    modifier=models.Modifier.IDF
                )
            }
        )
        logger.info("Collection created.")
    else:
        logger.info(f"Collection {COLLECTION_NAME} already exists.")

    # 3. Load Data
    logger.info(f"Loading data from {DATA_FILE}...")
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            data = json.load(f)
    except FileNotFoundError:
        logger.error(f"File {DATA_FILE} not found.")
        return

    points = []
    
    logger.info("Processing data (Full text per clause)...")
    for article in data:
        year = article.get("year", "")
        article_id = article.get("article", "")
        title = article.get("title", "")
        clauses = article.get("clauses", [])

        for clause in clauses:
            clause_content = clause.get("content", "")
            
            # Kết hợp title và content thành một khối văn bản duy nhất
            full_text = f"{title}\n{clause_content}"
            
            # Tạo payload
            payload = {
                "year": year,
                "article": article_id,
                "title": title,
                "content": full_text # Lưu trữ toàn bộ full_text
            }
            
            # Tạo Point (Không chia nhỏ chunk, dùng trực tiếp full_text)
            point = models.PointStruct(
                id=uuid.uuid4().hex,
                vector={
                    "dense": models.Document(
                        text=full_text,
                        model=DENSE_MODEL_NAME,
                    ),
                    "sparse": models.Document(
                        text=full_text,
                        model=SPARSE_MODEL_NAME,
                    ),
                },
                payload=payload
            )
            points.append(point)

    # 5. Upsert to Qdrant
    logger.info(f"Upserting {len(points)} points to Qdrant...")
    
    # Batch upsert
    BATCH_SIZE = 3
    total_batches = (len(points) + BATCH_SIZE - 1) // BATCH_SIZE
    
    for i in range(0, len(points), BATCH_SIZE):
        batch = points[i:i + BATCH_SIZE]
        try:
            client.upsert(
                collection_name=COLLECTION_NAME,
                points=batch
            )
            logger.info(f"Upserted batch {i // BATCH_SIZE + 1}/{total_batches}")
        except Exception as e:
            logger.error(f"Error upserting batch {i // BATCH_SIZE + 1}: {e}")

    logger.info("Data ingestion complete.")

if __name__ == "__main__":
    main()