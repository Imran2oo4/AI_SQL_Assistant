"""
RAG Service - Retrieves similar NL->SQL examples for few-shot learning
"""

from typing import List, Dict, Optional

# Try to import RAG infrastructure, but make it optional
try:
    from rag.retriever import SQLRetriever
    RAG_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  RAG imports not available: {e}")
    RAG_AVAILABLE = False
    SQLRetriever = None


class RAGService:
    """
    Service wrapper for RAG retrieval of SQL examples.
    """
    
    def __init__(self, top_k: int = 3):
        """
        Initialize RAG service.
        
        Args:
            top_k: Default number of examples to retrieve
        """
        self.top_k = top_k
        self.retriever = None
        self._initialize_retriever()
    
    def _initialize_retriever(self):
        """Initialize the SQL retriever."""
        if not RAG_AVAILABLE:
            print("⚠️  RAG dependencies not installed. Install with: pip install langchain langchain-community langchain-chroma langchain-huggingface")
            print("   Will operate without RAG examples")
            return
            
        try:
            self.retriever = SQLRetriever()
            print("✓ RAG Service initialized")
        except Exception as e:
            print(f"⚠️  RAG Service initialization failed: {e}")
            print("   Will operate without RAG examples")
    
    def clear_all_examples(self):
        """Clear all RAG examples from database."""
        if not self.retriever:
            return False
        try:
            self.retriever.clear_all_examples()
            return True
        except Exception as e:
            print(f"⚠️  Failed to clear RAG examples: {e}")
            return False
    
    def save_successful_query(
        self,
        question: str,
        sql: str,
        schema: str
    ) -> bool:
        """
        Save successful query to RAG for future learning (feedback loop).
        Includes deduplication to avoid storing near-duplicate examples.
        
        Args:
            question: User's natural language question
            sql: Successfully executed SQL query
            schema: Database schema context
        
        Returns:
            True if saved successfully
        """
        if not self.retriever:
            return False
        
        try:
            # Check for near-duplicates before saving
            existing_examples = self.retriever.retrieve(query=question, top_k=3)
            
            # Deduplication logic: skip if very similar example exists
            for example in existing_examples:
                existing_question = example.get('question', '').lower().strip()
                existing_sql = example.get('sql', '').lower().strip()
                new_question = question.lower().strip()
                new_sql = sql.lower().strip()
                
                # Skip if exact duplicate
                if existing_question == new_question and existing_sql == new_sql:
                    print(f"⊗ Skipping duplicate: '{question}'")
                    return False
                
                # Skip if questions are very similar (>90% token overlap) and SQL is same
                question_tokens = set(new_question.split())
                existing_tokens = set(existing_question.split())
                if len(question_tokens) > 0:
                    overlap = len(question_tokens & existing_tokens) / len(question_tokens)
                    if overlap > 0.9 and existing_sql == new_sql:
                        print(f"⊗ Skipping near-duplicate: '{question}'")
                        return False
            
            # Add new example if not duplicate
            self.retriever.add_example({
                'question': question,
                'sql': sql,
                'schema': schema
            })
            print(f"✓ Saved to RAG: '{question}' → {sql[:50]}...")
            return True
            
        except Exception as e:
            print(f"⚠️  Failed to save query to RAG: {e}")
            return False
    
    def generate_initial_examples(self, schema: Dict[str, List[str]], detailed_schema: str) -> int:
        """
        Auto-generate initial RAG examples based on database schema.
        This provides immediate few-shot learning for new databases.
        
        Args:
            schema: Database schema (table_name -> columns)
            detailed_schema: Detailed schema information
        
        Returns:
            Number of examples generated
        """
        if not self.retriever or not schema:
            return 0
        
        generated_count = 0
        
        for table_name, columns in schema.items():
            # Generate natural table/column names (remove underscores, make singular)
            natural_table = table_name.replace('_', ' ')
            singular_table = natural_table.rstrip('s') if natural_table.endswith('s') else natural_table
            
            # Example 1: Show all records
            examples = [
                {
                    'question': f"Show all {natural_table}",
                    'sql': f"SELECT * FROM {table_name}",
                },
                {
                    'question': f"Count total {natural_table}",
                    'sql': f"SELECT COUNT(*) as total FROM {table_name}",
                },
            ]
            
            # Example 3: Add examples based on column types
            for col in columns:
                col_lower = col.lower()
                natural_col = col.replace('_', ' ')
                
                # For date/year columns - recent records
                if any(term in col_lower for term in ['date', 'year', 'time', 'created', 'joined']):
                    examples.append({
                        'question': f"Show {natural_table} from last year",
                        'sql': f"SELECT * FROM {table_name} WHERE {col} >= date('now', '-1 year')",
                    })
                    break
                
                # For name/title columns - alphabetical
                elif any(term in col_lower for term in ['name', 'title']):
                    examples.append({
                        'question': f"Show {natural_table} ordered by {natural_col}",
                        'sql': f"SELECT * FROM {table_name} ORDER BY {col}",
                    })
                    break
                
                # For status/category columns - grouping
                elif any(term in col_lower for term in ['status', 'category', 'type', 'department', 'location', 'gender']):
                    examples.append({
                        'question': f"Count {natural_table} by {natural_col}",
                        'sql': f"SELECT {col}, COUNT(*) as count FROM {table_name} GROUP BY {col}",
                    })
                    break
                
                # For numeric columns - statistics
                elif any(term in col_lower for term in ['price', 'amount', 'salary', 'cost', 'total', 'age']):
                    examples.append({
                        'question': f"Show average {natural_col} of {natural_table}",
                        'sql': f"SELECT AVG({col}) as average_{col} FROM {table_name}",
                    })
                    examples.append({
                        'question': f"Show {natural_table} with highest {natural_col}",
                        'sql': f"SELECT * FROM {table_name} ORDER BY {col} DESC LIMIT 10",
                    })
                    break
            
            # Save generated examples to RAG
            for example in examples[:5]:  # Limit to 5 per table to avoid clutter
                try:
                    self.retriever.add_example({
                        'question': example['question'],
                        'sql': example['sql'],
                        'schema': detailed_schema
                    })
                    generated_count += 1
                except Exception as e:
                    print(f"⚠️  Failed to save auto-generated example: {e}")
        
        print(f"✨ Auto-generated {generated_count} RAG examples for new database")
        return generated_count
    
    def get_similar_examples(
        self,
        question: str,
        top_k: Optional[int] = None,
        schema: Optional[Dict[str, List[str]]] = None
    ) -> List[Dict[str, str]]:
        """
        Retrieve similar question-SQL pairs for few-shot learning.
        Now schema-aware: enhances query with current table names for better context matching.
        
        Args:
            question: Natural language question
            top_k: Number of examples to retrieve (uses default if None)
            schema: Current database schema (table_name -> columns)
        
        Returns:
            List of dicts with 'question' and 'sql' keys
        """
        if not self.retriever:
            return []
        
        k = top_k if top_k is not None else self.top_k
        
        try:
            # Enhance query with schema context for better matching
            enhanced_query = question
            if schema:
                table_names = list(schema.keys())
                if table_names:
                    # Add table context to help match relevant examples
                    table_context = " ".join(table_names)
                    enhanced_query = f"{question} {table_context}"
            
            results = self.retriever.retrieve(
                query=enhanced_query,
                top_k=k * 2  # Retrieve more, then filter
            )
            
            # Filter results based on schema relevance if schema provided
            if schema:
                table_names_lower = [t.lower() for t in schema.keys()]
                
                # STRICT FILTERING: Only keep results that mention current tables
                relevant_results = []
                
                for result in results:
                    sql = result.get('sql', '').lower()
                    result_question = result.get('question', '').lower()
                    
                    # Check if the example mentions ANY of our current tables
                    relevance_score = 0
                    for table in table_names_lower:
                        if table in sql or table in result_question:
                            relevance_score += 1
                    
                    # ONLY include if it mentions at least one current table
                    if relevance_score > 0:
                        relevant_results.append((relevance_score, result))
                
                # Sort by relevance (highest first) and take top k
                relevant_results.sort(key=lambda x: x[0], reverse=True)
                results = [r[1] for r in relevant_results[:k]]
                
                # If no relevant results, return empty list
                if not results:
                    return []
            else:
                results = results[:k]
            
            # Format results for prompt injection
            examples = []
            for result in results:
                examples.append({
                    'question': result.get('question', ''),
                    'sql': result.get('sql', ''),
                    'score': result.get('score', 0.0)
                })
            
            return examples
            
        except Exception as e:
            print(f"⚠️  RAG retrieval error: {e}")
            return []
    
    def is_available(self) -> bool:
        """Check if RAG service is operational."""
        return self.retriever is not None


def create_rag_service(top_k: int = 3) -> RAGService:
    """Factory function to create RAG service."""
    return RAGService(top_k=top_k)
