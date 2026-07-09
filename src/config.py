import os

# Model Configurations
EMBEDDING_MODEL_NAME = "BAAI/bge-small-en-v1.5"
RERANK_MODEL_NAME = "BAAI/bge-reranker-base"

# Vector DB Configurations (Pinecone)
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY", "")
PINECONE_INDEX_NAME = os.getenv("PINECONE_INDEX_NAME", "enterprise-rag-index")
PINECONE_CLOUD = os.getenv("PINECONE_CLOUD", "aws")
PINECONE_REGION = os.getenv("PINECONE_REGION", "us-east-1")

# AWS S3 / Lakehouse Configurations
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME", "enterprise-rag-lakehouse")
S3_PREFIX = os.getenv("S3_PREFIX", "documents/")

# Pricing Configurations (Rate per 1,000 tokens / queries)
PRICE_EMBEDDING_PER_1K = 0.00002       # BGE-small embedding pricing
PRICE_RERANK_PER_1K = 0.00010          # Cross-encoder reranker pricing
PRICE_LLM_INPUT_PER_1K = 0.00150        # LLM input prompt pricing
PRICE_LLM_OUTPUT_PER_1K = 0.00200       # LLM generation pricing
PRICE_PINECONE_UPSERT_PER_1K = 0.00100   # Pinecone DB write operations pricing

# Text Processing Configurations
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50

# Data Directories
DATA_DIR = "./data"
