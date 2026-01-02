"""
SQL Validator - Ensures only safe SELECT queries are executed
Enforces: SELECT-only, schema validation, no destructive operations
"""

import re
import sqlparse
from sqlparse.sql import Statement, Identifier, IdentifierList, Token
from sqlparse.tokens import Keyword, DML
from typing import Dict, List, Tuple, Optional


class SQLValidator:
    """
    Validates SQL queries for safety before execution.
    Enforces read-only SELECT queries and schema compliance.
    """
    
    # Destructive keywords that must be blocked
    DESTRUCTIVE_KEYWORDS = {
        'DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER', 'CREATE',
        'TRUNCATE', 'REPLACE', 'MERGE', 'EXEC', 'EXECUTE',
        'GRANT', 'REVOKE', 'COMMIT', 'ROLLBACK'
    }
    
    def __init__(self, schema: Dict[str, List[str]]):
        """
        Initialize validator with database schema.
        
        Args:
            schema: Dict mapping table names to list of column names
                   e.g., {'users': ['id', 'name', 'email'], 'orders': [...]}
        """
        self.schema = {k.lower(): [c.lower() for c in v] for k, v in schema.items()}
        self.table_names = set(self.schema.keys())
    
    def validate(self, sql: str) -> Tuple[bool, Optional[str], Optional[str]]:
        """
        Validate SQL query for safety and correctness.
        
        Returns:
            (is_valid, sanitized_sql, error_message)
            - is_valid: True if query passes all checks
            - sanitized_sql: Query with added LIMIT if needed
            - error_message: Description of validation failure if any
        """
        
        # Step 1: Basic sanitization
        sql = sql.strip()
        
        # Remove any trailing semicolons
        while sql.endswith(';'):
            sql = sql[:-1].strip()
        
        if not sql:
            return False, None, "Empty query provided"
        
        # Step 2: Check for multiple statements
        if ';' in sql:
            return False, None, "Multiple statements not allowed. Only single SELECT queries permitted."
        
        # Step 3: Parse SQL
        try:
            parsed = sqlparse.parse(sql)
            if not parsed or len(parsed) == 0:
                return False, None, "Unable to parse SQL query"
            
            if len(parsed) > 1:
                return False, None, "Multiple statements detected. Only one query allowed."
            
            statement = parsed[0]
        except Exception as e:
            return False, None, f"SQL parsing error: {str(e)}"
        
        # Step 4: Verify it's a SELECT statement
        if not self._is_select_only(statement):
            return False, None, "Only SELECT queries are allowed. No INSERT, UPDATE, DELETE, DROP, or other destructive operations."
        
        # Step 5: Check for destructive keywords
        if self._contains_destructive_keywords(sql):
            return False, None, "Query contains destructive keywords. Only read operations are permitted."
        
        # Step 6: Extract and validate table/column references
        valid, error = self._validate_schema_references(statement)
        if not valid:
            return False, None, error
        
        # Step 7: Ensure LIMIT clause (add if missing)
        sql_with_limit = self._ensure_limit(sql, statement)
        
        return True, sql_with_limit, None
    
    def _is_select_only(self, statement: Statement) -> bool:
        """Check if statement is a SELECT query."""
        first_token = statement.token_first(skip_ws=True, skip_cm=True)
        if not first_token:
            return False
        
        return first_token.ttype is DML and first_token.value.upper() == 'SELECT'
    
    def _contains_destructive_keywords(self, sql: str) -> bool:
        """Check for destructive SQL keywords."""
        sql_upper = sql.upper()
        for keyword in self.DESTRUCTIVE_KEYWORDS:
            # Use word boundaries to avoid false positives
            pattern = r'\b' + keyword + r'\b'
            if re.search(pattern, sql_upper):
                return True
        return False
    
    def _validate_schema_references(self, statement: Statement) -> Tuple[bool, Optional[str]]:
        """
        Validate that all table and column references exist in schema.
        """
        try:
            # Extract table names from FROM and JOIN clauses
            tables = self._extract_tables(statement)
            
            # Verify all tables exist
            for table in tables:
                if table not in self.table_names:
                    return False, f"Table '{table}' does not exist in the database schema. Available tables: {', '.join(sorted(self.table_names))}"
            
            # Extract column references (simplified - could be enhanced)
            # For MVP, we do basic validation. Full validation would need context-aware parsing.
            columns = self._extract_columns(statement)
            
            # Check columns against schema (with table context when available)
            for col, table_hint in columns:
                if table_hint:
                    # Qualified column reference (table.column)
                    if table_hint not in self.table_names:
                        return False, f"Table '{table_hint}' not found"
                    if col not in self.schema[table_hint] and col != '*':
                        return False, f"Column '{col}' not found in table '{table_hint}'. Available columns: {', '.join(self.schema[table_hint])}"
                else:
                    # Unqualified column - check if exists in any referenced table
                    if col != '*' and not self._column_exists_in_any_table(col, tables):
                        return False, f"Column '{col}' not found in any referenced tables"
            
            return True, None
            
        except Exception as e:
            # If parsing fails, allow it (better false negative than false positive for UX)
            # The database will catch actual errors
            return True, None
    
    def _extract_tables(self, statement: Statement) -> List[str]:
        """Extract table names from SQL statement."""
        tables = []
        from_seen = False
        
        for token in statement.tokens:
            if from_seen:
                if isinstance(token, Identifier):
                    table_name = token.get_real_name()
                    if table_name:
                        tables.append(table_name.lower())
                elif isinstance(token, IdentifierList):
                    for identifier in token.get_identifiers():
                        table_name = identifier.get_real_name()
                        if table_name:
                            tables.append(table_name.lower())
                elif token.ttype is Keyword and token.value.upper() in ('WHERE', 'ORDER', 'GROUP', 'HAVING', 'LIMIT'):
                    from_seen = False
            
            if token.ttype is Keyword and token.value.upper() == 'FROM':
                from_seen = True
            
            # Handle JOIN clauses
            if token.ttype is Keyword and 'JOIN' in token.value.upper():
                from_seen = True
        
        return tables
    
    def _extract_columns(self, statement: Statement) -> List[Tuple[str, Optional[str]]]:
        """
        Extract column references from SQL.
        Returns list of (column_name, table_name) tuples.
        table_name is None if column is unqualified.
        """
        columns = []
        
        # Extract columns recursively from all tokens (SELECT, WHERE, JOIN, etc.)
        # Skip tokens that come after FROM or JOIN (those are table names)
        self._extract_columns_recursive(statement.tokens, columns, skip_next_identifier=False)
        
        return columns
    
    def _extract_columns_recursive(self, tokens, columns, skip_next_identifier=False):
        """Recursively extract column identifiers from tokens."""
        i = 0
        while i < len(tokens):
            token = tokens[i]
            
            # Check if this is a FROM or JOIN keyword - skip the next identifier
            if token.ttype is Keyword and token.value.upper() in ('FROM', 'JOIN'):
                skip_next_identifier = True
                i += 1
                continue
            
            # Reset skip flag after WHERE, ORDER BY, etc
            if token.ttype is Keyword and token.value.upper() in ('WHERE', 'ORDER', 'GROUP', 'HAVING', 'LIMIT'):
                skip_next_identifier = False
            
            # Handle nested token groups (WHERE clauses, etc.)
            if hasattr(token, 'tokens'):
                self._extract_columns_recursive(token.tokens, columns, skip_next_identifier)
            
            # Extract identifiers (but skip if they're table names after FROM/JOIN)
            if not skip_next_identifier:
                if isinstance(token, IdentifierList):
                    for identifier in token.get_identifiers():
                        col, table = self._parse_identifier(identifier)
                        if col:
                            columns.append((col, table))
                elif isinstance(token, Identifier):
                    col, table = self._parse_identifier(token)
                    if col and col.lower() not in ('select', 'from', 'where', 'order', 'group'):
                        columns.append((col, table))
            else:
                # We just skipped a table identifier, reset the flag
                if isinstance(token, (Identifier, IdentifierList)):
                    skip_next_identifier = False
            
            i += 1
    
    def _parse_identifier(self, identifier) -> Tuple[Optional[str], Optional[str]]:
        """Parse an identifier to extract column and table names."""
        if hasattr(identifier, 'get_real_name'):
            name = identifier.get_real_name()
            if name:
                parts = name.split('.')
                if len(parts) == 2:
                    return parts[1].lower(), parts[0].lower()
                return name.lower(), None
        return None, None
    
    def _column_exists_in_any_table(self, column: str, tables: List[str]) -> bool:
        """Check if column exists in any of the given tables."""
        if not tables:
            # If no tables specified, check all tables
            tables = list(self.table_names)
        
        for table in tables:
            if table in self.schema and column in self.schema[table]:
                return True
        return False
    
    def _ensure_limit(self, sql: str, statement: Statement, max_limit: int = 500) -> str:
        """
        Ensure query has a LIMIT clause. Add one if missing.
        """
        sql_upper = sql.upper()
        
        # Check if LIMIT already exists
        if 'LIMIT' in sql_upper:
            # Verify the limit is reasonable
            try:
                limit_match = re.search(r'\bLIMIT\s+(\d+)', sql_upper)
                if limit_match:
                    existing_limit = int(limit_match.group(1))
                    if existing_limit > max_limit:
                        # Replace with max_limit
                        sql = re.sub(r'\bLIMIT\s+\d+', f'LIMIT {max_limit}', sql, flags=re.IGNORECASE)
            except:
                pass
            return sql
        
        # Add LIMIT clause
        return f"{sql} LIMIT {max_limit}"


def create_validator_from_schema(schema_dict: Dict[str, List[str]]) -> SQLValidator:
    """
    Factory function to create a validator from schema dictionary.
    
    Args:
        schema_dict: Dictionary mapping table names to column lists
    
    Returns:
        Configured SQLValidator instance
    """
    return SQLValidator(schema_dict)
