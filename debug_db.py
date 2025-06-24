#!/usr/bin/env python3
"""Debug script to check database contents."""

import os
from src.embd.database_manager import DatabaseManager
from sqlalchemy import text

def main():
    database_url = os.getenv('DATABASE_URL')
    if not database_url:
        print("DATABASE_URL not set")
        return
    
    db = DatabaseManager()
    
    # Get all constructs
    with db.Session() as session:
        result = session.execute(text("""
            SELECT name, construct_type, line_start, line_end, 
                   LENGTH(code) as code_length, description
            FROM code_embeddings 
            ORDER BY line_start
        """))
        
        constructs = result.fetchall()
        
    print(f"Found {len(constructs)} constructs:")
    for construct in constructs:
        print(f"  - {construct[0]} ({construct[1]}) lines {construct[2]}-{construct[3]} ({construct[4]} chars)")
        print(f"    Description: {construct[5]}")
        print()

if __name__ == "__main__":
    main()
