#!/usr/bin/env python3
"""Test script to debug tree-sitter chunking without Rich UI interference."""

import sys
import os
sys.path.append('/Users/darnold/git/embed')

from src.embd.processors.local import LocalFileProcessor
from src.embd.embedding import EmbeddingGenerator
from src.embd.database_manager import DatabaseManager

def main():
    print("=== Testing Tree-Sitter Chunking ===")
    
    # Create processor
    processor = LocalFileProcessor(
        '/Users/darnold/git/embed',
        include_patterns=['src/embd/models.py']
    )
    
    # Create embedding generator (but we'll bypass it for speed)
    embedding_gen = EmbeddingGenerator()
    processor.embedding_generator = embedding_gen
    
    print("Processing models.py file...")
    
    # Process directly
    constructs, imports = processor.process()
    
    print(f"\nFound {len(constructs)} constructs:")
    for i, (construct, embedding) in enumerate(constructs):
        print(f"  {i+1}. {construct.name} ({construct.construct_type}) lines {construct.line_start}-{construct.line_end}")
    
    print(f"\nFound {len(imports)} imports")
    
    # Test database saving
    print("\nTesting database save...")
    db = DatabaseManager()
    db.init_db()
    
    # Add repository info
    for construct, _ in constructs:
        construct.repository = "test_repo"
    
    # Save without progress bars
    print(f"Saving {len(constructs)} constructs to database...")
    db._store_constructs_simple(constructs)
    print("Save completed!")
    
    # Verify what was saved
    with db.Session() as session:
        from sqlalchemy import text
        result = session.execute(text("""
            SELECT name, construct_type, line_start, line_end 
            FROM code_embeddings 
            ORDER BY line_start
        """))
        saved_constructs = result.fetchall()
    
    print(f"\nVerification - Found {len(saved_constructs)} saved constructs:")
    for construct in saved_constructs:
        print(f"  - {construct[0]} ({construct[1]}) lines {construct[2]}-{construct[3]}")

if __name__ == "__main__":
    main()
