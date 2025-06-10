"""Command-line utility for fetching and processing web documents."""

import sys
import json
import urllib.parse
from typing import Optional, List, Dict, Any
import click
from rich.console import Console
from rich.table import Table
from rich import box

from . import models
from . import web_parser
from . import db
from . import config

console = Console()

@click.command()
@click.argument('url')
@click.option('--save/--no-save', default=False, help='Save results to database')
@click.option('--output', '-o', type=str, help='Output file for JSON results')
def main(url: str, save: bool, output: Optional[str] = None):
    """Fetch and process a web document from URL.
    
    This utility fetches a web document (HTML or Markdown) from the provided URL,
    processes it into code constructs, and optionally saves it to the database.
    """
    try:
        # Validate URL
        parsed_url = urllib.parse.urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            console.print(f"[bold red]Invalid URL:[/] {url}")
            sys.exit(1)
            
        console.print(f"[bold blue]Fetching document from:[/] {url}")
        
        # Fetch and process document
        constructs_with_embeddings = web_parser.process_web_document(url)
        
        console.print(f"[bold green]Successfully processed document![/]")
        console.print(f"[bold]Found {len(constructs_with_embeddings)} constructs[/]")
        
        # Print table of constructs
        table = Table(
            title=f"Web Document Constructs ({len(constructs_with_embeddings)} total)",
            box=box.ROUNDED,
            show_lines=True,
            title_style="bold magenta"
        )
        
        table.add_column("Type", style="cyan")
        table.add_column("Name", style="bright_yellow")
        table.add_column("Content Length", style="green")
        
        for construct, _embedding in constructs_with_embeddings:
            table.add_row(
                construct.construct_type,
                construct.name[:50],  # Truncate long names
                str(len(construct.code))
            )
        
        console.print(table)
        
        # Save to database if requested
        if save:
            console.print("[bold yellow]Saving to database...[/]")
            db.store_constructs(constructs_with_embeddings)
            console.print("[bold green]Saved![/]")
            
        # Save to JSON file if requested
        if output:
            console.print(f"[bold yellow]Writing results to {output}...[/]")
            results = []
            for construct, embedding in constructs_with_embeddings:
                results.append({
                    "type": construct.construct_type,
                    "name": construct.name,
                    "filename": construct.filename,
                    "content_length": len(construct.code),
                    "content_preview": construct.code[:100] + "..." if len(construct.code) > 100 else construct.code,
                    "description": construct.description
                })
                
            with open(output, 'w', encoding='utf-8') as f:
                json.dump(results, f, indent=2)
                
            console.print(f"[bold green]Results written to {output}[/]")
        
    except Exception as e:
        console.print(f"[bold red]Error:[/] {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
