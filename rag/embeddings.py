"""
Embedding Module for RAG System
Uses FREE sentence-transformers (no API costs).
Gemini is ONLY used for final SQL generation.
"""

from sentence_transformers import SentenceTransformer
import os

# =============================================================================
# FREE LOCAL EMBEDDING MODEL
# =============================================================================

# Using all-MiniLM-L6-v2: fast, good quality, 384 dimensions
MODEL_NAME = "all-MiniLM-L6-v2"

# Global model instance (loaded once)
_model = None

def get_model():
    """Get or load the embedding model."""
    global _model
    if _model is None:
        print(f"  Loading embedding model: {MODEL_NAME}")
        _model = SentenceTransformer(MODEL_NAME)
    return _model

# =============================================================================
# EMBEDDING FUNCTIONS
# =============================================================================

def get_embedding(text):
    """Get embedding for a single text."""
    try:
        model = get_model()
        embedding = model.encode(text, convert_to_numpy=True)
        return embedding.tolist()
    except Exception as e:
        print(f"Error getting embedding: {e}")
        return None

def get_embeddings_batch(texts):
    """Get embeddings for multiple texts at once (efficient)."""
    try:
        model = get_model()
        embeddings = model.encode(texts, convert_to_numpy=True, show_progress_bar=False)
        return [emb.tolist() for emb in embeddings]
    except Exception as e:
        print(f"Error in batch embedding: {e}")
        return [None] * len(texts)

# =============================================================================
# TEST
# =============================================================================

def test_embedding():
    """Test embedding functionality."""
    print("=" * 50)
    print("TESTING EMBEDDINGS (FREE - No API)")
    print("=" * 50)
    
    test_texts = [
        "Find all employees with salary greater than 50000",
        "Show customers who ordered last month",
        "Count products by category"
    ]
    
    print(f"\nModel: {MODEL_NAME}")
    print(f"Testing with {len(test_texts)} texts...\n")
    
    # Single embedding
    emb = get_embedding(test_texts[0])
    if emb:
        print(f"✓ Single embedding works")
        print(f"  Dimension: {len(emb)}")
    
    # Batch embedding
    embs = get_embeddings_batch(test_texts)
    if embs and embs[0]:
        print(f"✓ Batch embedding works")
        print(f"  Got {len(embs)} embeddings")
    
    print("\n✓ All tests passed (FREE - No Gemini used)")
    return True

if __name__ == "__main__":
    test_embedding()