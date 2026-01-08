"""
TinyLlama Service - SQL Generation using fine-tuned model
"""

# Try to import TinyLlama, but make it optional for quick testing
try:
    from pipeline.models.sql_generator import SQLGenerator
    TINYLLAMA_AVAILABLE = True
except ImportError as e:
    print(f"⚠️  TinyLlama imports not available: {e}")
    TINYLLAMA_AVAILABLE = False
    SQLGenerator = None


class TinyLlamaService:
    """
    Service wrapper for TinyLlama SQL generation.
    """
    
    def __init__(self):
        """Initialize TinyLlama service."""
        self.generator = None
        self._initialize_generator()
    
    def _initialize_generator(self):
        """Initialize the SQL generator."""
        if not TINYLLAMA_AVAILABLE:
            print("⚠️  TinyLlama dependencies not installed. Using fallback mode.")
            print("   Install transformers, torch, peft for full functionality")
            return
            
        try:
            self.generator = SQLGenerator()
            print("✓ TinyLlama Service initialized")
        except Exception as e:
            print(f"⚠️  TinyLlama Service initialization failed: {e}")
            print("   Using fallback mode - will extract SQL from prompts")
    
    def generate_sql(
        self,
        prompt: str,
        max_tokens: int = 256
    ) -> str:
        """
        Generate SQL from a prompt.
        
        Args:
            prompt: Complete prompt with schema + examples + question
            max_tokens: Maximum tokens to generate
        
        Returns:
            Generated SQL query (or CLARIFY response)
        """
        if not self.generator:
            # Fallback: return a message asking user to provide SQL
            return "CLARIFY: TinyLlama model not loaded. Please install dependencies or provide SQL directly."
        
        try:
            # Generate SQL using the sql_generator module
            result = self.generator.generate_sql(
                prompt=prompt,
                max_length=max_tokens
            )
            
            # Clean up the result
            sql = self._extract_sql(result)
            return sql
            
        except Exception as e:
            print(f"⚠️  TinyLlama generation error: {e}")
            return "CLARIFY: I encountered an error generating the SQL query."
    
    def _extract_sql(self, generated_text: str) -> str:
        """
        Extract clean SQL from generated text.
        Handles various output formats.
        """
        # Remove markdown code blocks if present
        if '```sql' in generated_text.lower():
            parts = generated_text.split('```')
            for part in parts:
                if part.strip().lower().startswith('sql'):
                    return part[3:].strip()
        
        if '```' in generated_text:
            parts = generated_text.split('```')
            if len(parts) >= 3:
                return parts[1].strip()
        
        # Look for SELECT statement
        lines = generated_text.split('\n')
        sql_lines = []
        in_sql = False
        
        for line in lines:
            line_upper = line.strip().upper()
            if line_upper.startswith('SELECT'):
                in_sql = True
            
            if in_sql:
                sql_lines.append(line.strip())
                # Stop at semicolon or end of query indicators
                if line.strip().endswith(';'):
                    break
        
        if sql_lines:
            result = ' '.join(sql_lines)
        else:
            # If no clear SQL found, return the whole thing cleaned
            result = generated_text.strip()
            
            # Remove common prefixes
            for prefix in ['SQL:', 'Query:', 'Answer:']:
                if result.startswith(prefix):
                    result = result[len(prefix):].strip()
        
        # Remove any text after [ or ( that might be examples/rules
        if '[' in result:
            result = result[:result.index('[')].strip()
        if '(' in result and 'Output:' in result:
            result = result[:result.index('(')].strip()
        
        # Remove trailing semicolon for consistency
        result = result.rstrip(';').strip()
        
        return result
    
    def is_available(self) -> bool:
        """Check if TinyLlama service is operational."""
        return self.generator is not None


def create_tinyllama_service() -> TinyLlamaService:
    """Factory function to create TinyLlama service."""
    return TinyLlamaService()
