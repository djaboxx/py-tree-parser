"""CLI tool for processing web documents."""

import click
from typing import Optional
from rich.console import Console
from ..database_manager import DatabaseManager
from .base import ProcessorCLI

class WebCLI(ProcessorCLI):
    """CLI tool for web document processing."""
    
    def __init__(self):
        """Initialize web processor CLI."""
        super().__init__('web')

    def process_url(self, url: str, save: bool = False, output: Optional[str] = None) -> None:
        """Process a web URL.
        
        Args:
            url: URL to process
            save: Whether to save results to database
            output: Optional output file for JSON results
        """
        try:
            self.console.print(f"[bold cyan]Processing URL:[/bold cyan] {url}")
            
            # Create and run processor
            processor = self.create_processor(url=url)
            constructs, _ = processor.process()
            
            if not constructs:
                self.console.print("[yellow]No code constructs found.[/yellow]")
                return
                
            # Save to database if requested
            if save:
                db = DatabaseManager()
                db.init_db()
                self.save_results(constructs, db)
                
            # Export to file if requested
            if output:
                self.export_results(constructs, output)
                
            self.console.print("\n[bold green]Processing completed successfully![/bold green]")
                
        except Exception as e:
            self.console.print(f"[bold red]Error processing URL: {str(e)}[/bold red]")
            raise click.Abort()

@click.command()
@click.argument('url')
@click.option('--save/--no-save', default=False, help='Save results to database')
@click.option('--output', '-o', type=str, help='Output file for JSON results')
def main(url: str, save: bool, output: Optional[str] = None):
    """Process a web document from URL."""
    cli = WebCLI()
    cli.process_url(url, save, output)

if __name__ == '__main__':
    main()
