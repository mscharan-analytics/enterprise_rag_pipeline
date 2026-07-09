from fastapi import FastAPI
from contextlib import asynccontextmanager
import uvicorn

from src.connections.qdrant import QdrantConnectionManager
from src.connections.spark import SparkSessionManager
from src.ingestion.pipeline import RAGIngestionPipeline
from src.retrieval.search import RAGSearchEngine
from src.api.routes import router
from src.utils.logger import setup_logger

logger = setup_logger("api_main")

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    FastAPI Lifespan handler that sets up RAG components on app startup
    and handles connection teardown on app shutdown.
    """
    logger.info("Initializing REST API backend components...")
    
    # 1. Instantiate managers
    spark_manager = SparkSessionManager()
    qdrant_manager = QdrantConnectionManager()
    
    # 2. Instantiate engines
    ingestion_pipeline = RAGIngestionPipeline(spark_manager, qdrant_manager)
    search_engine = RAGSearchEngine(qdrant_manager)
    
    # 3. Cache services in app state
    app.state.ingestion_pipeline = ingestion_pipeline
    app.state.search_engine = search_engine
    
    logger.info("REST API dependencies loaded.")
    yield
    
    # Clean up Spark Session on shutdown
    logger.info("Cleaning up backend sessions...")
    spark_manager.stop_session()
    logger.info("REST API backend shutdown complete.")

# Create FastAPI app
app = FastAPI(
    title="Enterprise Scale-Ready RAG REST API",
    description="Production REST API controller for hybrid vector search and Spark data ingestion",
    version="1.0.0",
    lifespan=lifespan
)

# Register routes controller
app.include_router(router, prefix="/api/v1")

if __name__ == "__main__":
    logger.info("Launching backend server on http://localhost:8000")
    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=False)
