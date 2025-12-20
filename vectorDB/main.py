import json
import logging
import uuid
import os
from typing import List, Dict, Any
from dotenv import load_dotenv

from qdrant_client import QdrantClient, models
from llama_index.core.node_parser import SentenceSplitter

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
# Read Qdrant cloud configuration from environment variables
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6335")
QDRANT_API_KEY = os.getenv("QDRANT_API_KEY")
COLLECTION_NAME = "traffic_law_qa_system"
DATA_FILE = os.path.join(os.path.dirname(__file__), "data", "traffic_laws.json")
DENSE_MODEL_NAME = "intfloat/multilingual-e5-large"
DENSE_VECTOR_SIZE = 1024
SPARSE_MODEL_NAME = "Qdrant/bm25"
CHUNK_SIZE = 512
CHUNK_OVERLAP = 64

def main():
    # 1. Connect to Qdrant
    logger.info(f"Connecting to Qdrant at {QDRANT_URL}...")
    client = QdrantClient(
        url=QDRANT_URL,
        api_key=QDRANT_API_KEY
    )
    
    # 2. Create Collection
    # Check if collection exists
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

    # 4. Initialize Splitter
    splitter = SentenceSplitter(chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP)

    points = []
    
    logger.info("Processing data...")
    for article in data:
        year = article.get("year", "")
        article_id = article.get("article", "")
        title = article.get("title", "")
        clauses = article.get("clauses", [])

        for clause in clauses:
            clause_content = clause.get("content", "")
            
            # Combine title and content
            # "Với mỗi mẫu trong "clause" lấy "title" (bên ngoài) + "content" (bên trong clause)"
            full_text = f"{title}\n{clause_content}"
            
            # Split text
            chunks = splitter.split_text(full_text)
            
            for chunk in chunks:
                # Create payload
                payload = {
                    "year": year,
                    "article": article_id,
                    "title": title,
                    "content": chunk # Storing the chunk content
                }
                
                # Create Point
                # Using models.Document to let Qdrant client handle embedding generation
                point = models.PointStruct(
                    id=uuid.uuid4().hex,
                    vector={
                        "dense": models.Document(
                            text=chunk,
                            model=DENSE_MODEL_NAME,
                        ),
                        "sparse": models.Document(
                            text=chunk,
                            model=SPARSE_MODEL_NAME,
                        ),
                    },
                    payload=payload
                )
                points.append(point)

    # 5. Upsert to Qdrant
    logger.info(f"Upserting {len(points)} points to Qdrant...")
    
    # Batch upsert to avoid issues with large requests
    BATCH_SIZE = 20 # Smaller batch size for embedding generation
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
