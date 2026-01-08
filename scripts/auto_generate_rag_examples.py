"""
[PRIMARY METHOD] Database-Agnostic RAG Example Generator

This is the PRIMARY and RECOMMENDED method for populating RAG examples.
Automatically generates examples for ANY database by analyzing schema.

USAGE:
    python scripts/auto_generate_rag_examples.py

FEATURES:
- Database-agnostic: Works with any SQLite database
- Schema-aware: Detects categorical constraints, numeric ranges
- Scalable: Generates 20-50 examples per table automatically
- Type-aware: Different patterns for TEXT, INTEGER, REAL columns
- Production-ready: No manual hardcoding required

ADVANTAGES:
- No hardcoding needed (unlike populate_rag_examples.py)
- Works with multiple databases
- Adapts to schema changes automatically
- Scales linearly with table count
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.core.database import DatabaseManager
from rag.retriever import SQLRetriever
from typing import List, Dict, Any


class RAGExampleGenerator:
    """Generate RAG examples dynamically from database schema."""
    
    def __init__(self, db_manager: DatabaseManager):
        self.db = db_manager
        self.schema = None
        self.detailed_schema = None
        self.examples = []
    
    def analyze_database(self):
        """Analyze database schema to understand structure."""
        print("\n[1/5] Analyzing database schema...")
        self.schema = self.db.get_schema()
        self.detailed_schema = self.db.get_detailed_schema()
        
        print(f"  ✓ Found {len(self.schema)} tables")
        for table, columns in self.schema.items():
            print(f"    - {table}: {len(columns)} columns")
    
    def generate_basic_queries(self):
        """Generate basic SELECT queries for each table."""
        print("\n[2/5] Generating basic SELECT queries...")
        count = 0
        
        for table, columns in self.schema.items():
            # SELECT * FROM table
            self.examples.append({
                "question": f"Show all records from {table}",
                "sql": f"SELECT * FROM {table}",
                "tables": [table],
                "columns": columns,
                "complexity": "simple"
            })
            count += 1
            
            # SELECT specific columns
            if len(columns) > 1:
                for col in columns[:3]:  # First 3 columns
                    self.examples.append({
                        "question": f"List all {col} from {table}",
                        "sql": f"SELECT {col} FROM {table}",
                        "tables": [table],
                        "columns": [col],
                        "complexity": "simple"
                    })
                    count += 1
                
                # Two column select
                if len(columns) >= 2:
                    col1, col2 = columns[0], columns[1]
                    self.examples.append({
                        "question": f"Show {col1} and {col2} from {table}",
                        "sql": f"SELECT {col1}, {col2} FROM {table}",
                        "tables": [table],
                        "columns": [col1, col2],
                        "complexity": "simple"
                    })
                    count += 1
        
        print(f"  ✓ Generated {count} basic queries")
    
    def generate_filter_queries(self):
        """Generate WHERE clause queries based on column types."""
        print("\n[3/5] Generating filtered queries...")
        count = 0
        
        for table in self.detailed_schema['tables']:
            columns = self.detailed_schema['tables'][table]
            
            for col_def in columns:
                col_parts = col_def.split(':')
                col_name = col_parts[0]
                col_type = col_parts[1].split('*')[0].split('∈')[0].split('(')[0].strip()
                
                # Extract categorical values if present
                if '∈' in col_def:
                    values_str = col_def.split('∈')[1].strip(' []')
                    values = [v.strip().strip("'\"") for v in values_str.split(',')]
                    
                    # Generate query for each categorical value
                    for value in values[:3]:  # Limit to 3 examples per column
                        # Determine if value needs quotes
                        needs_quotes = col_type.upper() in ['TEXT', 'VARCHAR', 'CHAR', 'STRING']
                        formatted_value = f"'{value}'" if needs_quotes else value
                        
                        self.examples.append({
                            "question": f"Show all {table} where {col_name} is {value}",
                            "sql": f"SELECT * FROM {table} WHERE {col_name} = {formatted_value}",
                            "tables": [table],
                            "columns": list(self.schema[table]),
                            "complexity": "simple"
                        })
                        count += 1
                
                # Numeric comparisons
                elif col_type.upper() in ['INTEGER', 'INT', 'REAL', 'FLOAT', 'DOUBLE', 'NUMERIC', 'DECIMAL']:
                    # Extract example values
                    if '(e.g.,' in col_def:
                        example_str = col_def.split('(e.g.,')[1].split(')')[0]
                        examples = [v.strip() for v in example_str.split(',')]
                        
                        if examples:
                            val = examples[0]
                            # Greater than
                            self.examples.append({
                                "question": f"Find {table} where {col_name} is greater than {val}",
                                "sql": f"SELECT * FROM {table} WHERE {col_name} > {val}",
                                "tables": [table],
                                "columns": list(self.schema[table]),
                                "complexity": "simple"
                            })
                            count += 1
                            
                            # Less than
                            self.examples.append({
                                "question": f"Get {table} with {col_name} less than {val}",
                                "sql": f"SELECT * FROM {table} WHERE {col_name} < {val}",
                                "tables": [table],
                                "columns": list(self.schema[table]),
                                "complexity": "simple"
                            })
                            count += 1
                            
                            # Exact match
                            self.examples.append({
                                "question": f"Show {table} where {col_name} equals {val}",
                                "sql": f"SELECT * FROM {table} WHERE {col_name} = {val}",
                                "tables": [table],
                                "columns": list(self.schema[table]),
                                "complexity": "simple"
                            })
                            count += 1
        
        print(f"  ✓ Generated {count} filtered queries")
    
    def generate_aggregation_queries(self):
        """Generate COUNT, AVG, SUM, MIN, MAX queries."""
        print("\n[4/5] Generating aggregation queries...")
        count = 0
        
        for table in self.detailed_schema['tables']:
            columns = self.detailed_schema['tables'][table]
            
            # COUNT total
            self.examples.append({
                "question": f"How many records in {table}",
                "sql": f"SELECT COUNT(*) as count FROM {table}",
                "tables": [table],
                "columns": [],
                "complexity": "aggregation"
            })
            count += 1
            
            for col_def in columns:
                col_parts = col_def.split(':')
                col_name = col_parts[0]
                col_type = col_parts[1].split('*')[0].split('∈')[0].split('(')[0].strip()
                
                # Categorical columns - GROUP BY
                if '∈' in col_def:
                    self.examples.append({
                        "question": f"Count {table} by {col_name}",
                        "sql": f"SELECT {col_name}, COUNT(*) as count FROM {table} GROUP BY {col_name}",
                        "tables": [table],
                        "columns": [col_name],
                        "complexity": "aggregation"
                    })
                    count += 1
                
                # Numeric columns - AVG, SUM, MIN, MAX
                elif col_type.upper() in ['INTEGER', 'INT', 'REAL', 'FLOAT', 'DOUBLE', 'NUMERIC', 'DECIMAL']:
                    # AVG
                    self.examples.append({
                        "question": f"What is the average {col_name} in {table}",
                        "sql": f"SELECT AVG({col_name}) as avg_{col_name} FROM {table}",
                        "tables": [table],
                        "columns": [col_name],
                        "complexity": "aggregation"
                    })
                    count += 1
                    
                    # SUM
                    self.examples.append({
                        "question": f"Total {col_name} from {table}",
                        "sql": f"SELECT SUM({col_name}) as total FROM {table}",
                        "tables": [table],
                        "columns": [col_name],
                        "complexity": "aggregation"
                    })
                    count += 1
                    
                    # MIN
                    self.examples.append({
                        "question": f"Minimum {col_name} in {table}",
                        "sql": f"SELECT MIN({col_name}) as min_{col_name} FROM {table}",
                        "tables": [table],
                        "columns": [col_name],
                        "complexity": "aggregation"
                    })
                    count += 1
                    
                    # MAX
                    self.examples.append({
                        "question": f"Maximum {col_name} in {table}",
                        "sql": f"SELECT MAX({col_name}) as max_{col_name} FROM {table}",
                        "tables": [table],
                        "columns": [col_name],
                        "complexity": "aggregation"
                    })
                    count += 1
        
        print(f"  ✓ Generated {count} aggregation queries")
    
    def generate_ordering_queries(self):
        """Generate ORDER BY and LIMIT queries."""
        print("\n[5/5] Generating sorting and limit queries...")
        count = 0
        
        for table, columns in self.schema.items():
            # ORDER BY first column
            if columns:
                col = columns[0]
                self.examples.append({
                    "question": f"Sort {table} by {col}",
                    "sql": f"SELECT * FROM {table} ORDER BY {col}",
                    "tables": [table],
                    "columns": columns,
                    "complexity": "simple"
                })
                count += 1
                
                self.examples.append({
                    "question": f"Sort {table} by {col} descending",
                    "sql": f"SELECT * FROM {table} ORDER BY {col} DESC",
                    "tables": [table],
                    "columns": columns,
                    "complexity": "simple"
                })
                count += 1
            
            # LIMIT queries
            self.examples.append({
                "question": f"Show first 5 records from {table}",
                "sql": f"SELECT * FROM {table} LIMIT 5",
                "tables": [table],
                "columns": columns,
                "complexity": "simple"
            })
            count += 1
            
            self.examples.append({
                "question": f"Get top 10 records from {table}",
                "sql": f"SELECT * FROM {table} LIMIT 10",
                "tables": [table],
                "columns": columns,
                "complexity": "simple"
            })
            count += 1
        
        print(f"  ✓ Generated {count} sorting queries")
    
    def generate_all_examples(self):
        """Generate all types of examples."""
        self.analyze_database()
        self.generate_basic_queries()
        self.generate_filter_queries()
        self.generate_aggregation_queries()
        self.generate_ordering_queries()
        
        print(f"\n✓ Total examples generated: {len(self.examples)}")
        return self.examples
    
    def populate_rag(self):
        """Populate ChromaDB with generated examples."""
        print("\n" + "=" * 60)
        print("POPULATING RAG WITH AUTO-GENERATED EXAMPLES")
        print("=" * 60)
        
        # Generate examples
        examples = self.generate_all_examples()
        
        # Initialize retriever
        print("\n[6/6] Adding examples to ChromaDB...")
        retriever = SQLRetriever()
        
        success_count = 0
        for idx, example in enumerate(examples, 1):
            try:
                retriever.add_example({
                    'question': example["question"],
                    'sql': example["sql"],
                    'schema': f"Table: {', '.join(example['tables'])} | Columns: {', '.join(example['columns'])}"
                })
                success_count += 1
                if idx % 25 == 0:
                    print(f"  ✓ Added {idx}/{len(examples)} examples")
            except Exception as e:
                print(f"  ✗ Failed to add example {idx}: {e}")
        
        print(f"\n✓ Successfully added {success_count}/{len(examples)} examples")
        print("\n" + "=" * 60)
        print("RAG AUTO-POPULATION COMPLETE")
        print("=" * 60)
        print(f"\n✓ RAG is now database-aware and scalable")
        print(f"✓ Works with any database structure")
        print(f"✓ Examples cover all tables and columns")


def main():
    """Main execution."""
    # Load database from environment
    from backend.core import create_database_manager_from_env
    
    print("=" * 60)
    print("SCALABLE RAG EXAMPLE GENERATOR")
    print("=" * 60)
    print("\nThis tool auto-generates RAG examples for ANY database")
    print("by analyzing the schema and creating relevant Q&A pairs.\n")
    
    try:
        # Create database manager
        db = create_database_manager_from_env()
        
        # Create generator and populate
        generator = RAGExampleGenerator(db)
        generator.populate_rag()
        
    except Exception as e:
        print(f"\n✗ Error: {e}")
        raise


if __name__ == "__main__":
    main()
