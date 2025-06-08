import click
from rich.console import Console
from rich.table import Table
from rich.syntax import Syntax
from rich import box
import sys
from json import dumps as json_dumps
from . import search

console = Console()

@click.command()
@click.argument('query', type=str)
@click.option(
    '--limit', '-n',
    type=int,
    default=5,
    help='Maximum number of results to return'
)
@click.option(
    '--min-similarity', '-s',
    type=float,
    default=0.7,
    help='Minimum similarity score (0-1) for matches'
)
@click.option(
    '--include-code/--no-code',
    default=True,
    help='Include code content in results'
)
@click.option(
    '--include-description/--no-description',
    default=True,
    help='Include descriptions in results'
)
@click.option(
    '--include-embedding/--no-embedding',
    default=False,
    help='Include embeddings in results'
)
@click.option(
    '--for-reconstruction/--no-reconstruction',
    default=False,
    help='Include all fields needed for CodeConstruct reconstruction'
)
@click.option(
    '--json',
    is_flag=True,
    help='Output results as JSON'
)
def main(query: str, limit: int, min_similarity: float,
         include_code: bool, include_description: bool, include_embedding: bool,
         for_reconstruction: bool, json: bool):
    """Search code constructs using natural language.
    
    Examples:
        # Basic search with default settings
        search_cli "find user by email"
        
        # Lightweight search without code
        search_cli "find user by email" --no-code
        
        # Search with embeddings for chaining
        search_cli "find user by email" --include-embedding --json
        
        # Get full data for reconstruction
        search_cli "find user by email" --for-reconstruction --json
    """
    results = search.search_code(
        query=query,
        limit=limit,
        min_similarity=min_similarity,
        include_code=include_code or json,  # Always get code if JSON output
        include_description=include_description,
        include_embedding=include_embedding,
        for_reconstruction=for_reconstruction
    )
    
    if not results:
        console.print("\n[yellow]No matches found[/yellow]\n")
        return
        
    if json:
        # Print JSON output
        console.print(json_dumps(results, indent=2, default=str))
        return
    
    # Create results table
    table = Table(
        title=f"Search Results for: {query}",
        box=box.ROUNDED,
        show_lines=True,
        title_style="bold magenta"
    )
    
    table.add_column("Score", style="cyan", justify="right")
    table.add_column("Type", style="green")
    table.add_column("Name", style="bright_yellow")
    table.add_column("File:Lines", style="blue")
    if include_description:
        table.add_column("Description", style="yellow", no_wrap=False)
    
    # Add results sorted by similarity
    for result in sorted(results, key=lambda x: x['similarity'], reverse=True):
        row = [
            f"{result['similarity']:.3f}",
            result['type'],
            result['name'],
            f"{result['filename']}:{result['line_start']}-{result['line_end']}"
        ]
        if include_description:
            row.append(result['description'])
        table.add_row(*row)
    
    console.print(table)

    # If code was requested, show it after the table for each result
    if include_code:
        for result in sorted(results, key=lambda x: x['similarity'], reverse=True):
            console.print(f"\n[bold blue]{result['filename']}[/bold blue] "
                        f"[bold cyan]({result['type']})[/bold cyan]:")
            # Use Syntax highlighting based on file extension
            language = 'python' if result['filename'].endswith('.py') else \
                      'hcl' if result['filename'].endswith(('.tf', '.tfvars')) else \
                      'default'
            syntax = Syntax(
                result['code'],
                language,
                theme="monokai",
                line_numbers=True,
                start_line=result['line_start']
            )
            console.print(syntax)
    
if __name__ == "__main__":
    main()
