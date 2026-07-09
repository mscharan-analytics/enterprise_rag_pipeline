from pydantic import BaseModel, Field
from typing import List, Optional, Dict

class QueryRequest(BaseModel):
    query: str = Field(..., description="The user query or prompt to answer.")
    top_k_hybrid: int = Field(30, description="Stage 1: Top-K hybrid matches to retrieve from Pinecone.")
    top_k_rerank: int = Field(5, description="Stage 2: Top-K context pieces to return after reranking.")

class ChunkDetail(BaseModel):
    id: str = Field(..., description="Unique Point UUID.")
    doc_id: str = Field(..., description="SHA-256 unique ID of the source document.")
    chunk_text: str = Field(..., description="The raw context text of this chunk.")
    chunk_index: int = Field(..., description="The position offset of this chunk in the doc.")
    score: float = Field(..., description="Stage 1 Pinecone hybrid score.")
    rerank_score: Optional[float] = Field(None, description="Stage 2 Cross-Encoder rerank score.")

class QueryResponse(BaseModel):
    query: str
    answer: str = Field(..., description="Synthesized answer from retrieved documents.")
    metrics: Dict[str, float] = Field(..., description="Detailed execution timing breakdown in ms.")
    results: List[ChunkDetail] = Field(..., description="Top context documents matching the query.")

class IngestResponse(BaseModel):
    status: str = Field("success", description="Ingestion status message.")
    total_chunks: int = Field(..., description="Total count of text chunks successfully indexed.")

class S3IngestRequest(BaseModel):
    bucket: Optional[str] = Field(None, description="Target S3 Bucket override.")
    prefix: Optional[str] = Field(None, description="Target S3 Prefix override.")

class AnalyticsBreakdown(BaseModel):
    embedding: float
    rerank: float
    llm_input: float
    llm_output: float
    db_write: float

class AnalyticsResponse(BaseModel):
    total_queries: int
    total_ingests: int
    total_tokens: int
    total_cost: float
    cost_breakdown: AnalyticsBreakdown

class HealthResponse(BaseModel):
    status: str = Field("healthy", description="Status code of the container.")
    timestamp: str
