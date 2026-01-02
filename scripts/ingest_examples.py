"""
Script to ingest NL-SQL example pairs into ChromaDB
Run this to populate the RAG knowledge base
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from rag.knowledge_base import build_knowledge_base

def main():
    """
    Ingest examples from data directory into ChromaDB.
    Assumes you have example files in data/ folder.
    """
    print("=" * 60)
    print("INGESTING EXAMPLES INTO CHROMADB")
    print("=" * 60)
    
    data_dir = "data"
    
    if not os.path.exists(data_dir):
        print(f"❌ Data directory not found: {data_dir}")
        print("   Please create data/ folder with SQL example files")
        return
    
    try:
        build_knowledge_base(
            data_dir=data_dir,
            batch_size=500,
            persist_directory="chromadb_data"
        )
        print("\n✅ ChromaDB ingestion complete!")
        print("   Knowledge base ready for RAG retrieval")
        
    except Exception as e:
        print(f"\n❌ Ingestion failed: {e}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
