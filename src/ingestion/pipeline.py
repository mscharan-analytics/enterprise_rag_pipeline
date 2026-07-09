import os
import uuid
import tempfile
from pyspark.sql.types import ArrayType, StructType, StructField, StringType, IntegerType
import pyspark.sql.functions as F

from src.config import DATA_DIR
from src.connections.pinecone import PineconeConnectionManager
from src.connections.spark import SparkSessionManager
from src.connections.s3 import S3ConnectionManager
from src.utils.token_tracker import TokenCostTracker
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
    Supports AWS S3 Data Lakes and Local directories.
    """
    def __init__(
        self,
        spark_manager: SparkSessionManager,
        pinecone_manager: PineconeConnectionManager,
        s3_manager: S3ConnectionManager
    ):
        self.spark_manager = spark_manager
        self.pinecone_manager = pinecone_manager
        self.s3_manager = s3_manager

    def run(self, data_directory: str = DATA_DIR, from_s3: bool = False) -> int:
        """
        Executes the ingestion pipeline. 
        If from_s3 is True, pulls files from S3 first.
        Returns total count of chunks processed.
        """
        # 1. Sync from S3 Lakehouse if requested
        if from_s3:
            logger.info("Triggering S3 Lakehouse synchronization...")
            self.s3_manager.sync_to_local(data_directory)
            
        # 2. Initialize Vector Database Index
        logger.info("Initializing Pinecone Index schema...")
        self.pinecone_manager.setup_index()
        
        # 3. Get active Spark context
        logger.info("Getting/Creating SparkSession...")
        spark = self.spark_manager.get_or_create_session()
        
        try:
            raw_data_path = os.path.join(data_directory, "*")
            logger.info(f"Reading raw logs / documents from: '{raw_data_path}'")
            
            # Load whole text files as (filepath, content) tuples
            # Spark handles binary wholeTextFiles safely.
            rdd_raw = spark.sparkContext.wholeTextFiles(raw_data_path)
            df_raw = rdd_raw.toDF(["file_path", "raw_content"])
            
            # Filter only txt and pdf files (PDF text parsing is handled by the PDF API uploader,
            # while Spark handles raw text directories)
            df_text = df_raw.filter(
                (F.col("file_path").endswith(".txt")) | (F.col("file_path").endswith(".log"))
            )
            
            if df_text.count() == 0:
                logger.warning(f"No text files found in data directory: {data_directory}")
                return 0
                
            # 4. Clean Text and Hash
            df_clean = df_text.withColumn(
                "cleaned_content", 
                F.regexp_replace(F.trim(df_text.raw_content), r"\s+", " ")
            ).filter(F.col("cleaned_content") != "").withColumn(
                "doc_id", 
                F.sha2(F.col("cleaned_content"), 256)
            )
            
            # 5. Chunking (using UDF + Recursive Chunker)
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
            # 6. Extract Embeddings (in parallel) and collect results back to the driver
            raw_points = df_chunks.rdd.mapPartitions(embed_partition).collect()
            total_chunks = len(raw_points)
            
            if total_chunks == 0:
                logger.info("No text chunks generated.")
                return 0
                
            logger.info(f"Successfully generated {total_chunks} embeddings. Initiating serial database inserts...")
            
            # 7. Serial insertion from driver to avoid database indexing performance issues
            vectors = []
            all_text_list = []
            for p in raw_points:
                all_text_list.append(p["chunk_text"])
                vectors.append({
                    "id": p["id"],
                    "values": p["dense_emb"],
                    "sparse_values": {
                        "indices": p["sparse_indices"],
                        "values": p["sparse_values"]
                    },
                    "metadata": {
                        "doc_id": p["doc_id"],
                        "chunk_text": p["chunk_text"],
                        "chunk_index": int(p["chunk_index"])
                    }
                })
                if len(vectors) >= 100:
                    self.pinecone_manager.upsert_vectors(vectors)
                    vectors = []
            if vectors:
                self.pinecone_manager.upsert_vectors(vectors)
                
            # Track cost analytics
            all_text = " ".join(all_text_list)
            TokenCostTracker.track_ingestion(total_chunks, all_text)
            
            logger.info(f"Ingestion completed. Indexed {total_chunks} chunks.")
            return total_chunks
            
        finally:
            logger.info("Stopping Spark Session...")
            self.spark_manager.stop_session()

if __name__ == "__main__":
    # Test script standalone execution path
    spark_m = SparkSessionManager()
    pinecone_m = PineconeConnectionManager()
    s3_m = S3ConnectionManager()
    pipeline = RAGIngestionPipeline(spark_m, pinecone_m, s3_m)
    pipeline.run()
