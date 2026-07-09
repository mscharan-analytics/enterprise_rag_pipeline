import time
from sentence_transformers import SentenceTransformer, CrossEncoder

from src.config import EMBEDDING_MODEL_NAME, RERANK_MODEL_NAME
from src.connections.pinecone import PineconeConnectionManager
from src.utils.sparse_encoder import SparseEncoder
from src.utils.logger import setup_logger

logger = setup_logger("search_engine")

class RAGSearchEngine:
    """
    Core search engine that implements a production-grade 2-stage retrieval pipeline:
    Stage 1: Dual-Vector Hybrid Search (Dense Cosine Similarity + Sparse Term Matching)
             fused via Pinecone Cloud sparse-dense lookup.
    Stage 2: Cross-Encoder Reranking to surface the top-K contexts.
    """
    def __init__(self, pinecone_manager: PineconeConnectionManager):
        self.pinecone_manager = pinecone_manager
        
        # Load encoders
        logger.info(f"Loading dense embedding model on CPU: {EMBEDDING_MODEL_NAME}...")
        self.dense_model = SentenceTransformer(EMBEDDING_MODEL_NAME, device="cpu")
        self.sparse_encoder = SparseEncoder()
        
        # Load cross-encoder reranker
        logger.info(f"Loading cross-encoder reranker model on CPU: {RERANK_MODEL_NAME}...")
        self.reranker = CrossEncoder(RERANK_MODEL_NAME, device="cpu")
        
    def search(self, query_text: str, top_k_hybrid: int = 50, top_k_rerank: int = 5) -> dict:
        """
        Executes hybrid search + cross-encoder reranking. Returns results and timing metrics.
        """
        metrics = {}
        
        # --- Stage 1a: Dense vector generation ---
        t0 = time.perf_counter()
        dense_vector = self.dense_model.encode(query_text, convert_to_numpy=True).tolist()
        t1 = time.perf_counter()
        metrics["dense_embedding_ms"] = (t1 - t0) * 1000
        
        # --- Stage 1b: Sparse vector generation ---
        t0_sparse = time.perf_counter()
        sparse_vector = self.sparse_encoder.encode(query_text)
        t1_sparse = time.perf_counter()
        metrics["sparse_embedding_ms"] = (t1_sparse - t0_sparse) * 1000
        
        # --- Stage 1c: Pinecone Hybrid Query ---
        t0_search = time.perf_counter()
        try:
            points = self.pinecone_manager.query_hybrid(
                dense_vector=dense_vector,
                sparse_indices=sparse_vector["indices"],
                sparse_values=sparse_vector["values"],
                limit=top_k_hybrid
            )
            
            raw_hits = []
            for hit in points:
                raw_hits.append({
                    "id": hit.id,
                    "doc_id": hit.payload.get("doc_id"),
                    "chunk_text": hit.payload.get("chunk_text"),
                    "chunk_index": hit.payload.get("chunk_index"),
                    "score": hit.score
                })
        except Exception as e:
            logger.error(f"Pinecone Hybrid Query failed: {e}. Falling back to dense-only search.")
            # Fallback to dense-only query
            index = self.pinecone_manager.get_index()
            response = index.query(
                vector=dense_vector,
                top_k=top_k_hybrid,
                include_metadata=True
            )
            raw_hits = []
            for match in response.matches:
                meta = match.metadata or {}
                raw_hits.append({
                    "id": match.id,
                    "doc_id": meta.get("doc_id"),
                    "chunk_text": meta.get("chunk_text"),
                    "chunk_index": meta.get("chunk_index"),
                    "score": match.score
                })
                
        t1_search = time.perf_counter()
        metrics["db_hybrid_search_ms"] = (t1_search - t0_search) * 1000
        metrics["retrieval_total_ms"] = metrics["dense_embedding_ms"] + metrics["sparse_embedding_ms"] + metrics["db_hybrid_search_ms"]
        
        # --- Stage 2: Cross-Encoder Reranking ---
        if not raw_hits:
            logger.info("No candidates returned from Stage 1 retrieval.")
            return {
                "results": [],
                "raw_hits": [],
                "metrics": metrics
            }
            
        t0_rerank = time.perf_counter()
        # Build query-chunk pairs
        pairs = [[query_text, hit["chunk_text"]] for hit in raw_hits]
        rerank_scores = self.reranker.predict(pairs).tolist()
        
        # Merge scores and sort
        for hit, score in zip(raw_hits, rerank_scores):
            hit["rerank_score"] = score
            
        reranked_hits = sorted(raw_hits, key=lambda x: x["rerank_score"], reverse=True)
        top_reranked = reranked_hits[:top_k_rerank]
        
        t1_rerank = time.perf_counter()
        metrics["reranking_ms"] = (t1_rerank - t0_rerank) * 1000
        metrics["pipeline_total_ms"] = metrics["retrieval_total_ms"] + metrics["reranking_ms"]
        
        return {
            "results": top_reranked,
            "raw_hits": raw_hits,
            "metrics": metrics
        }
