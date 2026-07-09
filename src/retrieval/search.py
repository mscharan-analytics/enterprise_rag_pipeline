import time
from qdrant_client import QdrantClient
from qdrant_client import models
from sentence_transformers import SentenceTransformer, CrossEncoder

from src.config import (
    USE_EMBEDDED_QDRANT, QDRANT_URL, QDRANT_STORAGE_PATH,
    COLLECTION_NAME, EMBEDDING_MODEL_NAME, RERANK_MODEL_NAME
)
from src.retrieval.sparse_encoder import SparseEncoder

class RAGSearchEngine:
    """
    Two-stage hybrid retrieval engine that combines:
    1. Dense Embeddings (SentenceTransformers)
    2. Sparse Text Embeddings (Custom TF-IDF Index)
    Merged using Reciprocal Rank Fusion (RRF) in Qdrant, followed by
    3. Cross-Encoder Reranking to extract the top-K contexts.
    """
    def __init__(self):
        # Initialize Qdrant Client based on configurations
        if USE_EMBEDDED_QDRANT:
            print(f"Initializing Qdrant Client in EMBEDDED MODE at '{QDRANT_STORAGE_PATH}'...")
            self.client = QdrantClient(path=QDRANT_STORAGE_PATH)
        else:
            print(f"Initializing Qdrant Client connecting to Docker container at '{QDRANT_URL}'...")
            self.client = QdrantClient(url=QDRANT_URL)
            
        # Initialize Dense and Sparse Encoders
        print(f"Loading dense embedding model: {EMBEDDING_MODEL_NAME}...")
        self.dense_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        self.sparse_encoder = SparseEncoder()
        
        # Initialize Reranker Model
        print(f"Loading cross-encoder reranker model: {RERANK_MODEL_NAME}...")
        self.reranker = CrossEncoder(RERANK_MODEL_NAME)
        
    def search(self, query_text: str, top_k_hybrid: int = 50, top_k_rerank: int = 5) -> dict:
        """
        Executes hybrid search + reranking and returns the top contexts alongside detailed latency breakdown.
        """
        metrics = {}
        
        # --- Stage 1: Vector & Sparse Index Generation ---
        t0 = time.perf_counter()
        dense_vector = self.dense_model.encode(query_text, convert_to_numpy=True).tolist()
        t1 = time.perf_counter()
        metrics["dense_embedding_ms"] = (t1 - t0) * 1000
        
        t0_sparse = time.perf_counter()
        sparse_vector = self.sparse_encoder.encode(query_text)
        t1_sparse = time.perf_counter()
        metrics["sparse_embedding_ms"] = (t1_sparse - t0_sparse) * 1000
        
        # --- Stage 1.5: Qdrant Hybrid Query (RRF) ---
        t0_search = time.perf_counter()
        try:
            # Execute Qdrant Query API using Reciprocal Rank Fusion (RRF)
            prefetch = [
                models.Prefetch(
                    query=dense_vector,
                    using="text-dense",
                    limit=top_k_hybrid
                ),
                models.Prefetch(
                    query=models.SparseVector(
                        indices=sparse_vector["indices"],
                        values=sparse_vector["values"]
                    ),
                    using="text-sparse",
                    limit=top_k_hybrid
                )
            ]
            
            response = self.client.query_points(
                collection_name=COLLECTION_NAME,
                prefetch=prefetch,
                query=models.FusionQuery(
                    fusion=models.Fusion.RRF
                ),
                limit=top_k_hybrid
            )
            
            # Map response points to list of dictionaries
            raw_hits = []
            for hit in response.points:
                raw_hits.append({
                    "id": hit.id,
                    "doc_id": hit.payload.get("doc_id"),
                    "chunk_text": hit.payload.get("chunk_text"),
                    "chunk_index": hit.payload.get("chunk_index"),
                    "score": hit.score  # RRF score
                })
        except Exception as e:
            print(f"Qdrant query failed: {e}. Fallback to dense-only search.")
            # Fallback to pure-dense search if sparse index is uninitialized
            response = self.client.search(
                collection_name=COLLECTION_NAME,
                query_vector=("text-dense", dense_vector),
                limit=top_k_hybrid
            )
            raw_hits = []
            for hit in response:
                raw_hits.append({
                    "id": hit.id,
                    "doc_id": hit.payload.get("doc_id"),
                    "chunk_text": hit.payload.get("chunk_text"),
                    "chunk_index": hit.payload.get("chunk_index"),
                    "score": hit.score
                })
                
        t1_search = time.perf_counter()
        metrics["db_hybrid_search_ms"] = (t1_search - t0_search) * 1000
        metrics["retrieval_total_ms"] = metrics["dense_embedding_ms"] + metrics["sparse_embedding_ms"] + metrics["db_hybrid_search_ms"]
        
        # --- Stage 2: Cross-Encoder Reranking ---
        if not raw_hits:
            return {
                "results": [],
                "metrics": metrics
            }
            
        t0_rerank = time.perf_counter()
        # Build evaluation pairs for cross-encoder
        pairs = [[query_text, hit["chunk_text"]] for hit in raw_hits]
        rerank_scores = self.reranker.predict(pairs).tolist()
        
        # Attach rerank score to each hit and sort
        for hit, score in zip(raw_hits, rerank_scores):
            hit["rerank_score"] = score
            
        reranked_hits = sorted(raw_hits, key=lambda x: x["rerank_score"], reverse=True)
        top_reranked = reranked_hits[:top_k_rerank]
        
        t1_rerank = time.perf_counter()
        metrics["reranking_ms"] = (t1_rerank - t0_rerank) * 1000
        metrics["pipeline_total_ms"] = metrics["retrieval_total_ms"] + metrics["reranking_ms"]
        
        return {
            "results": top_reranked,
            "raw_hits": raw_hits,  # Returned for UI diagnostics
            "metrics": metrics
        }
