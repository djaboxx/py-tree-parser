"""Command-line utility for fetching and processing web documents."""

import sys
import json
import os
import urllib.parse
import importlib
import asyncio
from typing import Optional, List, Dict, Any, Tuple
import click
from rich.console import Console
from rich.table import Table
from rich import box

from . import models
from . import web_parser
from . import db
from . import config

console = Console()

def try_import_rag_web_processor():
    """Try to import the enhanced web processor from the rag module."""
    try:
        # Find the rag directory relative to this file
        rag_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../../rag'))
        if not os.path.exists(rag_dir):
            return None
            
        sys.path.insert(0, rag_dir)
        
        # Try importing the module
        spec = importlib.util.find_spec('src.rag.web_processor')
        if spec is None:
            return None
            
        # Import the module
        rag_web_processor = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(rag_web_processor)
        return rag_web_processor
    except Exception as e:
        console.print(f"[yellow]Error importing rag web processor: {str(e)}[/]")
        return None

@click.command()
@click.argument('url')
@click.option('--save/--no-save', default=False, help='Save results to database')
@click.option('--output', '-o', type=str, help='Output file for JSON results')
@click.option('--max-tokens', type=int, default=4000, help='Maximum tokens per section (default: 4000)')
@click.option('--chunk-overlap', type=int, default=200, help='Token overlap between chunks (default: 200)')
@click.option('--max-sections', type=int, default=100, help='Maximum number of sections to return (default: 100)')
@click.option('--as-markdown/--as-html', default=False, help='Force processing as Markdown')
@click.option('--use-advanced-chunking/--use-basic-processing', default=True, 
              help='Use advanced chunking for large documents (default: True)')
def main(url: str, save: bool, output: Optional[str] = None, max_tokens: int = 4000, 
         chunk_overlap: int = 200, max_sections: int = 100, as_markdown: bool = False,
         use_advanced_chunking: bool = True):
    """Fetch and process a web document from URL.
    
    This utility fetches a web document (HTML or Markdown) from the provided URL,
    processes it into code constructs with automatic chunking for large documents,
    and optionally saves it to the database.
    """
    try:
        # Validate URL
        parsed_url = urllib.parse.urlparse(url)
        if not parsed_url.scheme or not parsed_url.netloc:
            console.print(f"[bold red]Invalid URL:[/] {url}")
            sys.exit(1)
            
        console.print(f"[bold blue]Fetching document from:[/] {url}")
        console.print(f"[dim]Using parameters: max_tokens={max_tokens}, chunk_overlap={chunk_overlap}, max_sections={max_sections}[/]")
        
        # Initialize constructs list
        constructs_with_embeddings = []
        
        # Try enhanced processing if requested
        if use_advanced_chunking:
            try:
                # Try to import the RAG web processor
                rag_web_processor = try_import_rag_web_processor()
                
                if rag_web_processor and hasattr(rag_web_processor, 'fetch_web_document'):
                    console.print("[yellow]Using enhanced web document processing with chunking...[/]")
                    
                    # Call the enhanced web processor that handles chunking
                    processed_doc = asyncio.run(rag_web_processor.fetch_web_document(
                        url=url,
                        extract_code_blocks=True,
                        process_as_markdown=as_markdown,
                        max_tokens_per_section=max_tokens,
                        chunk_overlap=chunk_overlap,
                        max_sections=max_sections
                    ))
                    
                    # Convert back into constructs for compatibility with the original flow
                    constructs_with_embeddings = []
                    
                    # Determine document type for construct typing
                    doc_type = processed_doc['document_type']  # 'html' or 'markdown'
                    
                    # Use a placeholder git commit hash since it's required but not relevant for web docs
                    git_commit = "web-document-fetch"
                    
                    # Main document construct
                    main_construct = models.CodeConstruct(
                        name=processed_doc["title"],
                        code=processed_doc["content"],
                        construct_type=f"web_{doc_type}_document",
                        filename=url,
                        repository="",
                        git_commit=git_commit,
                        line_start=1,
                        line_end=processed_doc["content"].count("\n") + 1,
                        embedding=[],
                        description=f"Web document: {processed_doc['title']}"
                    )
                    main_embedding = web_parser.parser.get_embedding(
                        processed_doc["content"], 
                        f"Web document: {processed_doc['title']}"
                    )
                    constructs_with_embeddings.append((main_construct, main_embedding))
                    
                    # Process sections
                    for i, section in enumerate(processed_doc["sections"][:max_sections]):
                        # Extract title and content correctly
                        if isinstance(section, dict):
                            section_title = section.get("title", f"Section {i+1}")
                            section_content = section.get("content", "")
                        else:
                            # Handle if it's a model object with attributes
                            section_title = getattr(section, "title", f"Section {i+1}")
                            section_content = getattr(section, "content", "")
                        
                        section_construct = models.CodeConstruct(
                            name=section_title,
                            code=section_content,
                            construct_type=f"web_{doc_type}_section",
                            filename=url,
                            repository="",
                            git_commit=git_commit,
                            line_start=1,
                            line_end=section_content.count("\n") + 1,
                            embedding=[],
                            description=f"Web document section: {section_title}"
                        )
                        section_embedding = web_parser.parser.get_embedding(
                            section_content, 
                            f"Web document section: {section_title}"
                        )
                        constructs_with_embeddings.append((section_construct, section_embedding))
                    
                    # Process code blocks
                    for i, block in enumerate(processed_doc["code_blocks"]):
                        # Extract language and code correctly
                        if isinstance(block, dict):
                            block_lang = block.get("language", "unknown")
                            block_code = block.get("code", "")
                        else:
                            # Handle if it's a model object with attributes
                            block_lang = getattr(block, "language", "unknown")
                            block_code = getattr(block, "code", "")
                        
                        code_construct = models.CodeConstruct(
                            name=f"Code block {i+1} ({block_lang})",
                            code=block_code,
                            construct_type=f"web_{doc_type}_code_block",
                            filename=url,
                            repository="",
                            git_commit=git_commit,
                            line_start=1,
                            line_end=block_code.count("\n") + 1,
                            embedding=[],
                            description=f"Code block in {block_lang}"
                        )
                        code_embedding = web_parser.parser.get_embedding(
                            block_code, 
                            f"Code block in {block_lang}"
                        )
                        constructs_with_embeddings.append((code_construct, code_embedding))
                    
                    # Update message with section info
                    console.print(f"[green]Enhanced processing with chunking produced {len(processed_doc['sections'])} sections[/]")
                    
                    # Skip the fallback since we processed successfully
                    use_fallback = False
                else:
                    use_fallback = True
            except Exception as e:
                console.print(f"[yellow]Error with enhanced processing: {str(e)}[/]")
                use_fallback = True
        else:
            use_fallback = True
            
        # Fall back to the original processor if needed
        if use_fallback:
            console.print("[yellow]Using original web document processing (no chunking)...[/]")
            constructs_with_embeddings = web_parser.process_web_document(url)
        
        # Display results
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
