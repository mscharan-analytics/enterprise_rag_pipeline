import pytest
from src.utils.chunker import RecursiveCharacterChunker

def test_chunker_basic_splitting():
    text = "Paragraph one is here.\n\nParagraph two is there. It is slightly longer."
    chunker = RecursiveCharacterChunker(chunk_size=30, chunk_overlap=5)
    chunks = chunker.chunk_text(text)
    
    assert len(chunks) >= 2
    # Ensure chunks are non-empty strings
    for c in chunks:
        assert isinstance(c, str)
        assert len(c) > 0
        assert len(c) <= 30 + 5  # chunk size + overlap allowance

def test_chunker_respects_overlap():
    text = "Word1 Word2 Word3 Word4 Word5"
    chunker = RecursiveCharacterChunker(chunk_size=15, chunk_overlap=5)
    chunks = chunker.chunk_text(text)
    
    assert len(chunks) > 1
    # Check that overlap prefix exists in subsequent chunks
    assert "Word2" in chunks[0]
    # Subsequent chunk should contain end slice of previous chunk
    # e.g., overlaps by 5 chars
    assert len(chunks[1]) > 0

def test_chunker_empty_input():
    chunker = RecursiveCharacterChunker(chunk_size=100, chunk_overlap=10)
    assert chunker.chunk_text("") == []
    assert chunker.chunk_text("   ") == []

def test_chunker_extremely_long_words():
    # Test how chunker behaves when a word is larger than the chunk size
    long_word = "A" * 100
    chunker = RecursiveCharacterChunker(chunk_size=20, chunk_overlap=2)
    chunks = chunker.chunk_text(long_word)
    
    # It should split character-by-character
    assert len(chunks) > 1
    for c in chunks:
        assert len(c) <= 20 + 2 + 1  # chunk_size + chunk_overlap + space allowance
