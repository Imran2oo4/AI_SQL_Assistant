"""
Groq Client for SQL Generation and Explanation
Provides fast inference with generous rate limits (30 RPM, 14,400 requests/day)
"""

import os
import time
from typing import Optional, List, Dict
from dotenv import load_dotenv
from groq import Groq

load_dotenv()

# =============================================================================
# CONFIGURATION
# =============================================================================

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY")

# Models (Updated December 2025 - llama-3.1-70b-versatile was decommissioned)
GROQ_MODELS = [
    os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile"),  # Latest Llama 3.3 70B (Best for SQL)
    "llama-3.1-8b-instant",  # Faster fallback
    "mixtral-8x7b-32768",  # Alternative
]

# Rate limiting (Groq free tier is very generous)
RATE_LIMIT_DELAY = 2.0  # 30 RPM = 2 seconds minimum
MAX_RETRIES = 2

# Global rate limit tracker
_global_last_request_time = 0
_rate_limit_lock = None


# =============================================================================
# GROQ CLIENT
# =============================================================================

class GroqClient:
    """
    Groq client for SQL generation with fast inference.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: Optional[str] = None
    ):
        """
        Initialize Groq client.
        
        Args:
            api_key: Groq API key
            model: Model name (default: llama-3.1-70b-versatile)
        """
        self.api_key = api_key or GROQ_API_KEY
        self.model = model or GROQ_MODELS[0]
        
        if not self.api_key:
            raise ValueError("No Groq API key provided. Set GROQ_API_KEY in .env or provide via UI.")
        
        # Initialize Groq client
        self.client = Groq(api_key=self.api_key)
        
        # Use global rate limit tracker
        global _rate_limit_lock
        if _rate_limit_lock is None:
            import threading
            _rate_limit_lock = threading.Lock()
        
        print(f"\n{'='*60}")
        print("Initializing Groq Client")
        print(f"{'='*60}")
        print(f"Model: {self.model}")
        print(f"Rate Limit: 30 requests/min (14,400/day)")
        print("✓ Groq initialized successfully")
        print(f"{'='*60}\n")
    
    def _rate_limit(self):
        """Apply rate limiting using global timestamp."""
        global _global_last_request_time, _rate_limit_lock
        
        with _rate_limit_lock:
            current_time = time.time()
            elapsed = current_time - _global_last_request_time
            
            if elapsed < RATE_LIMIT_DELAY:
                wait_time = RATE_LIMIT_DELAY - elapsed
                time.sleep(wait_time)
                _global_last_request_time = time.time()
            else:
                _global_last_request_time = current_time
    
    def generate(
        self,
        prompt: str,
        temperature: float = 0.1,
        max_tokens: int = 512,
        max_retries: int = MAX_RETRIES
    ) -> Optional[str]:
        """
        Generate text using Groq.
        
        Args:
            prompt: Input prompt
            temperature: Sampling temperature
            max_tokens: Maximum output tokens
            max_retries: Maximum retry attempts
        
        Returns:
            Generated text or None if failed
        """
        self._rate_limit()
        
        for attempt in range(max_retries):
            try:
                response = self.client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {"role": "system", "content": "You are an expert SQL query generator."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=temperature,
                    max_tokens=max_tokens
                )
                
                return response.choices[0].message.content
                
            except Exception as e:
                error_msg = str(e).lower()
                
                # Handle rate limit errors
                if "rate" in error_msg or "429" in error_msg or "quota" in error_msg:
                    if attempt < max_retries - 1:
                        wait_time = [5, 15][min(attempt, 1)]
                        print(f"⚠️ Rate limit hit (attempt {attempt + 1}/{max_retries}) - waiting {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                    else:
                        raise Exception("Groq API rate limit exceeded. Please wait a minute and try again.")
                
                # Handle other errors
                else:
                    print(f"⚠️ Groq error: {e}")
                    if attempt < max_retries - 1:
                        time.sleep(2)
                        continue
                
                return None
        
        print("❌ All Groq attempts failed")
        return None
    
    def _format_schema(self, schema_input) -> str:
        """
        Format schema for better readability in prompts.
        
        Args:
            schema_input: Either a dict (detailed_schema) or string
        
        Returns:
            Formatted schema string
        """
        if isinstance(schema_input, dict):
            # Format detailed schema nicely
            lines = []
            if 'tables' in schema_input:
                for table_name, columns in schema_input['tables'].items():
                    lines.append(f"\nTable: {table_name}")
                    for col in columns:
                        lines.append(f"  - {col}")
            
            if schema_input.get('fks'):
                lines.append("\nForeign Keys:")
                for fk in schema_input['fks']:
                    lines.append(f"  - {fk['from']} → {fk['to']}")
            
            return '\n'.join(lines)
        else:
            # Already a string
            return str(schema_input)
    
    def generate_sql_direct(
        self,
        question: str,
        schema: str,
        examples: List[Dict] = None
    ) -> Optional[str]:
        """
        Generate SQL directly from question using Groq.
        
        Args:
            question: User's natural language question
            schema: Database schema with column types and sample values (string or dict)
            examples: Optional list of similar examples from RAG
        
        Returns:
            Generated SQL query
        """
        # Format schema if it's a dictionary
        formatted_schema = self._format_schema(schema)
        
        examples_text = ""
        if examples and len(examples) > 0:
            examples_text = "\n\nSIMILAR EXAMPLES:\n"
            for i, ex in enumerate(examples[:3], 1):
                examples_text += f"\nExample {i}:\n"
                examples_text += f"Question: {ex.get('question', '')}\n"
                examples_text += f"SQL: {ex.get('sql', '')}\n"
        
        prompt = f"""You are an expert SQL query generator. Convert the natural language question to a SQL query.

DATABASE SCHEMA:
{formatted_schema}
{examples_text}

USER QUESTION:
{question}

CRITICAL RULES:
1. Output ONLY the SQL query - no explanations, no markdown, no extra text
2. For exact values, use = operator (NOT BETWEEN unless explicitly asked for range)
3. Match column values EXACTLY as shown in schema (respect capitalization)
   - If schema shows "gender:TEXT ∈ ['Male', 'Female']", use 'Male' or 'Female', NOT 'male' or 'female'
   - NEVER lowercase or change categorical values from their schema definition
4. Use only tables and columns that exist in the schema
5. Generate syntactically correct SQL

SQL:"""
        
        generated = self.generate(prompt, temperature=0.1, max_tokens=512)
        
        if generated:
            return self._clean_sql(generated)
        
        return None
    
    def _clean_sql(self, sql_text: str) -> str:
        """Clean and extract SQL from generated text."""
        sql = sql_text.strip()
        
        # Remove markdown code blocks
        if sql.startswith("```sql"):
            sql = sql[6:]
        if sql.startswith("```"):
            sql = sql[3:]
        if sql.endswith("```"):
            sql = sql[:-3]
        sql = sql.strip()
        
        # Remove any text after certain markers
        if '[' in sql:
            sql = sql[:sql.index('[')].strip()
        
        # Remove trailing semicolon for consistency
        sql = sql.rstrip(';').strip()
        
        return sql
    
    def explain_sql(
        self,
        sql: str,
        schema: str,
        question: str
    ) -> str:
        """
        Generate explanation for SQL query.
        
        Args:
            sql: SQL query
            schema: Database schema
            question: Original question
        
        Returns:
            Human-readable explanation
        """
        prompt = f"""You are a SQL expert. Explain the following SQL query in simple terms.

DATABASE SCHEMA:
{schema}

USER QUESTION:
{question}

SQL QUERY:
{sql}

TASK:
Explain this query in clear, detailed paragraphs (3-4 lines). Break down:
1. What data is being retrieved
2. Which tables and columns are involved
3. What filters or conditions are applied
4. What the final result represents

Make it understandable for non-technical users with sufficient detail.

EXPLANATION:"""
        
        explanation = self.generate(prompt, temperature=0.3, max_tokens=400)
        
        if explanation:
            return explanation.strip()
        
        return "SQL query executed successfully."
    
    def correct_sql_error(
        self,
        original_sql: str,
        error_message: str,
        schema: str,
        question: str
    ) -> Optional[str]:
        """
        Correct SQL query based on execution error.
        
        Args:
            original_sql: The SQL query that failed
            error_message: Error message from database execution
            schema: Database schema
            question: Original user question
        
        Returns:
            Corrected SQL query or None if correction fails
        """
        prompt = f"""You are an SQL expert debugger. Fix this SQL query that produced an error.

DATABASE SCHEMA:
{schema}

USER QUESTION:
{question}

FAILED SQL:
{original_sql}

ERROR MESSAGE:
{error_message}

TASK:
Analyze the error and provide a corrected SQL query. Common issues to check:
- Column names (case-sensitive, check spelling)
- Table names (verify they exist in schema)
- Data types (ensure correct type comparisons)
- Syntax errors (missing commas, parentheses, etc.)
- JOIN conditions (proper foreign key relationships)

CRITICAL: Return ONLY the corrected SQL query, no explanations.

CORRECTED SQL:"""
        
        corrected = self.generate(prompt, temperature=0.1, max_tokens=512)
        
        if corrected:
            return self._clean_sql(corrected)
        
        return None
    
    def refine_sql(
        self,
        sql: str,
        question: str,
        schema: str
    ) -> Optional[str]:
        """
        Refine and validate SQL query for correctness and optimization.
        
        Args:
            sql: Original SQL query (from TinyLlama or other model)
            question: Original user question
            schema: Database schema
        
        Returns:
            Refined SQL query
        """
        prompt = f"""You are an SQL expert reviewer. Review and refine this SQL query if needed.

DATABASE SCHEMA:
{schema}

ORIGINAL QUESTION:
{question}

GENERATED SQL:
{sql}

TASK:
1. Check if the SQL correctly answers the question
2. Verify syntax is correct
3. Optimize if possible (better joins, clearer logic, proper indexing)
4. Ensure it uses only tables/columns from the schema
5. Check for potential performance issues

RULES:
- If the SQL is already correct and optimal, return it unchanged
- If improvements are needed, return the refined version
- Return ONLY the SQL query, no explanations or markdown

REFINED SQL:"""
        
        refined = self.generate(prompt, temperature=0.1, max_tokens=512)
        
        if refined:
            return self._clean_sql(refined)
        
        return sql
    
    def is_available(self) -> bool:
        """
        Check if Groq client is available and configured.
        
        Returns:
            True if API key is available
        """
        return self.api_key is not None and self.api_key != ""


# =============================================================================
# FACTORY FUNCTION
# =============================================================================

def create_groq_client(
    api_key: Optional[str] = None,
    model: Optional[str] = None
) -> GroqClient:
    """
    Factory function to create Groq client.
    
    Args:
        api_key: Groq API key
        model: Model name
    
    Returns:
        GroqClient instance
    """
    return GroqClient(api_key=api_key, model=model)
