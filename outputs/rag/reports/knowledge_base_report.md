# RAG Knowledge Base Report

**Generated:** 2025-12-07 23:58:56

## Overview

| Metric | Value |
|--------|-------|
| Total Documents | 80,654 |
| Collection Name | sql_knowledge |
| Embedding Model | all-MiniLM-L6-v2 |

## Data Sources

| Source | Documents |
|--------|-----------|
| train | 56,355 |
| validation | 8,421 |
| test | 15,878 |

## Chunking Strategies

1. **SQL Clause Extraction**: Identifies SELECT, FROM, WHERE, GROUP BY, etc.
2. **Complexity Classification**: Categorizes as simple/intermediate/complex
3. **Keyword Extraction**: Extracts SQL operations (JOIN, COUNT, etc.)
4. **Size Categorization**: Classifies question/SQL length

## Complexity Distribution

| Level | Count |
|-------|-------|
| Simple | 80,396 |
| Intermediate | 258 |
| Complex | 0 |

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
