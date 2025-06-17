"""Enhanced command-line utility for fetching and processing web documents."""

import sys
import json
import os
import urllib.parse
import importlib.util
import asyncio
from typing import Optional, List, Dict, Any, Tuple
import click
from rich.console import Console
from rich.table import Table
from rich import box

from . import models
from . import web_parser
from . import parser
from . import db

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

def process_with_enhanced_chunking(
    url: str, 
    max_tokens: int, 
    chunk_overlap: int, 
    max_sections: int,
    process_as_markdown: bool
) -> Optional[Tuple[List[Tuple[models.CodeConstruct, List[float]]], Dict]]:
    """Process a URL using the enhanced chunking from rag module."""
    rag_web_processor = try_import_rag_web_processor()
    if not rag_web_processor:
        return None
        
    try:
        console.print("[yellow]Using enhanced web document processing with chunking...[/]")
        
        # Get the fetch_web_document function
        fetch_web_document = getattr(rag_web_processor, 'fetch_web_document', None)
        if not fetch_web_document:
            return None
            
        # Call the enhanced web processor
        processed_doc = asyncio.run(fetch_web_document(
            url=url,
            extract_code_blocks=True,
            process_as_markdown=process_as_markdown,
            max_tokens_per_section=max_tokens,
            chunk_overlap=chunk_overlap,
            max_sections=max_sections
        ))
        
        # Convert the processed document into constructs
        constructs_with_embeddings = []
        
        # Determine document type
        doc_type = processed_doc['document_type']  # 'html' or 'markdown'
        git_commit = "web-document-fetch"  # Placeholder
        
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
        
        # Generate embedding
        main_embedding = parser.get_embedding(processed_doc["content"], f"Web document: {processed_doc['title']}")
        constructs_with_embeddings.append((main_construct, main_embedding))
        
        # Process sections
        for i, section in enumerate(processed_doc["sections"]):
            section_title = section.get("title", f"Section {i+1}")
            section_content = section.get("content", "")
            
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
            
            section_embedding = parser.get_embedding(section_content, f"Web document section: {section_title}")
            constructs_with_embeddings.append((section_construct, section_embedding))
        
        # Process code blocks
        for i, block in enumerate(processed_doc["code_blocks"]):
            block_lang = block.get("language", "unknown")
            block_code = block.get("code", "")
            
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
            
            code_embedding = parser.get_embedding(block_code, f"Code block in {block_lang}")
            constructs_with_embeddings.append((code_construct, code_embedding))
            
        return constructs_with_embeddings, processed_doc
    except Exception as e:
        console.print(f"[red]Error in enhanced processing: {str(e)}[/]")
        return None

@click.command()
@click.argument('url')
@click.option('--save/--no-save', default=False, help='Save results to database')
@click.option('--output', '-o', type=str, help='Output file for JSON results')
@click.option('--max-tokens', type=int, default=4000, help='Maximum tokens per section (default: 4000)')
@click.option('--chunk-overlap', type=int, default=200, help='Token overlap between chunks (default: 200)')
@click.option('--max-sections', type=int, default=100, help='Maximum number of sections to return (default: 100)')
@click.option('--as-markdown/--as-html', default=False, help='Force processing as Markdown')
@click.option('--basic-processing', is_flag=True, default=False, help='Use basic processing without chunking')
def main(url: str, save: bool, output: Optional[str] = None, max_tokens: int = 4000, 
         chunk_overlap: int = 200, max_sections: int = 100, as_markdown: bool = False,
         basic_processing: bool = False):
    """Fetch and process a web document from URL with enhanced chunking.
    
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
        
        # Try to use enhanced processing if not explicitly disabled
        constructs_with_embeddings = None
        processed_doc = None
        enhanced_processing_used = False
        
        if not basic_processing:
            result = process_with_enhanced_chunking(url, max_tokens, chunk_overlap, max_sections, as_markdown)
            if result:
                constructs_with_embeddings, processed_doc = result
                enhanced_processing_used = True
                console.print(
                    f"[green]Successfully used enhanced chunking - " +
                    f"processed {len(processed_doc['sections'])} sections![/]"
                )
        
        # Fall back to original processing if enhanced processing failed or was disabled
        if not enhanced_processing_used:
            console.print("[yellow]Using original web document processing (no chunking)...[/]")
            constructs_with_embeddings = web_parser.process_web_document(url)
        
        # Print summary
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
