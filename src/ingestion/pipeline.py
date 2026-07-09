import os
import uuid
from pyspark.sql.types import ArrayType, StructType, StructField, StringType, IntegerType
import pyspark.sql.functions as F

from src.config import DATA_DIR
from src.connections.qdrant import QdrantConnectionManager
from src.connections.spark import SparkSessionManager
from src.utils.logger import setup_logger

logger = setup_logger("ingestion_pipeline")

def embed_partition(rows):
    """
    Worker-level function that runs in mapPartitions on Spark executors.
    Loads models once per partition on CPU, generates embeddings (dense + sparse), and returns.
    """
    import uuid
    from sentence_transformers import SentenceTransformer
    from src.utils.sparse_encoder import SparseEncoder
    from src.config import EMBEDDING_MODEL_NAME
    
    # Load embedding model once per partition on CPU (Mac safe)
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
            
    for row in rows:
        batch.append(row)
        if len(batch) >= 64:
            process_batch(batch)
            batch = []
            
    if batch:
        process_batch(batch)
        
    return results


class RAGIngestionPipeline:
    """
    Object-oriented ingestion pipeline that orchestrates cleaning, chunking,
    hashing, embedding calculation, and ingestion of documents using Spark.
    """
    def __init__(
        self,
        spark_manager: SparkSessionManager,
        qdrant_manager: QdrantConnectionManager
    ):
        self.spark_manager = spark_manager
        self.qdrant_manager = qdrant_manager

    def run(self, data_directory: str = DATA_DIR) -> int:
        """
        Executes the ingestion pipeline. Returns total count of chunks processed.
        """
        # 1. Initialize Vector Database Schema
        logger.info("Initializing vector database schema...")
        self.qdrant_manager.setup_collection()
        
        # 2. Get active Spark context
        logger.info("Getting/Creating SparkSession...")
        spark = self.spark_manager.get_or_create_session()
        
        try:
            raw_data_path = os.path.join(data_directory, "*.txt")
            logger.info(f"Reading raw corporate logs from: '{raw_data_path}'")
            
            # Load whole text files as (filepath, content) tuples
            rdd_raw = spark.sparkContext.wholeTextFiles(raw_data_path)
            df_raw = rdd_raw.toDF(["file_path", "raw_content"])
            
            if df_raw.count() == 0:
                logger.error(f"No source files found in data directory: {data_directory}")
                raise FileNotFoundError(f"No files found at {raw_data_path}")
                
            # 3. Clean Text and Hash
            df_clean = df_raw.withColumn(
                "cleaned_content", 
                F.regexp_replace(F.trim(df_raw.raw_content), r"\s+", " ")
            ).filter(F.col("cleaned_content") != "").withColumn(
                "doc_id", 
                F.sha2(F.col("cleaned_content"), 256)
            )
            
            # 4. Chunking (using UDF + Recursive Chunker)
            def _get_chunks_wrapper(text):
                from src.utils.chunker import RecursiveCharacterChunker
                chunker = RecursiveCharacterChunker(chunk_size=500, chunk_overlap=50)
                chunks = chunker.chunk_text(text)
                return [{"chunk_text": chunk, "chunk_index": idx} for idx, chunk in enumerate(chunks)]
                
            chunk_schema = ArrayType(
                StructType([
                    StructField("chunk_text", StringType(), False),
                    StructField("chunk_index", IntegerType(), False)
                ])
            )
            get_chunks_udf = F.udf(_get_chunks_wrapper, chunk_schema)
            
            # Explode chunks into separate rows
            df_chunks = df_clean.withColumn(
                "chunks_arr", 
                get_chunks_udf(F.col("cleaned_content"))
            ).withColumn(
                "chunk_data", 
                F.explode(F.col("chunks_arr"))
            ).select(
                F.col("doc_id"),
                F.col("chunk_data.chunk_text").alias("chunk_text"),
                F.col("chunk_data.chunk_index").alias("chunk_index")
            )
            
            logger.info("Distributed embedding calculation starting in parallel partitions...")
            # 5. Extract Embeddings (in parallel) and collect results back to the driver
            raw_points = df_chunks.rdd.mapPartitions(embed_partition).collect()
            total_chunks = len(raw_points)
            logger.info(f"Successfully generated {total_chunks} embeddings. Initiating serial database inserts...")
            
            # 6. Serial insertion from driver to avoid database file locks in embedded mode
            from qdrant_client.models import PointStruct, SparseVector
            points = []
            for p in raw_points:
                points.append(
                    PointStruct(
                        id=p["id"],
                        vector={
                            "text-dense": p["dense_emb"],
                            "text-sparse": SparseVector(
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
                    self.qdrant_manager.upsert_points(points)
                    points = []
            if points:
                self.qdrant_manager.upsert_points(points)
                
            logger.info(f"Ingestion completed. Indexed {total_chunks} chunks.")
            return total_chunks
            
        finally:
            logger.info("Stopping Spark Session...")
            self.spark_manager.stop_session()

if __name__ == "__main__":
    # Test script standalone execution path
    spark_m = SparkSessionManager()
    qdrant_m = QdrantConnectionManager()
    pipeline = RAGIngestionPipeline(spark_m, qdrant_m)
    pipeline.run()
