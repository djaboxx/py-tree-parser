"""CLI tool for resetting the database."""

import click
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from sqlalchemy import inspect, text
from ..database_manager import DatabaseManager
from .. import models

@click.command()
@click.option('--force', is_flag=True, help='Force reset without confirmation')
@click.option('--verify', is_flag=True, help='Verify tables are empty after reset')
def main(force: bool, verify: bool):
    """Reset the database schema for new embedding dimensions.
    
    This tool will:
    1. Drop all existing tables
    2. Recreate tables with current schema
    3. Initialize vector similarity indexes
    """
    console = Console()
    
    if not force:
        console.print('[yellow]Warning:[/yellow] This will delete all existing data including:')
        console.print('  • All code embeddings')
        console.print('  • All vector indexes')
        console.print('  • All related metadata\n')
        if not click.confirm('Are you sure you want to continue?'):
            console.print('[red]Aborted[/red]')
            return
    
    db = DatabaseManager()
    
    try:
        # Get inspector and all table names
        inspector = inspect(db.engine)
        table_names = inspector.get_table_names()
        
        if not table_names:
            console.print('[yellow]No existing tables found[/yellow]')
        else:
            # Drop existing tables in reverse order to handle dependencies
            with Progress(
                SpinnerColumn(),
                TextColumn("[progress.description]{task.description}"),
                console=console
            ) as progress:
                task = progress.add_task("[cyan]Dropping existing tables...", total=len(table_names))
                
                with db.engine.connect() as conn:
                    trans = conn.begin()
                    try:
                        for table in reversed(table_names):
                            conn.execute(text(f'DROP TABLE IF EXISTS {table} CASCADE;'))
                            progress.advance(task)
                        trans.commit()
                    except Exception as e:
                        trans.rollback()
                        raise click.ClickException(f"Error dropping tables: {str(e)}")
        
        # Reinitialize database
        console.print('[cyan]Reinitializing database schema...[/cyan]')
        db.init_db()
        
        if verify:
            console.print('\n[cyan]Verifying database state:[/cyan]')
            inspector = inspect(db.engine)
            current_tables = inspector.get_table_names()
            
            if set(current_tables) != set(models.Base.metadata.tables.keys()):
                missing_tables = set(models.Base.metadata.tables.keys()) - set(current_tables)
                console.print(f'[red]Warning: Missing tables: {", ".join(missing_tables)}[/red]')
            else:
                # Check that tables are empty
                with db.engine.connect() as conn:
                    for table in current_tables:
                        result = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar() or 0
                        if result > 0:
                            console.print(f'[red]Warning: Table {table} contains {result} rows[/red]')
                        else:
                            console.print(f'[green]Table {table} verified empty[/green]')
        
        console.print('\n[bold green]Database reset completed successfully![/bold green]')
    
    except Exception as e:
        console.print(f'\n[bold red]Error during database reset:[/bold red] {str(e)}')
        raise click.Abort()

if __name__ == '__main__':
    main()
