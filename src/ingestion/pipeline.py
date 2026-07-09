import os
import sys

# macOS and PySpark environment safety configurations
os.environ["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["SPARK_PYTHON_WORKER_FAULTHANDLER_ENABLED"] = "true"
os.environ["PYSPARK_PYTHON"] = sys.executable
os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable

# Ensure Java environment variables are set correctly for PySpark
os.environ["JAVA_HOME"] = "/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home"
os.environ["PATH"] = f"/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home/bin:{os.environ.get('PATH', '')}"

from pyspark.sql import SparkSession
import pyspark.sql.functions as F
from pyspark.sql.types import ArrayType, StructType, StructField, StringType, IntegerType

from src.config import (
    USE_EMBEDDED_QDRANT, QDRANT_URL, QDRANT_STORAGE_PATH, COLLECTION_NAME, DATA_DIR
)
from src.ingestion.chunker import RecursiveCharacterChunker

def setup_qdrant_collection():
    """
    Initializes/re-creates the Qdrant collection configured with:
    - named dense vector field (384 dimensions for BGE)
    - named sparse vector field (for keyword indexing)
    - Scalar Quantization (INT8) for memory optimization at scale.
    """
    from qdrant_client import QdrantClient
    from qdrant_client import models
    
    if USE_EMBEDDED_QDRANT:
        print(f"[Driver] Initializing Qdrant in embedded storage at '{QDRANT_STORAGE_PATH}'...")
        client = QdrantClient(path=QDRANT_STORAGE_PATH)
    else:
        print(f"[Driver] Connecting to Qdrant Docker container at '{QDRANT_URL}'...")
        client = QdrantClient(url=QDRANT_URL)
        
    try:
        collections = client.get_collections().collections
        exists = any(c.name == COLLECTION_NAME for c in collections)
        if exists:
            print(f"[Driver] Collection '{COLLECTION_NAME}' exists. Re-creating it to start fresh...")
            client.delete_collection(COLLECTION_NAME)
    except Exception as e:
        print(f"[Driver] Could not fetch collections. Initializing collection anyway. Detail: {e}")
        
    client.create_collection(
        collection_name=COLLECTION_NAME,
        vectors_config={
            "text-dense": models.VectorParams(
                size=384,
                distance=models.Distance.COSINE
            )
        },
        sparse_vectors_config={
            "text-sparse": models.SparseVectorParams(
                index=models.SparseIndexParams(on_disk=False)
            )
        },
        quantization_config=models.ScalarQuantization(
            scalar=models.ScalarQuantizationConfig(
                type=models.ScalarType.INT8,
                quantile=0.99,
                always_ram=True
            )
        )
    )
    print(f"[Driver] Collection '{COLLECTION_NAME}' created successfully with Scalar Quantization.")


def embed_partition(rows):
    """
    Worker-level function that runs in mapPartitions on Spark executors.
    Loads models once per partition, processes chunks in batches,
    generates embeddings (dense + sparse), and returns them.
    """
    import uuid
    from sentence_transformers import SentenceTransformer
    from src.retrieval.sparse_encoder import SparseEncoder
    
    # We must re-import config on executors to avoid serialization issues
    from src.config import EMBEDDING_MODEL_NAME
    
    # Load embedding model once per partition on CPU to prevent Metal initialization crashes in forked processes
    model = SentenceTransformer(EMBEDDING_MODEL_NAME, device="cpu")
    sparse_encoder = SparseEncoder()
    
    batch = []
    results = []
    
    def process_batch(b):
        if not b:
            return
        texts = [r.chunk_text for r in b]
        dense_embs = model.encode(texts, batch_size=len(texts), show_progress_bar=False).tolist()
        
        for row, dense_emb in zip(b, dense_embs):
            sparse_vec = sparse_encoder.encode(row.chunk_text)
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{row.doc_id}_{row.chunk_index}"))
            
            results.append({
                "id": point_id,
                "dense_emb": dense_emb,
                "sparse_indices": sparse_vec["indices"],
                "sparse_values": sparse_vec["values"],
                "doc_id": row.doc_id,
                "chunk_text": row.chunk_text,
                "chunk_index": row.chunk_index
            })
            
    # Process partition rows
    for row in rows:
        batch.append(row)
        if len(batch) >= 64:
            process_batch(batch)
            batch = []
            
    if batch:
        process_batch(batch)
        
    return results


def run_pipeline():
    # 1. Initialize Qdrant DB Collection
    setup_qdrant_collection()
    
    # 2. Build local PySpark session
    print("Starting SparkSession...")
    spark = SparkSession.builder \
        .appName("RAG-Ingestion-Pipeline") \
        .master("local[1]") \
        .config("spark.driver.memory", "4g") \
        .config("spark.sql.execution.arrow.pyspark.enabled", "true") \
        .getOrCreate()
        
    try:
        # Load raw files
        raw_data_path = os.path.join(DATA_DIR, "*.txt")
        print(f"Reading raw data files from {raw_data_path}...")
        
        # Load whole text files as (filepath, content) tuples
        rdd_raw = spark.sparkContext.wholeTextFiles(raw_data_path)
        df_raw = rdd_raw.toDF(["file_path", "raw_content"])
        
        # Check if empty
        if df_raw.count() == 0:
            print("Error: No data files found. Please generate the sample dataset first.")
            return
            
        # 3. Clean Text and Hash
        df_clean = df_raw.withColumn("cleaned_content", F.regexp_replace(F.trim(df_raw.raw_content), r"\s+", " ")) \
                         .filter(F.col("cleaned_content") != "") \
                         .withColumn("doc_id", F.sha2(F.col("cleaned_content"), 256))
                         
        # 4. Define Chunking UDF
        def get_chunks(text):
            chunker = RecursiveCharacterChunker(chunk_size=500, chunk_overlap=50)
            chunks = chunker.chunk_text(text)
            return [{"chunk_text": chunk, "chunk_index": idx} for idx, chunk in enumerate(chunks)]
            
        chunk_schema = ArrayType(
            StructType([
                StructField("chunk_text", StringType(), False),
                StructField("chunk_index", IntegerType(), False)
            ])
        )
        
        get_chunks_udf = F.udf(get_chunks, chunk_schema)
        
        # Expand document rows into chunk rows
        df_chunks = df_clean.withColumn("chunks_arr", get_chunks_udf(F.col("cleaned_content"))) \
                             .withColumn("chunk_data", F.explode(F.col("chunks_arr"))) \
                             .select(
                                 F.col("doc_id"),
                                 F.col("chunk_data.chunk_text").alias("chunk_text"),
                                 F.col("chunk_data.chunk_index").alias("chunk_index")
                             )
                             
        print(f"Processing partition levels and running distributed embedding...")
        # 5. Distributed Embedding generation
        raw_points = df_chunks.rdd.mapPartitions(embed_partition).collect()
        total_chunks = len(raw_points)
        print(f"Generated {total_chunks} embeddings. Upserting to Qdrant...")
        
        # 6. Single-threaded driver upsert to prevent database lock contention
        from qdrant_client import QdrantClient
        from qdrant_client import models
        if USE_EMBEDDED_QDRANT:
            client = QdrantClient(path=QDRANT_STORAGE_PATH)
        else:
            client = QdrantClient(url=QDRANT_URL)
            
        points = []
        for p in raw_points:
            points.append(
                models.PointStruct(
                    id=p["id"],
                    vector={
                        "text-dense": p["dense_emb"],
                        "text-sparse": models.SparseVector(
                            indices=p["sparse_indices"],
                            values=p["sparse_values"]
                        )
                    },
                    payload={
                        "doc_id": p["doc_id"],
                        "chunk_text": p["chunk_text"],
                        "chunk_index": p["chunk_index"]
                    }
                )
            )
            if len(points) >= 100:
                client.upsert(collection_name=COLLECTION_NAME, points=points)
                points = []
        if points:
            client.upsert(collection_name=COLLECTION_NAME, points=points)
            
        print(f"Successfully ingested {total_chunks} chunks into Qdrant '{COLLECTION_NAME}'.")
        
    finally:
        print("Stopping Spark session.")
        spark.stop()

if __name__ == "__main__":
    run_pipeline()
