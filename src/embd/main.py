"""Main module for parsing and storing code constructs."""
import os
from typing import Optional
import click
from git import Repo, exc as git_exc
from . import parser
from . import db

@click.command()
@click.argument('repo_name', type=str, required=False)
@click.option('--path', '-p', type=str, default=None, help='Repository path (defaults to current directory)')
def main(repo_name: Optional[str] = None, path: Optional[str] = None):
    """Process and store code constructs from a repository.
    
    Args:
        repo_name: Name to use for the repository when storing constructs.
                  Defaults to basename of repository path.
        path: Path to repository (defaults to current directory)
    """
    # Initialize database tables and indexes
    db.init_indexes()
    
    # Get the repository path (current directory if not specified)
    repo_path = os.path.abspath(path or os.getcwd())
    
    # Default repo_name to basename of repo_path if not specified
    if not repo_name:
        repo_name = os.path.basename(repo_path)
    
    try:
        repo = Repo(repo_path)
    except git_exc.InvalidGitRepositoryError:
        print(f"\nError: Not a git repository: {repo_path}")
        print("\nPlease specify a valid git repository path with --path or run from within a git repository.")
        print("You can initialize a new git repository with 'git init' if needed.\n")
        return 1
    
    # Get all tracked Python and Markdown files
    files = parser.get_git_tracked_files(repo_path)
    
    # Process each file
    for file_path in files:
        print(f"Processing {file_path}...")
        constructs_with_embeddings, imports = parser.parse_file(file_path, repo_path, repo_name)
        
        # Store code constructs and embeddings in PostgreSQL
        db.store_constructs(constructs_with_embeddings)
        
        # Log stored constructs
        for construct, _ in constructs_with_embeddings:
            print(f"Stored {construct.construct_type} '{construct.name}' from {construct.filename}")
    
    return 0

if __name__ == "__main__":
    main()
