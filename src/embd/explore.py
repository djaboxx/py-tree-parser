import os
from pymongo import MongoClient
from rich.console import Console
from rich.table import Table
from rich import box
from . import config

console = Console()

def connect_db():
    """Connect to MongoDB and return client"""
    try:
        client = MongoClient(config.MONGO_URI)
        # Test connection
        client.admin.command('ping')
        return client
    except Exception as e:
        console.print(f"\n[red bold]Error connecting to MongoDB:[/red bold] {str(e)}\n")
        return None

def print_constructs():
    """Print code constructs in a pretty table"""
    client = connect_db()
    if not client:
        return
        
    db = client[config.MONGO_DB]
    constructs = db[config.CONSTRUCTS_COLLECTION]
    
    count = constructs.count_documents({})
    if count == 0:
        console.print("\n[yellow]No code constructs found in database[/yellow]\n")
        return
    
    # Create table
    table = Table(
        title=f"Code Constructs ({count} total)",
        box=box.ROUNDED,
        show_lines=True,
        title_style="bold magenta"
    )
    
    table.add_column("Type", style="cyan")
    table.add_column("Name", style="bright_yellow")
    table.add_column("File", style="green")
    table.add_column("Lines", style="blue")
    table.add_column("Description", style="yellow", no_wrap=False)
    
    for construct in constructs.find().sort([("filename", 1), ("line_start", 1)]):
        table.add_row(
            construct['construct_type'].replace('_definition', ''),  # Clean up type name
            construct.get('name', 'unnamed'),
            os.path.basename(construct['filename']),
            f"{construct['line_start']}-{construct['line_end']}",
            construct.get('description', 'No description')
        )
    
    console.print(table)

def print_imports():
    """Print imports in a pretty table"""
    client = connect_db()
    if not client:
        return
        
    db = client[config.MONGO_DB]
    imports = db[config.IMPORTS_COLLECTION]
    
    count = imports.count_documents({})
    if count == 0:
        console.print("\n[yellow]No imports found in database[/yellow]\n")
        return
    
    table = Table(
        title=f"Module Imports ({count} total)",
        box=box.ROUNDED,
        show_lines=True,
        title_style="bold magenta"
    )
    
    table.add_column("Module", style="cyan")
    table.add_column("Type", style="green")
    table.add_column("File", style="blue")
    table.add_column("Repository", style="yellow")
    
    for imp in imports.find().sort([("module_name", 1)]):
        table.add_row(
            imp['module_name'],
            imp.get('import_type', 'unknown'),
            os.path.basename(imp['filename']),
            imp.get('repository', 'unknown')
        )
    
    console.print(table)

def main():
    """Main function to explore MongoDB records"""
    console.print("\n[bold blue]Exploring MongoDB Records[/bold blue]\n")
    
    print_constructs()
    print_imports()

if __name__ == "__main__":
    main()
