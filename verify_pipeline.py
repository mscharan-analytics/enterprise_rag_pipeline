import os
import sys

# macOS and PySpark environment safety configurations
os.environ["OBJC_DISABLE_INITIALIZE_FORK_SAFETY"] = "YES"
os.environ["TOKENIZERS_PARALLELISM"] = "false"
os.environ["SPARK_PYTHON_WORKER_FAULTHANDLER_ENABLED"] = "true"
os.environ["PYSPARK_PYTHON"] = sys.executable
os.environ["PYSPARK_DRIVER_PYTHON"] = sys.executable

# Ensure Java environment variables are set correctly for local PySpark
os.environ["JAVA_HOME"] = "/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home"
os.environ["PATH"] = f"/opt/homebrew/opt/openjdk@17/libexec/openjdk.jdk/Contents/Home/bin:{os.environ.get('PATH', '')}"

# Add current directory to python path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from data import generate_data
from src.connections.spark import SparkSessionManager
from src.connections.pinecone import PineconeConnectionManager
from src.connections.s3 import S3ConnectionManager
from src.ingestion.pipeline import RAGIngestionPipeline
from src.retrieval.search import RAGSearchEngine

def main():
    print("=== [RAG OOP Pipeline Verification Start] ===")
    
    # 1. Generate Dataset
    print("\n1. Triggering data generation...")
    generate_data.main()
    
    # 2. Instantiate managers
    print("\n2. Initializing OOP Connection Managers...")
    spark_manager = SparkSessionManager()
    pinecone_manager = PineconeConnectionManager()
    s3_manager = S3ConnectionManager()
    
    # 3. Launch Ingestion
    print("\n3. Launching RAG Ingestion Pipeline...")
    pipeline = RAGIngestionPipeline(spark_manager, pinecone_manager, s3_manager)
    total_indexed = pipeline.run()
    print(f"Ingested {total_indexed} chunks successfully.")
    
    # 4. Instantiate Search
    print("\n4. Initializing RAG Search Engine...")
    engine = RAGSearchEngine(pinecone_manager)
    
    # 5. Run Test Queries
    queries = [
        "Find a clinical log mentioning patient symptoms or diagnosis of contact dermatitis",
        "Which support tickets report a database connection timeout or memory leak?",
        "What is the standard operating procedure travel expense guideline?"
    ]
    
    print("\n5. Running test search queries...")
    for i, query in enumerate(queries, 1):
        print(f"\n--- Test Query {i}: '{query}' ---")
        results = engine.search(query, top_k_hybrid=15, top_k_rerank=2)
        
        print(f"Latency Performance Metrics:")
        for k, v in results["metrics"].items():
            print(f"  - {k}: {v:.2f} ms")
            
        print("\nTop 2 Reranked Context Results:")
        for rank, res in enumerate(results["results"], 1):
            print(f"  [{rank}] Doc: {res['doc_id'][:12]}... (Chunk {res['chunk_index']}) | Rerank Score: {res['rerank_score']:.4f}")
            print(f"      Text: {res['chunk_text'][:150]}...")
            
    print("\n=== [RAG OOP Pipeline Verification Complete] ===")

if __name__ == "__main__":
    main()
