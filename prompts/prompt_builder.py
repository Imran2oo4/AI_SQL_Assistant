"""
Prompt Builder for SQL Learning Assistant
Handles: Context Management, User Interaction Flows, Edge Cases
"""

import re
import os
import sys
import json
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from prompts.system_prompts import (
    get_system_prompt,
    get_prompt_template,
    CLARIFICATION_PROMPT,
    ERROR_RECOVERY_PROMPT
)

# =============================================================================
# OUTPUT DIRECTORIES
# =============================================================================

OUTPUT_DIR = "outputs/prompts"
LOGS_DIR = f"{OUTPUT_DIR}/logs"

def setup_directories():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    os.makedirs(LOGS_DIR, exist_ok=True)

# =============================================================================
# CONTEXT MANAGEMENT
# =============================================================================

class ConversationContext:
    """
    Manages conversation history and context for multi-turn interactions.
    """
    
    def __init__(self, max_history=5):
        self.history = []
        self.max_history = max_history
        self.current_tables = []
        self.current_schema = {}
        self.user_preferences = {}
    
    def add_turn(self, question, sql_response, success=True):
        """Add a conversation turn to history."""
        self.history.append({
            'question': question,
            'sql': sql_response,
            'success': success,
            'timestamp': datetime.now().isoformat()
        })
        
        # Keep only recent history
        if len(self.history) > self.max_history:
            self.history = self.history[-self.max_history:]
    
    def get_history_context(self):
        """Format history for prompt injection."""
        if not self.history:
            return ""
        
        context = "Previous conversation:\n"
        for turn in self.history[-3:]:  # Last 3 turns
            context += f"Q: {turn['question']}\n"
            context += f"SQL: {turn['sql']}\n\n"
        
        return context
    
    def set_schema(self, schema_dict):
        """Set current database schema context."""
        self.current_schema = schema_dict
    
    def get_schema_context(self):
        """Format schema for prompt injection."""
        if not self.current_schema:
            return ""
        
        context = "Available tables and columns:\n"
        for table, columns in self.current_schema.items():
            context += f"- {table}: {', '.join(columns)}\n"
        
        return context
    
    def clear(self):
        """Clear conversation history."""
        self.history = []
        self.current_tables = []
        self.current_schema = {}

# =============================================================================
# QUERY ANALYSIS (For Specialized Flows)
# =============================================================================

def analyze_query_intent(question):
    """
    Analyze user question to determine query type and intent.
    Returns: dict with query_type, keywords, entities
    """
    question_lower = question.lower()
    
    # Detect query type
    query_type = 'general'
    
    # Aggregation patterns
    agg_patterns = ['count', 'sum', 'average', 'avg', 'total', 'maximum', 'max', 
                    'minimum', 'min', 'how many', 'what is the total']
    if any(p in question_lower for p in agg_patterns):
        query_type = 'aggregation'
    
    # Complex query patterns
    complex_patterns = ['join', 'combine', 'merge', 'from multiple', 'across tables',
                       'subquery', 'nested', 'with the highest', 'with the lowest']
    if any(p in question_lower for p in complex_patterns):
        query_type = 'complex'
    
    # Modification patterns
    mod_patterns = ['insert', 'add new', 'update', 'change', 'modify', 'delete', 'remove']
    if any(p in question_lower for p in mod_patterns):
        query_type = 'modification'
    
    # Simple patterns (if nothing else matched)
    simple_patterns = ['show', 'list', 'get', 'find', 'select', 'display']
    if query_type == 'general' and any(p in question_lower for p in simple_patterns):
        query_type = 'simple'
    
    # Extract potential keywords
    keywords = []
    sql_keywords = ['where', 'group by', 'order by', 'having', 'limit', 'join', 
                   'distinct', 'between', 'like', 'in']
    for kw in sql_keywords:
        if kw in question_lower:
            keywords.append(kw.upper())
    
    return {
        'query_type': query_type,
        'keywords': keywords,
        'question_length': len(question.split())
    }

# =============================================================================
# EDGE CASE HANDLING
# =============================================================================

def detect_edge_cases(question):
    """
    Detect potential edge cases in user question.
    Returns: list of edge case types detected
    """
    edge_cases = []
    question_lower = question.lower()
    
    # Empty or too short
    if len(question.strip()) < 5:
        edge_cases.append('too_short')
    
    # Too vague
    vague_patterns = ['something', 'stuff', 'things', 'data', 'information']
    if any(p in question_lower for p in vague_patterns) and len(question.split()) < 5:
        edge_cases.append('too_vague')
    
    # Multiple questions
    if question.count('?') > 1:
        edge_cases.append('multiple_questions')
    
    # Contains SQL (user pasted SQL instead of question)
    sql_patterns = ['SELECT', 'INSERT', 'UPDATE', 'DELETE', 'FROM', 'WHERE']
    if sum(1 for p in sql_patterns if p in question.upper()) >= 2:
        edge_cases.append('contains_sql')
    
    # Potentially dangerous operations
    dangerous_patterns = ['drop table', 'truncate', 'delete all', 'remove all']
    if any(p in question_lower for p in dangerous_patterns):
        edge_cases.append('dangerous_operation')
    
    # Non-SQL question
    non_sql_patterns = ['weather', 'hello', 'how are you', 'thank', 'bye']
    if any(p in question_lower for p in non_sql_patterns):
        edge_cases.append('not_sql_related')
    
    return edge_cases

def handle_edge_case(edge_case_type, question):
    """
    Generate appropriate response for edge cases.
    Returns: (should_continue, message)
    """
    responses = {
        'too_short': (
            False,
            "Your question is too short. Please provide more details about what data you want to retrieve."
        ),
        'too_vague': (
            False,
            "Your question is a bit vague. Could you specify:\n- Which table(s) to query?\n- What columns to retrieve?\n- Any conditions to filter by?"
        ),
        'multiple_questions': (
            False,
            "I detected multiple questions. Please ask one question at a time for accurate SQL generation."
        ),
        'contains_sql': (
            False,
            "It looks like you've pasted SQL code. Please describe what you want in natural language, and I'll generate the SQL for you."
        ),
        'dangerous_operation': (
            False,
            "⚠️ This appears to be a destructive operation (DROP/TRUNCATE/DELETE ALL). Please confirm you want to proceed or rephrase your question."
        ),
        'not_sql_related': (
            False,
            "I'm an SQL assistant. Please ask me questions about querying databases, and I'll help generate SQL queries."
        )
    }
    
    return responses.get(edge_case_type, (True, ""))

# =============================================================================
# PROMPT BUILDER CLASS
# =============================================================================

class PromptBuilder:
    """
    Main class for building prompts with context management.
    """
    
    def __init__(self):
        self.context = ConversationContext()
        self.log_file = None
        setup_directories()
    
    def build_prompt(self, question, rag_context="", include_history=True):
        """
        Build complete prompt for SQL generation.
        
        Args:
            question: User's natural language question
            rag_context: Retrieved examples from RAG
            include_history: Whether to include conversation history
            
        Returns:
            dict with 'success', 'prompt' or 'error'
        """
        # Check for edge cases
        edge_cases = detect_edge_cases(question)
        
        if edge_cases:
            should_continue, message = handle_edge_case(edge_cases[0], question)
            if not should_continue:
                return {
                    'success': False,
                    'error': message,
                    'edge_case': edge_cases[0]
                }
        
        # Analyze query intent
        intent = analyze_query_intent(question)
        
        # Get appropriate system prompt
        system_prompt = get_system_prompt(intent['query_type'])
        
        # Build context parts
        context_parts = []
        
        # Add schema context if available
        schema_context = self.context.get_schema_context()
        if schema_context:
            context_parts.append(schema_context)
        
        # Add conversation history
        if include_history:
            history_context = self.context.get_history_context()
            if history_context:
                context_parts.append(history_context)
        
        # Add RAG context
        if rag_context:
            context_parts.append(rag_context)
        
        # Build final prompt
        if rag_context:
            template = get_prompt_template('rag')
            prompt = template.format(
                context=rag_context,
                question=question
            )
        else:
            template = get_prompt_template('zero_shot')
            prompt = template.format(question=question)
        
        # Combine everything
        full_prompt = f"{system_prompt}\n\n"
        if context_parts:
            full_prompt += "\n".join(context_parts) + "\n\n"
        full_prompt += prompt
        
        # Log the prompt
        self._log_prompt(question, intent, full_prompt)
        
        return {
            'success': True,
            'prompt': full_prompt,
            'system_prompt': system_prompt,
            'query_type': intent['query_type'],
            'keywords': intent['keywords']
        }
    
    def add_response(self, question, sql_response, success=True):
        """Add a completed interaction to history."""
        self.context.add_turn(question, sql_response, success)
    
    def set_schema(self, schema_dict):
        """Set database schema for context."""
        self.context.set_schema(schema_dict)
    
    def clear_context(self):
        """Clear all context."""
        self.context.clear()
    
    def _log_prompt(self, question, intent, prompt):
        """Log prompt for debugging/analysis."""
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'question': question,
            'intent': intent,
            'prompt_length': len(prompt)
        }
        
        log_file = f"{LOGS_DIR}/prompt_log.jsonl"
        with open(log_file, 'a') as f:
            f.write(json.dumps(log_entry) + '\n')

# =============================================================================
# USER INTERACTION FLOWS
# =============================================================================

def get_clarification_questions(question, intent):
    """
    Generate clarification questions for ambiguous queries.
    """
    clarifications = []
    
    # Generic clarifications based on query type
    if intent['query_type'] == 'aggregation':
        clarifications.append("Which column should be aggregated?")
        clarifications.append("Should results be grouped by any column?")
    
    if intent['query_type'] == 'complex':
        clarifications.append("Which tables need to be joined?")
        clarifications.append("What is the relationship between the tables?")
    
    # Check for missing specifics
    if 'table' not in question.lower():
        clarifications.append("Which table(s) should be queried?")
    
    if not any(word in question.lower() for word in ['all', 'specific', 'where', 'filter']):
        clarifications.append("Do you want all records or filtered results?")
    
    return clarifications

def create_error_recovery_prompt(original_question, error_message):
    """
    Create prompt for recovering from errors.
    """
    return ERROR_RECOVERY_PROMPT.format(
        error=error_message,
        question=original_question
    )

# =============================================================================
# TEST
# =============================================================================

def test_prompt_builder():
    """Test the prompt builder functionality."""
    
    print("=" * 60)
    print("TESTING PROMPT BUILDER")
    print("=" * 60)
    
    builder = PromptBuilder()
    
    # Test 1: Normal question
    print("\n[TEST 1] Normal Question")
    print("-" * 40)
    result = builder.build_prompt(
        "Find all employees with salary above 50000",
        rag_context="Example 1:\nQ: Get workers earning more than 40000\nSQL: SELECT * FROM employees WHERE salary > 40000"
    )
    print(f"Success: {result['success']}")
    print(f"Query Type: {result.get('query_type')}")
    print(f"Prompt Length: {len(result.get('prompt', ''))}")
    
    # Test 2: Edge case - too short
    print("\n[TEST 2] Edge Case - Too Short")
    print("-" * 40)
    result = builder.build_prompt("SQL")
    print(f"Success: {result['success']}")
    print(f"Error: {result.get('error', 'None')}")
    
    # Test 3: Edge case - contains SQL
    print("\n[TEST 3] Edge Case - Contains SQL")
    print("-" * 40)
    result = builder.build_prompt("SELECT * FROM users WHERE id = 1")
    print(f"Success: {result['success']}")
    print(f"Error: {result.get('error', 'None')}")
    
    # Test 4: Edge case - dangerous operation
    print("\n[TEST 4] Edge Case - Dangerous Operation")
    print("-" * 40)
    result = builder.build_prompt("Drop table users")
    print(f"Success: {result['success']}")
    print(f"Error: {result.get('error', 'None')}")
    
    # Test 5: Aggregation query
    print("\n[TEST 5] Aggregation Query")
    print("-" * 40)
    result = builder.build_prompt("Count total orders by customer")
    print(f"Success: {result['success']}")
    print(f"Query Type: {result.get('query_type')}")
    
    # Test 6: Context management
    print("\n[TEST 6] Context Management")
    print("-" * 40)
    builder.set_schema({
        'employees': ['id', 'name', 'salary', 'dept_id'],
        'departments': ['id', 'name', 'location']
    })
    builder.add_response("Show all employees", "SELECT * FROM employees", success=True)
    result = builder.build_prompt("Now filter by department")
    print(f"Success: {result['success']}")
    print(f"Has History: {'Previous conversation' in result.get('prompt', '')}")
    
    print("\n" + "=" * 60)
    print("✓ All tests complete")
    print("=" * 60)

if __name__ == "__main__":
    test_prompt_builder()