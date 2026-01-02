"""
Retriever Module for RAG System
Loads from: Local ChromaDB OR HuggingFace Hub
"""

import os
from dotenv import load_dotenv

load_dotenv()

# Try new imports first, fall back to old
try:
    from langchain_huggingface import HuggingFaceEmbeddings
    from langchain_chroma import Chroma
except ImportError:
    from langchain_community.vectorstores import Chroma
    from langchain_community.embeddings import HuggingFaceEmbeddings

# =============================================================================
# CONFIGURATION
# =============================================================================

LOCAL_CHROMADB_DIR = "chromadb_data"
HF_CHROMADB_ID = os.getenv("HF_CHROMADB_ID", None)
COLLECTION_NAME = "sql_knowledge"
EMBEDDING_MODEL = "all-MiniLM-L6-v2"

# =============================================================================
# CHROMADB LOADER
# =============================================================================

def ensure_chromadb_exists():
    """Ensure ChromaDB data exists - download from HF if needed."""
    
    # Check if local has actual ChromaDB files (not just empty folder)
    if os.path.exists(LOCAL_CHROMADB_DIR):
        local_files = os.listdir(LOCAL_CHROMADB_DIR) if os.path.isdir(LOCAL_CHROMADB_DIR) else []
        # ChromaDB creates files like chroma.sqlite3 or folders
        has_chroma_files = any('chroma' in f.lower() or 'sqlite' in f.lower() for f in local_files) or len(local_files) > 2
        
        if has_chroma_files:
            print(f"📁 Using local ChromaDB: {LOCAL_CHROMADB_DIR}")
            return LOCAL_CHROMADB_DIR
        else:
            print(f"⚠️ ChromaDB folder exists but is empty or incomplete")
    
    # Download from HuggingFace
    if HF_CHROMADB_ID:
        print(f"☁️ Downloading ChromaDB from HuggingFace: {HF_CHROMADB_ID}")
        from huggingface_hub import snapshot_download
        
        # Create folder if not exists
        os.makedirs(LOCAL_CHROMADB_DIR, exist_ok=True)
        
        snapshot_download(
            repo_id=HF_CHROMADB_ID,
            repo_type="dataset",
            local_dir=LOCAL_CHROMADB_DIR
        )
        print("✓ ChromaDB downloaded!")
        return LOCAL_CHROMADB_DIR
    
    # Need to build it from data
    print("⚠️ ChromaDB not found and no HF_CHROMADB_ID set. Building from data...")
    from rag.knowledge_base import build_knowledge_base
    build_knowledge_base(data_dir="data", batch_size=500)
    return LOCAL_CHROMADB_DIR

# =============================================================================
# LANGCHAIN EMBEDDINGS WITH CACHING
# =============================================================================

# Global cache for embeddings model
_embeddings_cache = None

def get_embeddings():
    """Get HuggingFace embeddings for LangChain. Uses singleton pattern for caching."""
    global _embeddings_cache
    if _embeddings_cache is None:
        _embeddings_cache = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            model_kwargs={'device': 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
    return _embeddings_cache

# =============================================================================
# RANKING FUNCTIONS
# =============================================================================

def calculate_relevance_score(result, query):
    """Calculate enhanced relevance score."""
    base_score = result.get('score', 0.5)
    boost = 0.0
    
    query_words = set(query.lower().split())
    question_words = set(result.get('question', '').lower().split())
    overlap = len(query_words & question_words)
    if overlap > 0:
        boost += 0.05 * min(overlap, 5)
    
    return min(base_score + boost, 1.0)

def filter_diverse_examples(results, min_diversity_threshold=0.4):
    """
    Filter results to ensure diversity - remove examples that are too similar to each other.
    
    Args:
        results: List of result dicts with 'question' field
        min_diversity_threshold: Minimum word overlap ratio to consider diverse (0-1)
        
    Returns:
        Filtered list with diverse examples
    """
    if not results:
        return results
    
    diverse_results = [results[0]]  # Always keep the most relevant
    
    for candidate in results[1:]:
        candidate_words = set(candidate['question'].lower().split())
        is_diverse = True
        
        # Check against all already selected examples
        for selected in diverse_results:
            selected_words = set(selected['question'].lower().split())
            
            # Calculate Jaccard similarity (intersection / union)
            if len(candidate_words | selected_words) > 0:
                similarity = len(candidate_words & selected_words) / len(candidate_words | selected_words)
                
                # If too similar, skip this candidate
                if similarity > (1 - min_diversity_threshold):
                    is_diverse = False
                    break
        
        if is_diverse:
            diverse_results.append(candidate)
    
    return diverse_results

def calculate_relevance_score_old(result, query):
    """Calculate enhanced relevance score."""
    base_score = result.get('score', 0.5)
    boost = 0.0
    
    query_words = set(query.lower().split())
    question_words = set(result.get('question', '').lower().split())
    overlap = len(query_words & question_words)
    if overlap > 0:
        boost += 0.05 * min(overlap, 5)
    
    query_length = len(query.split())
    if query_length <= 8 and result.get('complexity') == 'simple':
        boost += 0.1
    elif query_length > 15 and result.get('complexity') == 'complex':
        boost += 0.1
    
    return base_score + boost

def rerank_results(results, query):
    """Re-rank results using enhanced relevance scoring."""
    for r in results:
        r['relevance_score'] = calculate_relevance_score(r, query)
    results.sort(key=lambda x: x['relevance_score'], reverse=True)
    return results

# =============================================================================
# FILTERING FUNCTIONS
# =============================================================================

def filter_by_threshold(results, min_score=0.0):
    return [r for r in results if r.get('score', 0) >= min_score]

def filter_by_complexity(results, complexity=None):
    if complexity is None:
        return results
    return [r for r in results if r.get('complexity') == complexity]

# =============================================================================
# SQL RETRIEVER CLASS
# =============================================================================

class SQLRetriever:
    """LangChain-based retriever with local/HuggingFace support."""
    
    def __init__(self):
        """Initialize the retriever."""
        print("Initializing SQL Retriever...")
        
        # Ensure ChromaDB exists
        chromadb_path = ensure_chromadb_exists()
        self.persist_dir = chromadb_path  # Store for later use
        
        # Load embeddings
        self.embeddings = get_embeddings()
        
        # Load ChromaDB
        self.vectorstore = Chroma(
            collection_name=COLLECTION_NAME,
            persist_directory=chromadb_path,
            embedding_function=self.embeddings
        )
        
        self.doc_count = self.vectorstore._collection.count()
        print(f"✓ Loaded {self.doc_count:,} documents from {chromadb_path}")
    
    def retrieve(self, query, top_k=5, min_score=None, complexity=None, rerank=True):
        """Retrieve similar questions with filtering and ranking."""
        
        fetch_k = min(top_k * 3, 50)
        docs_with_scores = self.vectorstore.similarity_search_with_score(query, k=fetch_k)
        
        # Format results
        formatted = []
        for doc, score in docs_with_scores:
            formatted.append({
                'question': doc.page_content,
                'sql': doc.metadata.get('sql', ''),
                'source': doc.metadata.get('source', 'unknown'),
                'complexity': doc.metadata.get('complexity', 'unknown'),
                'keywords': doc.metadata.get('keywords', ''),
                'sql_clauses': doc.metadata.get('sql_clauses', ''),
                'distance': score,
                'score': 1 - score if score <= 1 else 1 / (1 + score)
            })
        
        # Apply filters
        if min_score is not None:
            formatted = filter_by_threshold(formatted, min_score)
        
        if complexity is not None:
            formatted = filter_by_complexity(formatted, complexity)
        
        # Apply re-ranking
        if rerank:
            formatted = rerank_results(formatted, query)
        
        # Apply diversity filter to ensure unique examples (less aggressive for more results)
        formatted = filter_diverse_examples(formatted, min_diversity_threshold=0.3)
        
        return formatted[:top_k]
    
    def retrieve_as_context(self, query, top_k=5):
        """Retrieve and format as context for LLM prompt."""
        results = self.retrieve(query, top_k=top_k)
        
        if not results:
            return ""
        
        context = "Similar SQL examples:\n\n"
        for i, r in enumerate(results, 1):
            context += f"Example {i}:\n"
            context += f"Question: {r['question']}\n"
            context += f"SQL: {r['sql']}\n\n"
        
        return context
    
    def add_example(self, example: dict):
        """
        Add a new example to ChromaDB (feedback loop).
        
        Args:
            example: Dict with 'question', 'sql', 'schema'
        """
        try:
            from langchain.schema import Document
        except ImportError:
            from langchain_core.documents import Document
        
        doc = Document(
            page_content=example['question'],
            metadata={
                'sql': example['sql'],
                'schema': example.get('schema', ''),
                'source': 'user_feedback',
                'complexity': self._detect_complexity(example['sql'])
            }
        )
        
        self.vectorstore.add_documents([doc])
        self.doc_count += 1
        print(f"✓ Added new example to RAG (total: {self.doc_count})")
    
    def clear_all_examples(self):
        """
        Clear all examples from ChromaDB.
        Useful when switching to a new database to avoid confusion with old examples.
        """
        try:
            # Delete the collection and recreate it
            self.vectorstore._client.delete_collection(COLLECTION_NAME)
            print(f"🗑️  Cleared all RAG examples from ChromaDB")
            
            # Reinitialize the vectorstore
            embeddings = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
            self.vectorstore = Chroma(
                collection_name=COLLECTION_NAME,
                embedding_function=embeddings,
                persist_directory=self.persist_dir
            )
            self.doc_count = 0
            print(f"✓ RAG database reinitialized")
        except Exception as e:
            print(f"⚠️  Failed to clear RAG examples: {e}")
    
    def _detect_complexity(self, sql: str) -> str:
        """Detect SQL complexity level."""
        sql_upper = sql.upper()
        if 'JOIN' in sql_upper or 'UNION' in sql_upper or 'SUBQUERY' in sql_upper:
            return 'complex'
        elif 'GROUP BY' in sql_upper or 'HAVING' in sql_upper:
            return 'aggregation'
        else:
            return 'simple'
    
    def get_stats(self):
        """Get retriever statistics."""
        return {
            'total_documents': self.doc_count,
            'collection_name': COLLECTION_NAME,
            'embedding_model': EMBEDDING_MODEL,
        }

# =============================================================================
# Production retriever - no test code in main module