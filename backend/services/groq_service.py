"""
Groq Service for SQL Generation
Wrapper around GroqClient for backend integration
"""

from typing import Optional, List, Dict, Tuple
from pipeline.models.groq_client import GroqClient, create_groq_client


class GroqService:
    """
    Service layer for Groq-based SQL generation.
    """
    
    def __init__(self, client: GroqClient):
        """
        Initialize Groq service.
        
        Args:
            client: GroqClient instance
        """
        self.client = client
    
    def generate_sql_direct(
        self,
        question: str,
        schema: str,
        examples: List[Dict] = None
    ) -> str:
        """
        Generate SQL query directly from question.
        
        Args:
            question: Natural language question
            schema: Database schema
            examples: Optional similar examples from RAG
        
        Returns:
            Generated SQL query
        """
        if not self.is_available():
            raise Exception("Groq service not available")
        
        sql = self.client.generate_sql_direct(
            question=question,
            schema=schema,
            examples=examples
        )
        
        return sql
    
    def generate_explanation(
        self,
        sql: str,
        schema: str,
        question: str
    ) -> Tuple[str, str]:
        """
        Generate explanation for SQL query.
        
        Args:
            sql: SQL query
            schema: Database schema
            question: Original question
        
        Returns:
            Tuple of (explanation, model_used)
        """
        if not self.is_available():
            return "SQL query executed successfully.", "none"
        
        explanation = self.client.explain_sql(
            sql=sql,
            schema=schema,
            question=question
        )
        
        return explanation, "groq"
    
    def correct_sql_error(
        self,
        original_sql: str,
        error_message: str,
        schema: str,
        question: str
    ) -> Optional[str]:
        """
        Attempt to correct SQL query based on execution error.
        
        Args:
            original_sql: The SQL that failed
            error_message: Error message from database
            schema: Database schema
            question: Original user question
        
        Returns:
            Corrected SQL or None if correction fails
        """
        if not self.is_available():
            return None
        
        return self.client.correct_sql_error(
            original_sql=original_sql,
            error_message=error_message,
            schema=schema,
            question=question
        )
    
    def refine_sql(
        self,
        sql: str,
        question: str,
        schema: str
    ) -> Optional[str]:
        """
        Refine and optimize SQL query.
        
        Args:
            sql: Original SQL query
            question: Original user question
            schema: Database schema
        
        Returns:
            Refined SQL query
        """
        if not self.is_available():
            return sql
        
        return self.client.refine_sql(
            sql=sql,
            question=question,
            schema=schema
        )
    
    def is_available(self) -> bool:
        """
        Check if Groq service is available.
        
        Returns:
            True if client is available
        """
        return self.client is not None and self.client.is_available()


def create_groq_service(api_key: Optional[str] = None) -> GroqService:
    """
    Factory function to create Groq service.
    
    Args:
        api_key: Optional Groq API key
    
    Returns:
        GroqService instance
    """
    try:
        client = create_groq_client(api_key=api_key)
        return GroqService(client)
    except Exception as e:
        print(f"Failed to create Groq service: {e}")
        raise
