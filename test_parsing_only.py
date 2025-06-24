#!/usr/bin/env python3
"""Test tree-sitter parsing without embedding generation."""

import sys
import os

# Add the src directory to the path
sys.path.append('/Users/darnold/git/embed/src')

from embd.processors.local import LocalFileProcessor

def test_parsing_only():
    """Test tree-sitter parsing without embeddings."""
    print("=" * 60)
    print("TESTING TREE-SITTER PARSING (NO EMBEDDINGS)")
    print("=" * 60)
    
    # Check which module is being loaded
    print(f"DEBUG: LocalFileProcessor loaded from: {LocalFileProcessor.__module__}")
    print(f"DEBUG: LocalFileProcessor file: {LocalFileProcessor.__file__ if hasattr(LocalFileProcessor, '__file__') else 'N/A'}")
    
    # Create processor WITHOUT embedding generator
    processor = LocalFileProcessor('/Users/darnold/git/embed')
    processor.embedding_generator = None  # Disable embedding generation
    
    # Test on models.py which should have classes
    file_path = '/Users/darnold/git/embed/src/embd/models.py'
    print(f"Processing file: {file_path}")
    
    print("DEBUG: About to call process_file")
    
    # Let's inspect the method directly
    import inspect
    print(f"DEBUG: process_file method source (first 200 chars): {inspect.getsource(processor.process_file)[:200]}...")
    
    # Process the file
    constructs, imports = processor.process_file(file_path)
    print("DEBUG: process_file returned")
    
    print(f"\nFOUND {len(constructs)} CONSTRUCTS:")
    for i, (construct, embedding) in enumerate(constructs):
        print(f"  {i+1}. {construct.name} ({construct.construct_type}) lines {construct.line_start}-{construct.line_end}")
        print(f"      Code snippet: {construct.code[:100]}...")
    
    print(f"\nFOUND {len(imports)} IMPORTS:")
    for i, import_obj in enumerate(imports):
        print(f"  {i+1}. {import_obj.module_name} ({import_obj.import_type}) line {import_obj.line_start}")

if __name__ == '__main__':
    test_parsing_only()
