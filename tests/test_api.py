import pytest
from fastapi.testclient import TestClient
from unittest.mock import MagicMock

# Import app but mock lifespan to prevent actual Spark/SentenceTransformer load during test imports
from src.api.main import app

@pytest.fixture
def test_client():
    # Mock ingestion pipeline
    mock_pipeline = MagicMock()
    mock_pipeline.run.return_value = 150
    
    # Mock search engine
    mock_search = MagicMock()
    mock_search.search.return_value = {
        "results": [
            {
                "id": "e0b4b2aa-4f2a-5a9d-b8d4-28b9d62d08a1",
                "doc_id": "test_sha_256_hash",
                "chunk_text": "This is a mocked RAG chunk response used for API schema validation.",
                "chunk_index": 2,
                "score": 0.048,
                "rerank_score": 0.985
            }
        ],
        "raw_hits": [],
        "metrics": {
            "dense_embedding_ms": 15.2,
            "sparse_embedding_ms": 0.4,
            "db_hybrid_search_ms": 12.1,
            "retrieval_total_ms": 27.7,
            "reranking_ms": 20.5,
            "pipeline_total_ms": 48.2
        }
    }
    
    # Yield client within context lifecycle
    with TestClient(app) as client:
        # Cache original app state
        orig_pipeline = getattr(client.app.state, "ingestion_pipeline", None)
        orig_search = getattr(client.app.state, "search_engine", None)
        
        # Inject mocks
        client.app.state.ingestion_pipeline = mock_pipeline
        client.app.state.search_engine = mock_search
        
        yield client
        
        # Restore original state
        client.app.state.ingestion_pipeline = orig_pipeline
        client.app.state.search_engine = orig_search


def test_health_check_endpoint(test_client):
    response = test_client.get("/api/v1/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "timestamp" in data


def test_ingestion_api_endpoint(test_client):
    response = test_client.post("/api/v1/ingest")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "success"
    assert data["total_chunks"] == 150


def test_query_api_endpoint(test_client):
    payload = {
        "query": "Is there a network gateway connection error?",
        "top_k_hybrid": 20,
        "top_k_rerank": 3
    }
    response = test_client.post("/api/v1/query", json=payload)
    assert response.status_code == 200
    data = response.json()
    
    assert data["query"] == "Is there a network gateway connection error?"
    assert "answer" in data
    assert "metrics" in data
    assert "pipeline_total_ms" in data["metrics"]
    
    assert len(data["results"]) == 1
    assert data["results"][0]["doc_id"] == "test_sha_256_hash"
    assert data["results"][0]["chunk_index"] == 2
    assert data["results"][0]["rerank_score"] == 0.985
