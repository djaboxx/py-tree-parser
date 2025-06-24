"""CLI tool for processing git repositories."""

import os
from typing import Optional, List
from rich.table import Table
import click
from git import Repo, exc as git_exc
from .base import ProcessorCLI
from ..database_manager import DatabaseManager

class RepoCLI(ProcessorCLI):
    """CLI tool for repository processing."""
    
    def __init__(self):
        """Initialize repository processor CLI."""
        super().__init__('local')

    def process_repo(self, 
                    repo_name: Optional[str] = None, 
                    path: Optional[str] = None, 
                    save: bool = False, 
                    output: Optional[str] = None,
                    list_only: bool = False,
                    include: Optional[List[str]] = None,
                    exclude: Optional[List[str]] = None) -> None:
        """Process a git repository.
        
        Args:
            repo_name: Optional repository name (defaults to directory name)
            path: Optional repository path (defaults to current directory)
            save: Whether to save results to database
            output: Optional output file for JSON results
            list_only: Only list files that would be processed
            include: List of glob patterns for files to include
            exclude: List of glob patterns for files to exclude
        """
        try:
            # Determine repository path and name
            repo_path = os.path.abspath(path if path else os.getcwd())
            if not repo_name:
                repo_name = os.path.basename(repo_path)

            # Validate repository
            try:
                repo = Repo(repo_path)
                if repo.bare:
                    raise click.UsageError("Cannot process bare repository")
            except git_exc.InvalidGitRepositoryError:
                raise click.UsageError("Not a git repository")

            self.console.print(f"[bold cyan]Processing repository:[/bold cyan] {repo_name}")
            self.console.print(f"[bold cyan]Path:[/bold cyan] {repo_path}")
            
            # Create processor with patterns
            processor = self.create_processor(
                repo_path=repo_path,
                include_patterns=include,
                exclude_patterns=exclude
            )
            
            if list_only:
                # Create a table to show files
                table = Table(title="Files to Process")
                table.add_column("Status", style="cyan", no_wrap=True)
                table.add_column("Path", style="white")
                
                processable = processor.list_processable_files()
                skipped = [
                    (f, os.path.relpath(f, repo_path)) 
                    for f in processor.get_tracked_files() 
                    if not processor.should_process_file(f)
                ]
                
                # Add processable files
                for _, rel_path in sorted(processable):
                    table.add_row("INCLUDE", rel_path)
                
                # Add skipped files
                for _, rel_path in sorted(skipped):
                    table.add_row("EXCLUDE", rel_path, style="dim")
                
                self.console.print(table)
                self.console.print(f"\nTotal files: {len(processable)} included, {len(skipped)} excluded")
                return
            
            # Process the repository
            self.console.print("\n[bold cyan]Starting processing...[/bold cyan]")
            constructs, _ = processor.process()
            print(f"\nCLI DEBUG: Received {len(constructs)} constructs from processor.process()")
            self.console.print(f"[bold cyan]Processing complete. Found {len(constructs)} constructs.[/bold cyan]\n")
            
            # Debug: show constructs
            for i, (construct, _) in enumerate(constructs):
                print(f"CLI DEBUG: {i+1}. {construct.name} ({construct.construct_type}) lines {construct.line_start}-{construct.line_end}")
            
            # Add repository info to constructs
            for construct, _ in constructs:
                construct.repository = repo_name
            
            print(f"\nCLI DEBUG: After adding repo info, still have {len(constructs)} constructs")
            
            if not constructs:
                self.console.print("[yellow]No code constructs found.[/yellow]")
                return
                
            # Save to database if requested
            if save:
                print(f"CLI DEBUG: About to save {len(constructs)} constructs to database")
                db = DatabaseManager()
                db.init_db()
                self.save_results(constructs, db)
                
            # Export to file if requested
            if output:
                self.export_results(constructs, output)
                
            self.console.print("\n[bold green]Processing completed successfully![/bold green]")
                
        except click.UsageError:
            raise
        except Exception as e:
            self.console.print(f"[bold red]Error processing repository: {str(e)}[/bold red]")
            raise click.Abort()

@click.command()
@click.argument('repo_name', type=str, required=False)
@click.option('--path', '-p', type=str, default=None, help='Repository path (defaults to current directory)')
@click.option('--save/--no-save', default=False, help='Save results to database')
@click.option('--output', '-o', type=str, help='Output file for JSON results')
@click.option('--list-files', is_flag=True, help='Only list files that would be processed')
@click.option('--include', multiple=True, help='Glob patterns for files to include (can be specified multiple times)')
@click.option('--exclude', multiple=True, help='Glob patterns for files to exclude (can be specified multiple times)')
def main(repo_name: Optional[str] = None, path: Optional[str] = None, save: bool = False, 
         output: Optional[str] = None, list_files: bool = False,
         include: tuple[str, ...] = (), exclude: tuple[str, ...] = ()):
    """Process a git repository.
    
    Examples:
        \b
        # List files that would be processed
        embd-repo --list-files
        
        # Only process Python files
        embd-repo --include "**/*.py"
        
        # Exclude test files
        embd-repo --exclude "**/*test*.py" --exclude "**/tests/**"
        
        # Preview filtered files
        embd-repo --list-files --include "**/*.py" --exclude "**/tests/**"
    """
    cli = RepoCLI()
    cli.process_repo(
        repo_name=repo_name,
        path=path,
        save=save,
        output=output,
        list_only=list_files,
        include=list(include) if include else None,
        exclude=list(exclude) if exclude else None
    )

if __name__ == '__main__':
    main()
