"""Base classes for processor CLI tools."""

import click
from typing import Optional
import json
from rich.console import Console
from ..database_manager import DatabaseManager
from ..embedding import EmbeddingGenerator
from ..processors import get_processor

class ProcessorCLI:
    """Base class for processor CLI tools."""
    
    def __init__(self, processor_name: str):
        """Initialize CLI with processor name.
        
        Args:
            processor_name: Name of the registered processor to use
        """
        self.processor_name = processor_name
        self.console = Console()
        self.processor_class = get_processor(processor_name)
        
    def create_processor(self, **kwargs):
        """Create processor instance with given arguments.
        
        Args:
            **kwargs: Arguments to pass to the processor constructor.
                     For LocalFileProcessor, this can include:
                     - repo_path: Path to git repository
                     - include_patterns: List of glob patterns to include
                     - exclude_patterns: List of glob patterns to exclude
        """
        embedding_gen = EmbeddingGenerator()
        return self.processor_class(embedding_generator=embedding_gen, **kwargs)
        
    def save_results(self, constructs, db_manager: DatabaseManager) -> None:
        """Save constructs to database."""
        try:
            self.console.print("[bold cyan]Saving results to database...[/bold cyan]")
            print(f"DEBUG: About to save {len(constructs)} constructs:")
            for i, (construct, _) in enumerate(constructs):
                print(f"  {i+1}. {construct.name} ({construct.construct_type}) lines {construct.line_start}-{construct.line_end}")
            db_manager.store_constructs(constructs, show_progress=False)
            self.console.print("[bold green]Results saved successfully![/bold green]")
        except Exception as e:
            self.console.print(f"[bold red]Error saving results: {str(e)}[/bold red]")
            raise click.Abort()
            
    def export_results(self, constructs, output_file: str) -> None:
        """Export results to JSON file."""
        try:
            self.console.print(f"[bold cyan]Exporting results to {output_file}...[/bold cyan]")
            results = []
            for construct, _ in constructs:
                results.append({
                    "type": construct.construct_type,
                    "name": construct.name,
                    "filename": construct.filename,
                    "description": construct.description
                })
            
            with open(output_file, 'w') as f:
                json.dump(results, f, indent=2)
                
            self.console.print("[bold green]Results exported successfully![/bold green]")
        except Exception as e:
            self.console.print(f"[bold red]Error exporting results: {str(e)}[/bold red]")
            raise click.Abort()
