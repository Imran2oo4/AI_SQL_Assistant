"""
Prompt Builder Service - Schema-aware SQL Generation
Constructs prompts with schema + RAG examples + clear instructions
"""

from typing import List, Dict, Any


class SchemaAwarePromptBuilder:
    """
    Builds prompts for SQL generation with schema awareness and few-shot examples.
    Supports 4 specialized prompt templates based on query complexity.
    """
    
    def __init__(self):
        self.prompt_templates = {
            'simple': self._get_simple_prompt(),
            'complex': self._get_complex_prompt(),
            'aggregation': self._get_aggregation_prompt(),
            'modification': self._get_modification_prompt()
        }
        self.system_instruction = self._get_system_instruction()
    
    def _get_simple_prompt(self) -> str:
        """Prompt for simple SELECT queries with basic WHERE clauses."""
        return """You are an expert SQL generator for SIMPLE queries. Generate clean SELECT statements with basic filtering.

CRITICAL RULES - FOLLOW EXACTLY:
1. Use SELECT with specific columns (avoid SELECT *)
2. For exact values, use = operator (NOT BETWEEN, NOT >, NOT <)
   - "age is 20" means: WHERE age = 20
   - "gender is male" means: WHERE gender = 'Male' (check schema for exact values)
3. Use BETWEEN only when explicitly asked for a range
4. Match column values EXACTLY as shown in schema examples
5. Output ONLY the SQL query - no explanations, no extra text
6. Do not add conditions that were not requested"""

    def _get_complex_prompt(self) -> str:
        """Prompt for complex queries with joins and subqueries."""
        return """You are an expert SQL generator for COMPLEX queries. Handle multi-table joins and nested queries.

RULES FOR COMPLEX QUERIES:
1. Use explicit JOIN syntax (INNER JOIN, LEFT JOIN)
2. Handle subqueries when needed
3. Use proper table aliases
4. Ensure foreign key relationships are correct
5. Output ONLY the SQL - no explanations"""

    def _get_aggregation_prompt(self) -> str:
        """Prompt for aggregation queries with GROUP BY."""
        return """You are an expert SQL generator for AGGREGATION queries. Handle COUNT, SUM, AVG, MIN, MAX with grouping.

RULES FOR AGGREGATION QUERIES:
1. Use appropriate aggregate functions
2. Include GROUP BY for non-aggregated columns
3. Use HAVING for aggregate filtering
4. Consider ORDER BY for sorted results
5. Output ONLY the SQL - no explanations"""

    def _get_modification_prompt(self) -> str:
        """Prompt for data modification (INSERT, UPDATE, DELETE)."""
        return """You are an expert SQL generator for DATA MODIFICATION. Handle INSERT, UPDATE, DELETE safely.

RULES FOR MODIFICATION QUERIES:
1. ALWAYS include WHERE clause for UPDATE/DELETE
2. Validate data types match schema
3. Use proper syntax for target database
4. Consider constraints and foreign keys
5. Output ONLY the SQL - no explanations
WARNING: Be extremely careful with DELETE and UPDATE without WHERE!"""

    def _get_system_instruction(self) -> str:
        """Base system instruction for SQL generation."""
        return """You are an expert SQL query generator. Your task is to convert natural language questions into syntactically correct SQL queries.

CRITICAL RULES - DO NOT DEVIATE:
1. Output ONLY the SQL query - no explanations, no markdown, no commentary
2. Use only tables and columns that exist in the provided schema
3. For EXACT values, use = operator (NOT BETWEEN unless explicitly asked)
   - "age is 20" → WHERE age = 20
   - "gender is male" → WHERE gender = 'Male' (check schema for exact value format)
4. LITERAL VALUE PRESERVATION (MOST IMPORTANT):
   - When schema shows categorical constraints like "gender ∈ ['Male', 'Female']", use EXACTLY those values
   - NEVER abbreviate, normalize, or transform categorical values (Male ≠ M, Female ≠ F)
   - NEVER infer synonyms unless explicitly in the schema (Male ≠ 'man', Female ≠ 'woman')
   - ALWAYS use the EXACT string format shown in the schema constraint set
5. Do NOT add extra conditions that were not requested
6. If uncertain, respond with: "CLARIFY: <your question>"

Your response must be either:
- A single line SQL query following the exact request
- OR "CLARIFY: <question>" if more information is needed"""
    
    def _detect_edge_cases(self, question: str) -> Dict[str, Any]:
        """
        Detect 6 types of edge cases in questions.
        Returns: Dict with edge case type and appropriate response
        """
        question_lower = question.lower()
        
        # 1. Ambiguous references
        if any(word in question_lower for word in ['it', 'that', 'those', 'them', 'this']) and \
           not any(table in question_lower for table in ['table', 'data', 'records']):
            return {
                'detected': True,
                'type': 'ambiguous_reference',
                'response': 'CLARIFY: Could you please specify which table or data you are referring to?'
            }
        
        # 2. Missing context
        if question_lower in ['show', 'list', 'get', 'find', 'display']:
            return {
                'detected': True,
                'type': 'missing_context',
                'response': 'CLARIFY: What would you like me to show or list?'
            }
        
        # 3. Impossible conditions
        impossible_patterns = ['before today and after tomorrow', 'less than 0 and greater than 100',
                              'older than 200', 'price negative']
        if any(pattern in question_lower for pattern in impossible_patterns):
            return {
                'detected': True,
                'type': 'impossible_condition',
                'response': 'CLARIFY: The conditions seem contradictory. Could you please rephrase?'
            }
        
        # 4. Non-existent operations
        non_sql_ops = ['machine learning', 'predict', 'forecast', 'train model', 
                       'visualize', 'plot', 'graph', 'chart']
        if any(op in question_lower for op in non_sql_ops):
            return {
                'detected': True,
                'type': 'non_sql_operation',
                'response': 'CLARIFY: This operation cannot be performed with SQL. SQL can query data but not perform ML or visualization.'
            }
        
        # 5. Overly vague
        if len(question.split()) <= 2:
            return {
                'detected': True,
                'type': 'too_vague',
                'response': 'CLARIFY: Could you provide more details about what you want to query?'
            }
        
        # 6. Multiple unrelated questions
        if question_lower.count('?') > 1 or question_lower.count(' and ') > 2:
            sentences = [s.strip() for s in question.split('.') if s.strip()]
            if len(sentences) > 2:
                return {
                    'detected': True,
                    'type': 'multiple_questions',
                    'response': 'CLARIFY: Please ask one question at a time for better accuracy.'
                }
        
        return {'detected': False}
    
    def _detect_query_complexity(self, question: str) -> str:
        """
        Detect query complexity from natural language question.
        Returns: 'simple', 'complex', 'aggregation', or 'modification'
        """
        question_lower = question.lower()
        
        # Check for modification keywords
        modification_keywords = ['insert', 'update', 'delete', 'add', 'remove', 'modify', 'change']
        if any(kw in question_lower for kw in modification_keywords):
            return 'modification'
        
        # Check for aggregation keywords
        aggregation_keywords = ['count', 'sum', 'average', 'avg', 'total', 'max', 'min', 
                               'group by', 'how many', 'number of', 'statistics']
        if any(kw in question_lower for kw in aggregation_keywords):
            return 'aggregation'
        
        # Check for complex query indicators
        complex_keywords = ['join', 'combine', 'relationship', 'compare', 'between', 
                           'both', 'all...and', 'subquery', 'nested']
        if any(kw in question_lower for kw in complex_keywords):
            return 'complex'
        
        # Default to simple
        return 'simple'
    
    def build_prompt(
        self,
        question: str,
        schema: Dict[str, List[str]],
        examples: List[Dict[str, str]] = None,
        detailed_schema: Dict[str, Any] = None
    ) -> str:
        """
        Build a complete prompt for SQL generation with complexity-aware template.
        
        Args:
            question: Natural language question
            schema: Dict of table_name -> [column_names]
            examples: List of {question, sql} example pairs from RAG
            detailed_schema: Optional detailed schema with types and FK relationships
        
        Returns:
            Complete prompt string
        """
        # Check for edge cases first
        edge_case = self._detect_edge_cases(question)
        if edge_case['detected']:
            # Return clarification response for edge cases
            return edge_case['response']
        
        # Detect query complexity and select appropriate template
        complexity = self._detect_query_complexity(question)
        specialized_prompt = self.prompt_templates.get(complexity, self.system_instruction)
        
        prompt_parts = [specialized_prompt, ""]
        prompt_parts.append(f"[Query Type: {complexity.upper()}]")
        prompt_parts.append("")
        
        # Add database schema
        prompt_parts.append("DATABASE SCHEMA:")
        prompt_parts.append(self._format_schema(schema, detailed_schema))
        prompt_parts.append("")
        
        # Add few-shot examples if available
        if examples and len(examples) > 0:
            prompt_parts.append("EXAMPLES OF SIMILAR QUERIES:")
            for i, example in enumerate(examples[:5], 1):  # Max 5 examples
                prompt_parts.append(f"\nExample {i}:")
                prompt_parts.append(f"Question: {example.get('question', '')}")
                prompt_parts.append(f"SQL: {example.get('sql', '')}")
            prompt_parts.append("")
        
        # Add the actual question
        prompt_parts.append("NOW GENERATE SQL FOR THIS QUESTION:")
        prompt_parts.append(f"Question: {question}")
        prompt_parts.append("")
        prompt_parts.append("SQL:")
        
        return "\n".join(prompt_parts)
    
    def _format_schema(
        self,
        schema: Dict[str, List[str]],
        detailed_schema: Dict[str, Any] = None
    ) -> str:
        """
        Format schema information for prompt injection.
        """
        lines = []
        
        if detailed_schema and 'tables' in detailed_schema:
            # Use detailed schema with types
            for table_name, columns in detailed_schema['tables'].items():
                lines.append(f"Table: {table_name}")
                lines.append(f"  Columns: {', '.join(columns)}")
            
            # Add foreign key relationships if available
            if detailed_schema.get('fks'):
                lines.append("\nRelationships:")
                for fk in detailed_schema['fks']:
                    lines.append(f"  {fk['from']} -> {fk['to']}")
        else:
            # Use simple schema
            for table_name, columns in schema.items():
                lines.append(f"Table: {table_name}")
                lines.append(f"  Columns: {', '.join(columns)}")
        
        return "\n".join(lines)
    
    def build_groq_explanation_prompt(self, question: str, sql: str) -> str:
        """
        Build prompt for Groq to generate plain-English explanation.
        
        Args:
            question: Original question
            sql: Final SQL query
        
        Returns:
            Explanation prompt
        """
        return f"""Generate a clear, beginner-friendly explanation of this SQL query.

QUESTION: {question}

SQL QUERY:
{sql}

Provide a 2-4 sentence explanation that:
1. Describes what data is being retrieved
2. Mentions any important filters, joins, or groupings
3. Uses simple language that a beginner can understand

Do not include the SQL query itself in your response, only the explanation."""


def create_prompt_builder() -> SchemaAwarePromptBuilder:
    """Factory function to create a prompt builder."""
    return SchemaAwarePromptBuilder()
