"""CLI tool for semantic code search."""

import click
import json
from typing import Optional
from rich.console import Console
from .. import DatabaseManager, EmbeddingGenerator

@click.command()
@click.argument('query')
@click.option('--limit', '-n', default=5, help='Maximum number of results')
@click.option('--min-similarity', '-s', default=0.7, help='Minimum similarity score')
@click.option('--type', '-t', help='Filter by construct type')
@click.option('--output', '-o', type=str, help='Output file for JSON results')
def main(query: str, limit: int = 5, min_similarity: float = 0.7, type: Optional[str] = None, output: Optional[str] = None):
    """Search for similar code using semantic similarity."""
    console = Console()
    
    # Initialize database and embedding generator
    db = DatabaseManager()
    db.init_db()  # Ensure database is initialized
    embedding_gen = EmbeddingGenerator()
    
    # Generate embedding for the query
    try:
        query_embedding = embedding_gen.generate(query)
        
        # Search for similar code
        results = db.search_similar_code(
            query_embedding=query_embedding,
            limit=limit,
            min_similarity=min_similarity,
            include_code=True,
            include_description=True,
            construct_type=type
        )
        
        # Format output
        formatted_results = []
        for result in results:
            formatted_results.append({
                'similarity': result['similarity'],
                'type': result['type'],
                'name': result.get('name', ''),
                'filename': result['filename'],
                'code': result.get('code', ''),
                'description': result.get('description', '')
            })
        
        if output:
            with open(output, 'w') as f:
                json.dump(formatted_results, f, indent=2)
        else:
            # Print results nicely with rich
            console.print("[bold green]Search Results:[/bold green]")
            for i, result in enumerate(formatted_results, 1):
                console.print(f"\n[bold cyan]{i}. {result['name']} ({result['type']})[/bold cyan]")
                console.print(f"[yellow]Similarity:[/yellow] {result['similarity']:.2f}")
                console.print(f"[yellow]File:[/yellow] {result['filename']}")
                if result.get('description'):
                    console.print(f"[yellow]Description:[/yellow] {result['description']}")
                if result.get('code'):
                    console.print("[yellow]Code:[/yellow]")
                    console.print(result['code'])
    
    except Exception as e:
        console.print(f"[bold red]Error performing search: {str(e)}[/bold red]")
        raise click.Abort()

if __name__ == '__main__':
    main()
