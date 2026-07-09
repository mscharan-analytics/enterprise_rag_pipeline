import pytest
from src.utils.sparse_encoder import SparseEncoder

def test_sparse_encoder_basic():
    encoder = SparseEncoder()
    text = "Database connection timeouts were observed."
    vector = encoder.encode(text)
    
    assert "indices" in vector
    assert "values" in vector
    assert len(vector["indices"]) == len(vector["values"])
    
    # Check that indices are sorted in ascending order (required by Qdrant)
    indices = vector["indices"]
    assert indices == sorted(indices)

def test_sparse_encoder_stopwords():
    encoder = SparseEncoder()
    text = "the a about connection of and in"
    vector = encoder.encode(text)
    
    # Stopwords should be filtered out, leaving only 'connection'
    assert len(vector["indices"]) == 1

def test_sparse_encoder_deterministic():
    encoder = SparseEncoder()
    text = "stable hashing is required for distributed databases"
    
    vector1 = encoder.encode(text)
    vector2 = encoder.encode(text)
    
    # Assert deterministic hashes across independent calculations
    assert vector1["indices"] == vector2["indices"]
    assert vector1["values"] == vector2["values"]

def test_sparse_encoder_stable_hash():
    encoder = SparseEncoder()
    token = "prototype"
    h1 = encoder._stable_hash(token)
    h2 = encoder._stable_hash(token)
    
    assert h1 == h2
    assert isinstance(h1, int)
    assert 0 <= h1 <= 0xffffffff  # Must fit in unsigned 32-bit integer (uint32)
