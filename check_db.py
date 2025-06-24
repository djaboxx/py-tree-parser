"""Script to check the database schema and content."""
from sqlalchemy import inspect, text
from rich.console import Console
from rich.table import Table
from embd.database_manager import DatabaseManager
from embd.models import CodeEmbedding

# Initialize the database manager and console
db = DatabaseManager()
console = Console()

def check_db_state():
    """Check and report on database state."""
    # Get inspector
    inspector = inspect(db.engine)

    # Get all table names
    table_names = inspector.get_table_names()
    if not table_names:
        console.print("[yellow]No tables found in database[/yellow]")
        return

    # Create a table for displaying schema info
    schema_table = Table(title="Database Schema")
    schema_table.add_column("Table", style="cyan")
    schema_table.add_column("Column", style="green")
    schema_table.add_column("Type", style="blue")
    schema_table.add_column("Nullable", style="yellow")

    # Get schema info for each table
    for table_name in table_names:
        columns = inspector.get_columns(table_name)
        for column in columns:
            schema_table.add_row(
                table_name,
                column['name'],
                str(column['type']),
                "✓" if column.get('nullable') else "✗"
            )

    console.print(schema_table)
    
    # Show row counts
    counts_table = Table(title="\nTable Row Counts")
    counts_table.add_column("Table", style="cyan")
    counts_table.add_column("Row Count", style="green", justify="right")
    
    with db.engine.connect() as conn:
        for table in table_names:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table}")).scalar() or 0
            counts_table.add_row(table, str(result))
    
    console.print(counts_table)
    
    # Check vector dimensions for code_embeddings
    if 'code_embeddings' in table_names:
        console.print("\n[cyan]Vector Embedding Details:[/cyan]")
        with db.engine.connect() as conn:
            # Check if there are any embeddings
            result = conn.execute(text(
                "SELECT embedding FROM code_embeddings LIMIT 1"
            )).first()
            
            if result:
                vector = result[0]
                console.print(f"[green]✓ Vector dimension:[/green] {len(vector)}")
            else:
                console.print("[yellow]No embeddings found to check dimensions[/yellow]")
            
            # Check pgvector extension
            result = conn.execute(text(
                "SELECT installed_version FROM pg_available_extensions WHERE name = 'vector'"
            )).first()
            
            if result:
                console.print(f"[green]✓ pgvector extension:[/green] version {result[0]}")
            else:
                console.print("[red]✗ pgvector extension not available[/red]")

if __name__ == '__main__':
    check_db_state()
