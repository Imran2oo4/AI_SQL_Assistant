"""
Knowledge Base Builder for RAG System
Includes: Chunking Strategies, Vector Storage
"""

import os
import pandas as pd
import chromadb
import json
import re
from datetime import datetime
import sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from rag.embeddings import get_embeddings_batch

# =============================================================================
# CONFIGURATION
# =============================================================================

CHROMA_DIR = "chromadb_data"
COLLECTION_NAME = "sql_knowledge"
OUTPUT_DIR = "outputs/rag"
STATS_DIR = f"{OUTPUT_DIR}/stats"
REPORT_DIR = f"{OUTPUT_DIR}/reports"

def setup_directories():
    """Create necessary directories."""
    for d in [CHROMA_DIR, OUTPUT_DIR, STATS_DIR, REPORT_DIR]:
        os.makedirs(d, exist_ok=True)

# =============================================================================
# CHUNKING STRATEGIES
# =============================================================================

def chunk_by_sql_clauses(sql):
    """
    Chunking Strategy 1: Split SQL by clauses.
    Identifies SELECT, FROM, WHERE, GROUP BY, ORDER BY, etc.
    """
    clauses = []
    
    # Common SQL clause patterns
    patterns = [
        (r'\bSELECT\b.*?(?=\bFROM\b|$)', 'SELECT'),
        (r'\bFROM\b.*?(?=\bWHERE\b|\bGROUP\b|\bORDER\b|\bLIMIT\b|$)', 'FROM'),
        (r'\bWHERE\b.*?(?=\bGROUP\b|\bORDER\b|\bLIMIT\b|$)', 'WHERE'),
        (r'\bGROUP BY\b.*?(?=\bHAVING\b|\bORDER\b|\bLIMIT\b|$)', 'GROUP BY'),
        (r'\bHAVING\b.*?(?=\bORDER\b|\bLIMIT\b|$)', 'HAVING'),
        (r'\bORDER BY\b.*?(?=\bLIMIT\b|$)', 'ORDER BY'),
        (r'\bLIMIT\b.*', 'LIMIT'),
    ]
    
    sql_upper = sql.upper()
    for pattern, clause_name in patterns:
        match = re.search(pattern, sql_upper, re.IGNORECASE | re.DOTALL)
        if match:
            clauses.append(clause_name)
    
    return clauses

def chunk_by_complexity(question, sql):
    """
    Chunking Strategy 2: Categorize by query complexity.
    """
    sql_upper = sql.upper()
    
    # Determine complexity level
    complexity_score = 0
    
    # Check for complex features
    if 'JOIN' in sql_upper:
        complexity_score += 2
    if 'SUBQUERY' in sql_upper or sql_upper.count('SELECT') > 1:
        complexity_score += 2
    if 'GROUP BY' in sql_upper:
        complexity_score += 1
    if 'HAVING' in sql_upper:
        complexity_score += 1
    if 'ORDER BY' in sql_upper:
        complexity_score += 1
    if any(agg in sql_upper for agg in ['COUNT', 'SUM', 'AVG', 'MAX', 'MIN']):
        complexity_score += 1
    if 'UNION' in sql_upper:
        complexity_score += 2
    
    # Categorize
    if complexity_score <= 1:
        return 'simple'
    elif complexity_score <= 3:
        return 'intermediate'
    else:
        return 'complex'

def extract_sql_keywords(sql):
    """
    Chunking Strategy 3: Extract SQL keywords for metadata.
    """
    sql_upper = sql.upper()
    
    keywords = []
    
    # Operations
    if 'SELECT' in sql_upper:
        keywords.append('SELECT')
    if 'INSERT' in sql_upper:
        keywords.append('INSERT')
    if 'UPDATE' in sql_upper:
        keywords.append('UPDATE')
    if 'DELETE' in sql_upper:
        keywords.append('DELETE')
    
    # Joins
    if 'INNER JOIN' in sql_upper:
        keywords.append('INNER JOIN')
    elif 'LEFT JOIN' in sql_upper:
        keywords.append('LEFT JOIN')
    elif 'RIGHT JOIN' in sql_upper:
        keywords.append('RIGHT JOIN')
    elif 'JOIN' in sql_upper:
        keywords.append('JOIN')
    
    # Clauses
    for clause in ['WHERE', 'GROUP BY', 'HAVING', 'ORDER BY', 'LIMIT']:
        if clause in sql_upper:
            keywords.append(clause)
    
    # Aggregations
    for agg in ['COUNT', 'SUM', 'AVG', 'MAX', 'MIN']:
        if agg in sql_upper:
            keywords.append(agg)
    
    # Subqueries
    if sql_upper.count('SELECT') > 1:
        keywords.append('SUBQUERY')
    
    return keywords

def calculate_chunk_size(text):
    """Calculate appropriate chunk size category."""
    word_count = len(text.split())
    
    if word_count <= 10:
        return 'short'
    elif word_count <= 25:
        return 'medium'
    else:
        return 'long'

# =============================================================================
# DOCUMENT PREPARATION WITH CHUNKING
# =============================================================================

def prepare_documents_with_chunking(datasets):
    """
    Prepare documents with chunking metadata.
    Each document gets rich metadata for filtering/ranking.
    """
    documents = []
    metadatas = []
    ids = []
    
    idx = 0
    for source, df in datasets.items():
        for _, row in df.iterrows():
            question = str(row['question'])
            sql = str(row['sql'])
            
            # Apply chunking strategies
            sql_clauses = chunk_by_sql_clauses(sql)
            complexity = chunk_by_complexity(question, sql)
            keywords = extract_sql_keywords(sql)
            q_size = calculate_chunk_size(question)
            sql_size = calculate_chunk_size(sql)
            
            # Create rich metadata
            metadata = {
                'sql': sql,
                'source': source,
                'question': question,
                # Chunking metadata
                'complexity': complexity,
                'sql_clauses': ','.join(sql_clauses),
                'keywords': ','.join(keywords),
                'question_size': q_size,
                'sql_size': sql_size,
                'keyword_count': len(keywords),
                'clause_count': len(sql_clauses),
            }
            
            documents.append(question)
            metadatas.append(metadata)
            ids.append(f"doc_{idx}")
            idx += 1
    
    return documents, metadatas, ids

# =============================================================================
# CHROMADB CLIENT
# =============================================================================

def get_chroma_client():
    """Get ChromaDB persistent client."""
    return chromadb.PersistentClient(path=CHROMA_DIR)

def get_or_create_collection(client):
    """Get or create the SQL knowledge collection."""
    return client.get_or_create_collection(
        name=COLLECTION_NAME,
        metadata={"description": "SQL question-answer pairs with chunking metadata"}
    )

# =============================================================================
# DATA LOADING
# =============================================================================

def load_datasets(data_dir="data"):
    """Load ALL CSV datasets."""
    datasets = {}
    
    files = {
        'train': 'train.csv',
        'validation': 'validation.csv',
        'test': 'test.csv'
        # 'synthetic': 'synthetic.csv'
    }
    
    for name, filename in files.items():
        filepath = os.path.join(data_dir, filename)
        if os.path.exists(filepath):
            df = pd.read_csv(filepath)
            datasets[name] = df
            print(f"  Loaded {name}: {len(df):,} rows")
        else:
            print(f"  Skipped {name}: file not found")
    
    return datasets

# =============================================================================
# KNOWLEDGE BASE BUILDING
# =============================================================================

def build_knowledge_base(data_dir="data", batch_size=500):
    """Build knowledge base with chunking strategies."""
    
    print("=" * 50)
    print("BUILDING RAG KNOWLEDGE BASE")
    print("With Chunking Strategies")
    print("=" * 50)
    
    setup_directories()
    
    # Step 1: Load data
    print(f"\n[1/5] Loading datasets...")
    datasets = load_datasets(data_dir)
    
    if not datasets:
        print("ERROR: No datasets found!")
        return None
    
    total_rows = sum(len(df) for df in datasets.values())
    print(f"  Total rows: {total_rows:,}")
    
    # Step 2: Prepare documents with chunking
    print(f"\n[2/5] Applying chunking strategies...")
    documents, metadatas, ids = prepare_documents_with_chunking(datasets)
    print(f"  Total documents: {len(documents):,}")
    
    # Show chunking stats
    complexities = [m['complexity'] for m in metadatas]
    print(f"  Complexity distribution:")
    print(f"    Simple: {complexities.count('simple'):,}")
    print(f"    Intermediate: {complexities.count('intermediate'):,}")
    print(f"    Complex: {complexities.count('complex'):,}")
    
    # Step 3: Initialize ChromaDB
    print(f"\n[3/5] Initializing ChromaDB...")
    client = get_chroma_client()
    
    try:
        client.delete_collection(COLLECTION_NAME)
        print("  Deleted existing collection")
    except:
        pass
    
    collection = get_or_create_collection(client)
    print(f"  Collection: {COLLECTION_NAME}")
    
    # Step 4: Generate embeddings and store
    print(f"\n[4/5] Generating embeddings...")
    
    total_added = 0
    
    for i in range(0, len(documents), batch_size):
        batch_docs = documents[i:i + batch_size]
        batch_meta = metadatas[i:i + batch_size]
        batch_ids = ids[i:i + batch_size]
        
        embeddings = get_embeddings_batch(batch_docs)
        
        if embeddings and embeddings[0] is not None:
            collection.add(
                documents=batch_docs,
                metadatas=batch_meta,
                ids=batch_ids,
                embeddings=embeddings
            )
            total_added += len(batch_docs)
        
        progress = min(i + batch_size, len(documents))
        pct = (progress / len(documents)) * 100
        print(f"  Progress: {progress:,}/{len(documents):,} ({pct:.1f}%)")
    
    # Step 5: Save statistics
    print(f"\n[5/5] Saving statistics...")
    stats = {
        'total_documents': total_added,
        'sources': {name: len(df) for name, df in datasets.items()},
        'collection_name': COLLECTION_NAME,
        'embedding_model': 'all-MiniLM-L6-v2',
        'chunking_strategies': [
            'sql_clause_extraction',
            'complexity_classification',
            'keyword_extraction',
            'size_categorization'
        ],
        'complexity_distribution': {
            'simple': complexities.count('simple'),
            'intermediate': complexities.count('intermediate'),
            'complex': complexities.count('complex')
        },
        'created_at': datetime.now().isoformat()
    }
    
    with open(f'{STATS_DIR}/knowledge_base_stats.json', 'w') as f:
        json.dump(stats, f, indent=2)
    
    generate_report(stats)
    
    print("\n" + "=" * 50)
    print("COMPLETE")
    print("=" * 50)
    print(f"  Documents indexed: {total_added:,}")
    print(f"  Storage: {CHROMA_DIR}/")
    
    return collection

# =============================================================================
# REPORT GENERATION
# =============================================================================

def generate_report(stats):
    """Generate knowledge base report."""
    
    report = f"""# RAG Knowledge Base Report

**Generated:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Overview

| Metric | Value |
|--------|-------|
| Total Documents | {stats['total_documents']:,} |
| Collection Name | {stats['collection_name']} |
| Embedding Model | {stats['embedding_model']} |

## Data Sources

| Source | Documents |
|--------|-----------|
"""
    
    for source, count in stats['sources'].items():
        report += f"| {source} | {count:,} |\n"
    
    report += f"""
## Chunking Strategies

1. **SQL Clause Extraction**: Identifies SELECT, FROM, WHERE, GROUP BY, etc.
2. **Complexity Classification**: Categorizes as simple/intermediate/complex
3. **Keyword Extraction**: Extracts SQL operations (JOIN, COUNT, etc.)
4. **Size Categorization**: Classifies question/SQL length

## Complexity Distribution

| Level | Count |
|-------|-------|
| Simple | {stats['complexity_distribution']['simple']:,} |
| Intermediate | {stats['complexity_distribution']['intermediate']:,} |
| Complex | {stats['complexity_distribution']['complex']:,} |

## Document Metadata Structure

Each document contains:
- `sql`: The SQL query
- `source`: Origin dataset
- `question`: Original question
- `complexity`: simple/intermediate/complex
- `sql_clauses`: Comma-separated clauses
- `keywords`: SQL keywords found
- `question_size`: short/medium/long
- `sql_size`: short/medium/long
"""
    
    with open(f'{REPORT_DIR}/knowledge_base_report.md', 'w') as f:
        f.write(report)
    
    print(f"  Report saved to {REPORT_DIR}/")

# =============================================================================
# ENTRY POINT
# =============================================================================

if __name__ == "__main__":
    build_knowledge_base(data_dir="data", batch_size=500)