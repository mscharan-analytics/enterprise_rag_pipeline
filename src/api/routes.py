import time
from fastapi import APIRouter, Request, HTTPException
from src.api.schemas import QueryRequest, QueryResponse, IngestResponse, HealthResponse, ChunkDetail
from src.utils.logger import setup_logger

logger = setup_logger("api_routes")
router = APIRouter()

@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Standard container health probe checking service readiness.
    """
    return HealthResponse(
        status="healthy",
        timestamp=time.strftime("%Y-%m-%d %H:%M:%SZ", time.gmtime())
    )

@router.post("/ingest", response_model=IngestResponse)
async def trigger_ingestion(request: Request):
    """
    Triggers the PySpark ingestion job to clean, chunk, hash, and load documents.
    """
    pipeline = getattr(request.app.state, "ingestion_pipeline", None)
    if not pipeline:
        raise HTTPException(status_code=503, detail="Ingestion service is not initialized.")
        
    try:
        logger.info("REST Ingest Request received. Launching PySpark job...")
        total_chunks = pipeline.run()
        return IngestResponse(status="success", total_chunks=total_chunks)
    except Exception as e:
        logger.error(f"Ingestion API call failed: {e}")
        raise HTTPException(status_code=500, detail=f"Ingestion failure: {str(e)}")

@router.post("/query", response_model=QueryResponse)
async def query_pipeline(request: Request, payload: QueryRequest):
    """
    Receives query, retrieves relevant chunks, reranks them, and synthesizes an answer.
    """
    search_engine = getattr(request.app.state, "search_engine", None)
    if not search_engine:
        raise HTTPException(status_code=503, detail="Search service is not initialized.")
        
    try:
        logger.info(f"REST Query Request received: '{payload.query}'")
        search_results = search_engine.search(
            payload.query,
            top_k_hybrid=payload.top_k_hybrid,
            top_k_rerank=payload.top_k_rerank
        )
        
        # Smart synthesized answer mock generator (mimicking the LLM response builder)
        answer = _synthesize_mock_answer(payload.query, search_results["results"])
        
        # Convert response chunks to schema models
        response_chunks = []
        for r in search_results["results"]:
            response_chunks.append(
                ChunkDetail(
                    id=r["id"],
                    doc_id=r["doc_id"],
                    chunk_text=r["chunk_text"],
                    chunk_index=r["chunk_index"],
                    score=r["score"],
                    rerank_score=r["rerank_score"]
                )
            )
            
        return QueryResponse(
            query=payload.query,
            answer=answer,
            metrics=search_results["metrics"],
            results=response_chunks
        )
    except Exception as e:
        logger.error(f"Query API call failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query engine failure: {str(e)}")

def _synthesize_mock_answer(query: str, contexts: list) -> str:
    """
    Synthesizes answer summary based on query content and matched chunks.
    """
    if not contexts:
        return "I apologize, but no relevant document chunks were found in the database."
        
    query_lower = query.lower()
    
    if "clinical" in query_lower or "patient" in query_lower or "medical" in query_lower:
        base = "### 🩺 Synthesized Clinical Summary\nBased on patient records matching the inquiry, we noted:\n\n"
        for i, c in enumerate(contexts[:2]):
            base += f"- **Patient Context {i+1}**: {c['chunk_text']}\n"
        return base
    elif "ticket" in query_lower or "error" in query_lower or "fail" in query_lower or "service" in query_lower:
        base = "### 💻 Infrastructure Incident Report\nAn analysis of the server logs indicates the following events occurred:\n\n"
        for i, c in enumerate(contexts[:2]):
            base += f"- **Incident Note {i+1}**: {c['chunk_text']}\n"
        return base
    elif "policy" in query_lower or "sop" in query_lower or "employee" in query_lower:
        base = "### 📋 Corporate Operations Policy Summary\nAccording to the guidelines retrieved from the HR directory:\n\n"
        for i, c in enumerate(contexts[:2]):
            base += f"- **Policy excerpt {i+1}**: {c['chunk_text']}\n"
        return base
    else:
        base = "### 🔍 Synthesized Context\nThe search matched multiple corporate documents. Summarizing relevant entries:\n\n"
        for i, c in enumerate(contexts[:3]):
            base += f"- **Entry {i+1}** (Doc ID: `{c['doc_id'][:12]}...`): {c['chunk_text']}\n"
        return base
