"""CLI tool for processing git repositories."""

import click
from pathlib import Path
from typing import Optional
from .. import LocalFileProcessor, DatabaseManager

@click.command()
@click.argument('repo_path', type=click.Path(exists=True, file_okay=False, dir_okay=True))
@click.option('--save/--no-save', default=False, help='Save results to database')
@click.option('--output', '-o', type=str, help='Output file for JSON results')
def main(repo_path: str, save: bool, output: Optional[str] = None):
    """Process a git repository."""
    processor = LocalFileProcessor(repo_path)
    constructs, imports = processor.process()
    
    if save:
        db = DatabaseManager()
        db.init_db()  # Ensure database is initialized
        db.store_constructs(constructs)
            
    if output:
        import json
        results = []
        for construct, _ in constructs:
            results.append({
                "type": construct.construct_type,
                "name": construct.name,
                "filename": construct.filename,
                "description": construct.description
            })
            
        with open(output, 'w') as f:
            json.dump(results, f, indent=2)

if __name__ == '__main__':
    main()
