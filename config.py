"""
Central Configuration for SQL Learning Assistant
Handles local vs HuggingFace paths automatically
"""

import os
from dotenv import load_dotenv

load_dotenv()

# =============================================================================
# HUGGINGFACE CONFIGURATION (for cloud deployment)
# Set these in .env or Streamlit secrets
# =============================================================================

HF_MODEL_ID = os.getenv("HF_MODEL_ID", None)  # e.g., "username/sql-tinyllama-lora"
HF_CHROMADB_ID = os.getenv("HF_CHROMADB_ID", None)  # e.g., "username/sql-chromadb"
HF_TOKEN = os.getenv("HF_TOKEN", None)

# =============================================================================
# LOCAL PATHS
# =============================================================================

LOCAL_MODEL_DIR = "outputs/finetuning/checkpoints/final"
LOCAL_CHROMADB_DIR = "chromadb_data"
LOCAL_DATA_DIR = "data"

# =============================================================================
# GEMINI CONFIGURATION
# =============================================================================

GEMINI_KEYS = [
    os.getenv("GEMINI_API_KEY"),
    os.getenv("GEMINI_API_KEY_FALLBACK_1"),
    os.getenv("GEMINI_API_KEY_FALLBACK_2"),
]
GEMINI_KEYS = [k for k in GEMINI_KEYS if k]  # Remove None values

GEMINI_MODELS = [
    os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
    os.getenv("GEMINI_MODEL_FALLBACK_1"),
]
GEMINI_MODELS = [m for m in GEMINI_MODELS if m]  # Remove None values

# =============================================================================
# RAG CONFIGURATION
# =============================================================================

EMBEDDING_MODEL = "all-MiniLM-L6-v2"
COLLECTION_NAME = "sql_knowledge"

# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def is_local():
    """Check if running locally (has local model/data)."""
    return os.path.exists(LOCAL_MODEL_DIR) and os.path.exists(LOCAL_CHROMADB_DIR)

def is_cloud():
    """Check if running in cloud (has HF config)."""
    return HF_MODEL_ID is not None or HF_CHROMADB_ID is not None

def get_model_source():
    """Get where model will be loaded from."""
    if os.path.exists(LOCAL_MODEL_DIR) and os.listdir(LOCAL_MODEL_DIR):
        return "local", LOCAL_MODEL_DIR
    elif HF_MODEL_ID:
        return "huggingface", HF_MODEL_ID
    else:
        return "base", "TinyLlama/TinyLlama-1.1B-Chat-v1.0"

def get_chromadb_source():
    """Get where ChromaDB will be loaded from."""
    if os.path.exists(LOCAL_CHROMADB_DIR) and os.listdir(LOCAL_CHROMADB_DIR):
        return "local", LOCAL_CHROMADB_DIR
    elif HF_CHROMADB_ID:
        return "huggingface", HF_CHROMADB_ID
    else:
        return "build", LOCAL_DATA_DIR

def print_config():
    """Print current configuration."""
    print("=" * 50)
    print("CONFIGURATION")
    print("=" * 50)
    
    model_src, model_path = get_model_source()
    chromadb_src, chromadb_path = get_chromadb_source()
    
    print(f"Model: {model_src} → {model_path}")
    print(f"ChromaDB: {chromadb_src} → {chromadb_path}")
    print(f"Gemini Keys: {len(GEMINI_KEYS)} available")
    print(f"Gemini Models: {GEMINI_MODELS}")
    print("=" * 50)

if __name__ == "__main__":
    print_config()