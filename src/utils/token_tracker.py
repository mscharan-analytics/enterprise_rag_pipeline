import threading
from src.config import (
    PRICE_EMBEDDING_PER_1K, PRICE_RERANK_PER_1K, PRICE_LLM_INPUT_PER_1K,
    PRICE_LLM_OUTPUT_PER_1K, PRICE_PINECONE_UPSERT_PER_1K
)
from src.utils.logger import setup_logger

logger = setup_logger("token_tracker")

class TokenCostTracker:
    """
    A thread-safe singleton tracker for logging token consumption and cost metrics
    across the entire lifespans of ingestion and query services.
    """
    _lock = threading.Lock()
    _analytics = {
        "total_queries": 0,
        "total_ingests": 0,
        "total_tokens": 0,
        "total_cost": 0.0,
        "cost_breakdown": {
            "embedding": 0.0,
            "rerank": 0.0,
            "llm_input": 0.0,
            "llm_output": 0.0,
            "db_write": 0.0
        }
    }

    @classmethod
    def estimate_tokens(cls, text: str) -> int:
        """
        Estimates the number of tokens in a given string using the standard
        character-based heuristic (average of 4 characters per token).
        """
        if not text:
            return 0
        return max(1, int(len(text) / 4))

    @classmethod
    def track_ingestion(cls, chunk_count: int, total_text: str) -> dict:
        """
        Tracks costs associated with distributed PySpark ingestion (dense embeddings + DB writes).
        """
        tokens = cls.estimate_tokens(total_text)
        embedding_cost = (tokens / 1000.0) * PRICE_EMBEDDING_PER_1K
        db_write_cost = (chunk_count / 1000.0) * PRICE_PINECONE_UPSERT_PER_1K
        added_cost = embedding_cost + db_write_cost

        with cls._lock:
            cls._analytics["total_ingests"] += 1
            cls._analytics["total_tokens"] += tokens
            cls._analytics["total_cost"] += added_cost
            cls._analytics["cost_breakdown"]["embedding"] += embedding_cost
            cls._analytics["cost_breakdown"]["db_write"] += db_write_cost

        logger.info(f"Tracked Ingestion: Chunks={chunk_count}, EstTokens={tokens}, Cost=${added_cost:.6f}")
        return {"tokens": tokens, "cost": added_cost}

    @classmethod
    def track_query(cls, query_text: str, retrieved_contexts: list, answer_text: str) -> dict:
        """
        Tracks costs associated with a RAG query (hybrid embedding lookup + reranking + LLM synthesis).
        """
        query_tokens = cls.estimate_tokens(query_text)
        
        # 1. Stage 1 Retrieval (Query embeddings: dense + sparse)
        embedding_cost = (query_tokens / 1000.0) * PRICE_EMBEDDING_PER_1K
        
        # 2. Stage 2 Reranking (We compare query to each retrieved context)
        context_text = " ".join([c.get("chunk_text", "") if isinstance(c, dict) else getattr(c, "chunk_text", "") for c in retrieved_contexts])
        context_tokens = cls.estimate_tokens(context_text)
        rerank_input_tokens = (query_tokens * len(retrieved_contexts)) + context_tokens
        rerank_cost = (rerank_input_tokens / 1000.0) * PRICE_RERANK_PER_1K
        
        # 3. LLM Synthesis (Prompt = query + contexts; Output = synthesized answer)
        llm_prompt_tokens = query_tokens + context_tokens
        llm_generation_tokens = cls.estimate_tokens(answer_text)
        
        llm_input_cost = (llm_prompt_tokens / 1000.0) * PRICE_LLM_INPUT_PER_1K
        llm_output_cost = (llm_generation_tokens / 1000.0) * PRICE_LLM_OUTPUT_PER_1K
        llm_cost = llm_input_cost + llm_output_cost
        
        added_cost = embedding_cost + rerank_cost + llm_cost
        total_tokens = query_tokens + rerank_input_tokens + llm_prompt_tokens + llm_generation_tokens

        with cls._lock:
            cls._analytics["total_queries"] += 1
            cls._analytics["total_tokens"] += total_tokens
            cls._analytics["total_cost"] += added_cost
            cls._analytics["cost_breakdown"]["embedding"] += embedding_cost
            cls._analytics["cost_breakdown"]["rerank"] += rerank_cost
            cls._analytics["cost_breakdown"]["llm_input"] += llm_input_cost
            cls._analytics["cost_breakdown"]["llm_output"] += llm_output_cost

        logger.info(f"Tracked Query: EstTokens={total_tokens}, Cost=${added_cost:.6f}")
        return {
            "tokens": total_tokens,
            "cost": added_cost,
            "breakdown": {
                "embedding": embedding_cost,
                "rerank": rerank_cost,
                "llm_input": llm_input_cost,
                "llm_output": llm_output_cost
            }
        }

    @classmethod
    def get_analytics(cls) -> dict:
        """
        Returns a snapshot copy of the cumulative tracking details.
        """
        with cls._lock:
            return dict(cls._analytics)
