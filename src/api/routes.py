import os
import time
import io
import hashlib
import uuid
from fastapi import APIRouter, Request, HTTPException, UploadFile, File
import pypdf

# Import LLM clients
from openai import OpenAI
from groq import Groq

from src.api.schemas import (
    QueryRequest, QueryResponse, IngestResponse, HealthResponse, ChunkDetail, 
    S3IngestRequest, AnalyticsResponse, AnalyticsBreakdown
)
from src.utils.token_tracker import TokenCostTracker
from src.utils.chunker import RecursiveCharacterChunker
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
    Triggers local directory document ingestion using distributed PySpark.
    """
    pipeline = getattr(request.app.state, "ingestion_pipeline", None)
    if not pipeline:
        raise HTTPException(status_code=503, detail="Ingestion service is not initialized.")
        
    try:
        logger.info("REST Ingest Request received. Launching PySpark job...")
        total_chunks = pipeline.run(from_s3=False)
        return IngestResponse(status="success", total_chunks=total_chunks)
    except ValueError as ve:
        logger.error(f"Ingestion validation failed: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Ingestion API call failed: {e}")
        raise HTTPException(status_code=500, detail=f"Ingestion failure: {str(e)}")

@router.post("/ingest/s3", response_model=IngestResponse)
async def trigger_s3_ingestion(request: Request, payload: S3IngestRequest):
    """
    Triggers AWS S3 / Lakehouse document ingestion using distributed PySpark.
    Downloads files from S3 first (or local mock folder fallback) and runs Spark.
    """
    pipeline = getattr(request.app.state, "ingestion_pipeline", None)
    if not pipeline:
        raise HTTPException(status_code=503, detail="Ingestion service is not initialized.")
        
    try:
        logger.info(f"REST S3 Ingest Request received. Bucket: '{payload.bucket}', Prefix: '{payload.prefix}'")
        
        # Override bucket configurations if provided
        if payload.bucket:
            pipeline.s3_manager.bucket_name = payload.bucket
        if payload.prefix:
            pipeline.s3_manager.prefix = payload.prefix
            
        total_chunks = pipeline.run(from_s3=True)
        return IngestResponse(status="success", total_chunks=total_chunks)
    except ValueError as ve:
        logger.error(f"S3 Ingestion validation failed: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"S3 Ingestion API call failed: {e}")
        raise HTTPException(status_code=500, detail=f"S3 Ingestion failure: {str(e)}")

@router.post("/upload", response_model=IngestResponse)
async def upload_file(
    request: Request,
    file: UploadFile = File(...)
):
    """
    Direct multi-part file upload route. Receives PDF or TXT files, extracts text,
    chunks it, embeds it on CPU, and pushes it to Pinecone immediately (bypassing Spark for quick files).
    """
    search_engine = getattr(request.app.state, "search_engine", None)
    pinecone_manager = getattr(request.app.state, "pinecone_manager", None)
    
    if not search_engine or not pinecone_manager:
        raise HTTPException(status_code=503, detail="Search or Pinecone service is not initialized.")
        
    try:
        contents = await file.read()
        filename = file.filename.lower()
        
        logger.info(f"File upload request received. Filename: '{filename}', Size: {len(contents)} bytes")
        text = ""
        
        # 1. Parse content based on file extension
        if filename.endswith(".pdf"):
            pdf_file = io.BytesIO(contents)
            reader = pypdf.PdfReader(pdf_file)
            text_list = []
            for idx, page in enumerate(reader.pages):
                page_text = page.extract_text()
                if page_text:
                    text_list.append(page_text)
            text = " ".join(text_list)
        else:
            # Fallback to UTF-8 text decoding
            text = contents.decode("utf-8", errors="ignore")
            
        cleaned_text = " ".join(text.strip().split())
        if not cleaned_text:
            raise HTTPException(status_code=400, detail="Uploaded file contains no readable text.")
            
        # 2. Document hashing
        doc_id = hashlib.sha256(cleaned_text.encode("utf-8")).hexdigest()
        
        # 3. Chunk text using utility
        chunker = RecursiveCharacterChunker(chunk_size=500, chunk_overlap=50)
        chunks = chunker.chunk_text(cleaned_text)
        
        if not chunks:
            return IngestResponse(status="success", total_chunks=0)
            
        # 4. Generate embeddings and upsert to Pinecone
        vectors = []
        for idx, chunk in enumerate(chunks):
            dense_emb = search_engine.dense_model.encode(chunk, convert_to_numpy=True).tolist()
            sparse_vec = search_engine.sparse_encoder.encode(chunk)
            point_id = str(uuid.uuid5(uuid.NAMESPACE_DNS, f"{doc_id}_{idx}"))
            
            vectors.append({
                "id": point_id,
                "values": dense_emb,
                "sparse_values": {
                    "indices": sparse_vec["indices"],
                    "values": sparse_vec["values"]
                },
                "metadata": {
                    "doc_id": doc_id,
                    "chunk_text": chunk,
                    "chunk_index": idx
                }
            })
            
            if len(vectors) >= 50:
                pinecone_manager.upsert_vectors(vectors)
                vectors = []
                
        if vectors:
            pinecone_manager.upsert_vectors(vectors)
            
        # Track cost analytics
        TokenCostTracker.track_ingestion(len(chunks), cleaned_text)
        
        logger.info(f"File upload ingestion complete. Indexed {len(chunks)} chunks.")
        return IngestResponse(status="success", total_chunks=len(chunks))
        
    except HTTPException:
        raise
    except ValueError as ve:
        logger.error(f"File upload validation failed: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"File upload route failed: {e}")
        raise HTTPException(status_code=500, detail=f"File upload failure: {str(e)}")

@router.post("/query", response_model=QueryResponse)
async def query_pipeline(request: Request, payload: QueryRequest):
    """
    Receives query, retrieves relevant chunks, reranks them, and synthesizes an answer using an LLM.
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
        
        # Real E2E LLM Generator synthesis (with mock fallback)
        answer = _generate_llm_answer(payload.query, search_results["results"])
        
        # Convert response chunks to schema models
        response_chunks = []
        for r in search_results["results"]:
            response_chunks.append(
                ChunkDetail(
                    id=r["id"],
                    doc_id=r["doc_id"],
                    chunk_text=r["chunk_text"],
                    chunk_index=int(r["chunk_index"]),
                    score=r["score"],
                    rerank_score=r["rerank_score"]
                )
            )
            
        # Log query metrics in TokenCostTracker
        TokenCostTracker.track_query(payload.query, search_results["results"], answer)
            
        return QueryResponse(
            query=payload.query,
            answer=answer,
            metrics=search_results["metrics"],
            results=response_chunks
        )
    except ValueError as ve:
        logger.error(f"Query validation failed: {ve}")
        raise HTTPException(status_code=400, detail=str(ve))
    except Exception as e:
        logger.error(f"Query API call failed: {e}")
        raise HTTPException(status_code=500, detail=f"Query engine failure: {str(e)}")

@router.get("/analytics", response_model=AnalyticsResponse)
async def get_analytics_snapshot():
    """
    Returns the accumulated query costs and token metrics tracker.
    """
    data = TokenCostTracker.get_analytics()
    breakdown = AnalyticsBreakdown(
        embedding=data["cost_breakdown"]["embedding"],
        rerank=data["cost_breakdown"]["rerank"],
        llm_input=data["cost_breakdown"]["llm_input"],
        llm_output=data["cost_breakdown"]["llm_output"],
        db_write=data["cost_breakdown"]["db_write"]
    )
    return AnalyticsResponse(
        total_queries=data["total_queries"],
        total_ingests=data["total_ingests"],
        total_tokens=data["total_tokens"],
        total_cost=data["total_cost"],
        cost_breakdown=breakdown
    )

def _generate_llm_answer(query: str, contexts: list) -> str:
    """
    Synthesizes response by calling Groq or OpenAI APIs if key is set in environment,
    otherwise falls back to structured template synthesis.
    """
    if not contexts:
        return "I apologize, but no relevant document chunks were found in the database."

    # Format the prompt context
    context_text = "\n\n".join([f"Document Segment {i+1}:\n{c['chunk_text']}" for i, c in enumerate(contexts)])
    
    system_prompt = (
        "You are an enterprise document intelligence assistant. Synthesize a concise, "
        "accurate answer based ONLY on the provided document segments. Cite document sources if applicable."
    )
    user_prompt = f"Context segments:\n{context_text}\n\nQuery: {query}"
    
    # 1. Attempt Groq API connection (free fast LLM tier)
    if os.getenv("GROQ_API_KEY"):
        try:
            logger.info("Calling Groq API for synthesis...")
            client = Groq()
            chat_completion = client.chat.completions.create(
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                model="llama3-8b-8192",
                temperature=0.2,
                max_tokens=500
            )
            return chat_completion.choices[0].message.content
        except Exception as e:
            logger.warning(f"Groq API call failed: {e}. Falling back...")
            
    # 2. Attempt OpenAI connection
    if os.getenv("OPENAI_API_KEY"):
        try:
            logger.info("Calling OpenAI API for synthesis...")
            client = OpenAI()
            completion = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.2,
                max_tokens=500
            )
            return completion.choices[0].message.content
        except Exception as e:
            logger.warning(f"OpenAI API call failed: {e}. Falling back...")

    # 3. Static fallback if no LLM key is configured
    logger.info("No LLM keys found in environment. Generating template-based mock answer.")
    return _synthesize_mock_answer(query, contexts)


def _synthesize_mock_answer(query: str, contexts: list) -> str:
    """
    Synthesizes answer summary based on query content and matched chunks.
    """
    query_lower = query.lower()
    
    if "clinical" in query_lower or "patient" in query_lower or "medical" in query_lower:
        base = "### 🩺 Clinical Analysis Summary\nBased on patient records matching the inquiry, we noted:\n\n"
        for i, c in enumerate(contexts[:2]):
            base += f"- **Patient Context {i+1}**: {c['chunk_text']}\n"
        return base
    elif "ticket" in query_lower or "error" in query_lower or "fail" in query_lower or "service" in query_lower:
        base = "### 💻 System Incident Report\nAn analysis of the server logs indicates the following events occurred:\n\n"
        for i, c in enumerate(contexts[:2]):
            base += f"- **Incident Note {i+1}**: {c['chunk_text']}\n"
        return base
    elif "policy" in query_lower or "sop" in query_lower or "employee" in query_lower or "travel" in query_lower:
        base = "### 📋 Corporate Operations Policy Summary\nAccording to the guidelines retrieved from the HR directory:\n\n"
        for i, c in enumerate(contexts[:2]):
            base += f"- **Policy excerpt {i+1}**: {c['chunk_text']}\n"
        return base
    else:
        base = "### 🔍 Synthesized Context Summary\nThe search matched multiple corporate documents. Summarizing relevant entries:\n\n"
        for i, c in enumerate(contexts[:3]):
            base += f"- **Entry {i+1}** (Doc ID: `{c['doc_id'][:12]}...`): {c['chunk_text']}\n"
        return base
