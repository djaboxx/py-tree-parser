"""Main module for parsing and storing code constructs."""
import os
from typing import Optional
import click
from rich.console import Console
from git import Repo, exc as git_exc
from .database_manager import DatabaseManager
from .processors.local import LocalFileProcessor
from .embedding import EmbeddingGenerator

@click.command()
@click.argument('repo_name', type=str, required=False)
@click.option('--path', '-p', type=str, default=None, help='Repository path (defaults to current directory)')
@click.option('--whole-file', '-w', is_flag=True, help='Embed complete files instead of individual constructs')
def main(repo_name: Optional[str] = None, path: Optional[str] = None, whole_file: bool = False):
    """Process and store code constructs from a repository.
    
    Args:
        repo_name: Name to use for the repository when storing constructs.
                  Defaults to basename of repository path.
        path: Path to repository (defaults to current directory)
        whole_file: If True, embed complete files instead of individual constructs
    """
    console = Console()
    
    console = Console()
    try:
        # Initialize components
        console.print("[bold cyan]Initializing...[/bold cyan]")
        db_manager = DatabaseManager()
        db_manager.init_db()
        embedding_gen = EmbeddingGenerator()
        
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

        console.print(f"[bold green]Processing repository:[/bold green] {repo_name}")
        console.print(f"[bold green]Path:[/bold green] {repo_path}")

        # Initialize processor
        processor = LocalFileProcessor(
            repo_path=repo_path,
            embedding_generator=embedding_gen
        )
        
        # Process repository
        constructs_with_embeddings, imports = processor.process()
        
        # Add repository info to constructs
        for construct, _ in constructs_with_embeddings:
            construct.repository = repo_name
        
        # Store results
        if constructs_with_embeddings:
            console.print("[bold cyan]Storing results in database...[/bold cyan]")
            db_manager.store_constructs(constructs_with_embeddings)
            
        console.print("\n[bold green]Processing completed successfully![/bold green]")
            
    except click.UsageError:
        raise
    except Exception as e:
        console.print(f"\n[bold red]Error processing repository:[/bold red] {str(e)}")
        raise click.Abort()

if __name__ == '__main__':
    main()
