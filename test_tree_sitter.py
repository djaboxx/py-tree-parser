#!/usr/bin/env python3
"""Test tree-sitter parsing."""

import sys
from tree_sitter import Parser
from tree_sitter_languages import get_language

def test_tree_sitter(file_path):
    print(f"Testing tree-sitter with {file_path}")
    
    # Read file
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    print(f"File content length: {len(content)} characters")
    
    # Initialize parser
    try:
        language = get_language('python')
        parser = Parser()
        parser.set_language(language)
        print("Parser initialized successfully")
    except Exception as e:
        print(f"Parser initialization failed: {e}")
        return
    
    # Parse content
    try:
        tree = parser.parse(content.encode())
        if not tree or not tree.root_node:
            print("Failed to parse file")
            return
        print(f"Parse successful! Root node type: {tree.root_node.type}")
        print(f"Number of children: {len(tree.root_node.children)}")
        
        # List top-level constructs
        for i, child in enumerate(tree.root_node.children):
            print(f"  Child {i}: {child.type}")
            if child.type in ['class_definition', 'function_definition']:
                name_node = child.child_by_field_name('name')
                if name_node:
                    name = content[name_node.start_byte:name_node.end_byte]
                    print(f"    Name: {name}")
                    
    except Exception as e:
        print(f"Parse failed: {e}")

if __name__ == '__main__':
    if len(sys.argv) != 2:
        print("Usage: python test_tree_sitter.py <file_path>")
        sys.exit(1)
    
    test_tree_sitter(sys.argv[1])
