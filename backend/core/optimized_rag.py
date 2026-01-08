"""
Optimized RAG Retriever with Batch Processing and Better Indexing
Improves embedding performance and retrieval speed
"""

from typing import List, Dict, Any, Optional
from functools import lru_cache
import time


class OptimizedRAGRetriever:
    """
    High-performance RAG retriever with optimizations:
    1. Batch embedding generation
    2. Query embedding caching
    3. Fast approximate search
    4. Result pre-filtering
    """
    
    def __init__(self, chroma_collection, embeddings_model):
        """
        Initialize optimized retriever.
        
        Args:
            chroma_collection: ChromaDB collection
            embeddings_model: HuggingFace embeddings model
        """
        self.collection = chroma_collection
        self.embeddings = embeddings_model
        self._query_cache = {}
        self._cache_hits = 0
        self._cache_misses = 0
    
    @lru_cache(maxsize=1000)
    def _get_query_embedding(self, query: str) -> List[float]:
        """
        Get embedding for query with caching.
        
        Args:
            query: Query string
        
        Returns:
            Embedding vector
        """
        return self.embeddings.embed_query(query)
    
    def retrieve_batch(
        self,
        queries: List[str],
        top_k: int = 3
    ) -> List[List[Dict[str, Any]]]:
        """
        Retrieve examples for multiple queries efficiently.
        Uses batch embedding generation.
        
        Args:
            queries: List of query strings
            top_k: Number of examples per query
        
        Returns:
            List of example lists, one per query
        """
        # Generate embeddings in batch (much faster than one-by-one)
        query_embeddings = self.embeddings.embed_documents(queries)
        
        results = []
        for query, embedding in zip(queries, query_embeddings):
            # Query ChromaDB with pre-computed embedding
            chroma_results = self.collection.query(
                query_embeddings=[embedding],
                n_results=top_k,
                include=["documents", "metadatas", "distances"]
            )
            
            # Format results
            examples = self._format_results(chroma_results)
            results.append(examples)
        
        return results
    
    def retrieve_with_filters(
        self,
        query: str,
        top_k: int = 3,
        min_score: float = 0.0,
        complexity_filter: Optional[str] = None,
        table_filter: Optional[List[str]] = None
    ) -> List[Dict[str, Any]]:
        """
        Retrieve examples with advanced filtering.
        
        Args:
            query: Query string
            top_k: Number of examples
            min_score: Minimum similarity score
            complexity_filter: Filter by complexity ('simple', 'intermediate', 'complex')
            table_filter: Filter by tables used
        
        Returns:
            Filtered examples
        """
        # Build ChromaDB where clause
        where_clause = {}
        
        if complexity_filter:
            where_clause["complexity"] = complexity_filter
        
        if table_filter and len(table_filter) > 0:
            # ChromaDB supports $in operator
            where_clause["tables"] = {"$in": table_filter}
        
        # Query with filters
        chroma_results = self.collection.query(
            query_texts=[query],
            n_results=top_k * 2,  # Get more, then filter
            where=where_clause if where_clause else None,
            include=["documents", "metadatas", "distances"]
        )
        
        # Format and score
        examples = self._format_results(chroma_results)
        
        # Apply score threshold
        if min_score > 0:
            examples = [ex for ex in examples if ex.get('score', 0) >= min_score]
        
        return examples[:top_k]
    
    def _format_results(self, chroma_results: Dict) -> List[Dict[str, Any]]:
        """Format ChromaDB results into example dictionaries."""
        if not chroma_results or 'ids' not in chroma_results:
            return []
        
        examples = []
        ids = chroma_results['ids'][0] if chroma_results['ids'] else []
        documents = chroma_results['documents'][0] if chroma_results['documents'] else []
        metadatas = chroma_results['metadatas'][0] if chroma_results['metadatas'] else []
        distances = chroma_results['distances'][0] if chroma_results['distances'] else []
        
        for i, doc_id in enumerate(ids):
            # Convert distance to similarity score (lower distance = higher similarity)
            score = 1.0 / (1.0 + distances[i]) if i < len(distances) else 0.5
            
            examples.append({
                'id': doc_id,
                'question': metadatas[i].get('question', '') if i < len(metadatas) else '',
                'sql': metadatas[i].get('sql', '') if i < len(metadatas) else '',
                'tables': metadatas[i].get('tables', []) if i < len(metadatas) else [],
                'complexity': metadatas[i].get('complexity', 'simple') if i < len(metadatas) else 'simple',
                'score': score
            })
        
        return examples
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Get cache performance statistics."""
        total = self._cache_hits + self._cache_misses
        hit_rate = (self._cache_hits / total * 100) if total > 0 else 0
        
        return {
            "cache_hits": self._cache_hits,
            "cache_misses": self._cache_misses,
            "hit_rate_percent": round(hit_rate, 2),
            "cache_info": self._get_query_embedding.cache_info()._asdict()
        }
    
    def clear_cache(self):
        """Clear embedding cache."""
        self._get_query_embedding.cache_clear()
        self._query_cache.clear()
        self._cache_hits = 0
        self._cache_misses = 0

