import os

# Model Configurations
EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"
RERANK_MODEL_NAME = "BAAI/bge-reranker-base"

# Vector DB Configurations (Pinecone)
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "enterprise-rag-index")
PINECONE_CLOUD = os.getenv("PINECONE_CLOUD", "aws")
PINECONE_REGION = os.getenv("PINECONE_REGION", "us-east-1")

# Text Processing Configurations
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# Data Directories
DATA_DIR = "./data"
