import os

# Model Configurations
EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"
RERANK_MODEL_NAME = "BAAI/bge-reranker-base"

# Vector DB Configurations
# Set USE_EMBEDDED_QDRANT = True to run Qdrant in-process (embedded mode) without Docker.
# Set USE_EMBEDDED_QDRANT = False to connect to the Docker container at QDRANT_URL.
USE_EMBEDDED_QDRANT = os.getenv("USE_EMBEDDED_QDRANT", "False").lower() in ("true", "1", "yes")
QDRANT_URL = os.getenv("QDRANT_URL", "http://localhost:6333")
QDRANT_STORAGE_PATH = "./qdrant_storage"
COLLECTION_NAME = "rag_collection"

# Text Processing Configurations
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# Data Directories
DATA_DIR = "./data"
