"""CLI tool for processing web documents."""

import click
from typing import Optional
from rich.console import Console
from .. import WebProcessor, DatabaseManager, EmbeddingGenerator

@click.command()
@click.argument('url')
@click.option('--save/--no-save', default=False, help='Save results to database')
@click.option('--output', '-o', type=str, help='Output file for JSON results')
def main(url: str, save: bool, output: Optional[str] = None):
    """Process a web document from URL."""
    console = Console()
    
    try:
        # Initialize embedding generator
        console.print("[bold cyan]Initializing...[/bold cyan]")
        embedding_gen = EmbeddingGenerator()
        processor = WebProcessor(url, embedding_generator=embedding_gen)
        
        # Process the web document
        console.print(f"[bold cyan]Processing {url}...[/bold cyan]")
        constructs, _ = processor.process()
        
        # Store results if requested
        if save:
            console.print("[bold cyan]Saving to database...[/bold cyan]")
            db = DatabaseManager()
            db.init_db()  # Ensure database is initialized
            db.store_constructs(constructs)
        
        # Generate output
        results = []
        for construct, embedding in constructs:
            results.append({
                "type": construct.construct_type,
                "name": construct.name,
                "filename": construct.filename,
                "description": construct.description
            })
            
        # Save or display results
        if output:
            console.print(f"[bold cyan]Saving results to {output}...[/bold cyan]")
            import json
            with open(output, 'w') as f:
                json.dump(results, f, indent=2)
        else:
            # Print results nicely
            console.print("\n[bold green]Extracted Code Constructs:[/bold green]")
            for i, result in enumerate(results, 1):
                console.print(f"\n[bold cyan]{i}. {result['name']} ({result['type']})[/bold cyan]")
                console.print(f"[yellow]File:[/yellow] {result['filename']}")
                if result['description']:
                    console.print(f"[yellow]Description:[/yellow] {result['description']}")
        
        console.print("\n[bold green]Processing completed successfully![/bold green]")
            
    except Exception as e:
        console.print(f"[bold red]Error processing web document: {str(e)}[/bold red]")
        raise click.Abort()

if __name__ == '__main__':
    main()
