#!/usr/bin/env python3
"""Simple test script to verify tree-sitter processing without Rich UI interference."""

import sys
import os

# Add the src directory to the path
sys.path.append('/Users/darnold/git/embed/src')

from embd.processors.local import LocalFileProcessor
from embd.embedding import EmbeddingGenerator
from embd.database_manager import DatabaseManager

def test_processing():
    """Test the processor directly."""
    print("=" * 60)
    print("TESTING TREE-SITTER PROCESSING")
    print("=" * 60)
    
    # Create processor and embedding generator
    processor = LocalFileProcessor('/Users/darnold/git/embed')
    embedding_generator = EmbeddingGenerator()
    processor.embedding_generator = embedding_generator
    
    # Test on models.py which should have classes
    file_path = '/Users/darnold/git/embed/src/embd/models.py'
    print(f"Processing file: {file_path}")
    
    # Process the file
    constructs, imports = processor.process_file(file_path)
    
    print(f"\nFOUND {len(constructs)} CONSTRUCTS:")
    for i, (construct, embedding) in enumerate(constructs):
        print(f"  {i+1}. {construct.name} ({construct.construct_type}) lines {construct.line_start}-{construct.line_end}")
    
    print(f"\nFOUND {len(imports)} IMPORTS:")
    for i, import_obj in enumerate(imports):
        print(f"  {i+1}. {import_obj.module_name} ({import_obj.import_type})")
    
    # Now test the full process() method
    print("\n" + "=" * 60)
    print("TESTING FULL PROCESS() METHOD")
    print("=" * 60)
    
    # Reset processed files
    processor._processed_files = set()
    processor.include_patterns = ["src/embd/models.py"]  # Only process models.py
    
    all_constructs, all_imports = processor.process()
    
    print(f"\nFULL PROCESS FOUND {len(all_constructs)} CONSTRUCTS:")
    for i, (construct, embedding) in enumerate(all_constructs):
        print(f"  {i+1}. {construct.name} ({construct.construct_type}) lines {construct.line_start}-{construct.line_end}")
    
    print(f"\nFULL PROCESS FOUND {len(all_imports)} IMPORTS:")
    for i, import_obj in enumerate(all_imports):
        print(f"  {i+1}. {import_obj.module_name} ({import_obj.import_type})")
        
    # Now save to database
    print("\n" + "=" * 60)
    print("TESTING DATABASE SAVE")
    print("=" * 60)
    
    # Set the DATABASE_URL
    os.environ['DATABASE_URL'] = 'postgresql://postgres:postgres@localhost:5432/code_embed'
    
    # Initialize database
    db = DatabaseManager()
    db.init_db()
    
    # Save constructs (disable progress bar)
    db.store_constructs(all_constructs, show_progress=False)
    
    print(f"Saved {len(all_constructs)} constructs to database")

if __name__ == '__main__':
    test_processing()
