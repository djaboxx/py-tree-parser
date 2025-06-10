"""Module for fetching and parsing web documents (HTML and Markdown).

This module extends the parsing capabilities of the embd system to handle
web documents. It can fetch HTML and Markdown content from URLs, 
and process them into the same CodeConstruct format used for local files.
"""

import re
import urllib.parse
from typing import List, Tuple, Optional, Dict, Any
import requests
from bs4 import BeautifulSoup
import markdown
from . import models
from . import parser
from . import config

# Web document types
WEB_DOCUMENT_TYPES = {
    'html': 'web_html',
    'markdown': 'web_markdown'
}

def fetch_web_document(url: str) -> Tuple[str, str]:
    """Fetch a web document from a URL.
    
    Args:
        url: The URL to fetch
        
    Returns:
        Tuple of (content, content_type) 
        where content_type is 'html' or 'markdown'
    
    Raises:
        ValueError: If the URL is invalid or content type is unsupported
        requests.RequestException: For network or HTTP errors
    """
    # Validate URL
    parsed_url = urllib.parse.urlparse(url)
    if not parsed_url.scheme or not parsed_url.netloc:
        raise ValueError(f"Invalid URL: {url}")
    
    # Fetch content
    headers = {
        'User-Agent': 'Mozilla/5.0 (compatible; embd/0.1.0; +https://github.com/yourusername/embed)'
    }
    response = requests.get(url, headers=headers, timeout=10)
    response.raise_for_status()  # Raise exception for 4XX/5XX responses
    
    # Determine content type
    content_type = response.headers.get('Content-Type', '').lower()
    
    if 'text/html' in content_type:
        return response.text, 'html'
    elif 'text/markdown' in content_type or url.endswith(('.md', '.markdown')):
        return response.text, 'markdown'
    elif 'text/plain' in content_type:
        # Try to determine if it's likely Markdown
        if _looks_like_markdown(response.text):
            return response.text, 'markdown'
        # For plain text, default to markdown for simplicity
        return response.text, 'markdown'
    else:
        raise ValueError(f"Unsupported content type: {content_type}")

def _looks_like_markdown(text: str) -> bool:
    """Check if text looks like Markdown based on common markers."""
    # Check for common Markdown patterns
    markdown_patterns = [
        r'^#+ ',                # Headers
        r'(?m)^[-*] ',          # List items
        r'\[.+?\]\(.+?\)',      # Links
        r'(?m)^```',            # Code blocks
        r'(?m)^>',              # Blockquotes
        r'\*\*.+?\*\*',         # Bold
        r'_.+?_'                # Italics
    ]
    
    # If any pattern matches, consider it Markdown
    for pattern in markdown_patterns:
        if re.search(pattern, text):
            return True
    
    return False

def parse_html_document(html_content: str, source_url: str) -> List[Tuple[models.CodeConstruct, List[float]]]:
    """Parse HTML document and extract meaningful sections.
    
    Args:
        html_content: Raw HTML content
        source_url: Original source URL (used as filename)
        
    Returns:
        List of tuples containing (CodeConstruct, embedding)
    """
    constructs = []
    soup = BeautifulSoup(html_content, 'html.parser')
    
    # Remove unwanted elements
    for unwanted in soup.find_all(['script', 'style', 'nav', 'footer', 'iframe']):
        unwanted.decompose()
    
    # Extract title for document name
    title = soup.title.string if soup.title else source_url
    
    # Extract main content
    main_content = _extract_main_content(soup)
    
    # Create a construct for the whole document
    whole_doc = models.CodeConstruct(
        filename=source_url,
        repository='web',
        git_commit='',
        code=main_content,
        construct_type='web_html_document',
        name=title,
        description=f"HTML document: {title}",
        line_start=1,
        line_end=len(main_content.split('\n')),
        embedding=[]
    )
    
    # Generate embedding for whole document
    embedding = parser.get_embedding(main_content, f"HTML document: {title}")
    constructs.append((whole_doc, embedding))
    
    # Extract sections (headings and their content)
    sections = _extract_html_sections(soup)
    for i, section in enumerate(sections):
        heading = section.get('heading', f"Section {i+1}")
        content = section.get('content', '')
        
        # Skip very short sections
        if len(content) < 50:
            continue
        
        # Create construct for section
        construct = models.CodeConstruct(
            filename=source_url,
            repository='web',
            git_commit='',
            code=content,
            construct_type='web_html_section',
            name=heading,
            description=f"HTML section: {heading}",
            line_start=1,  # HTML doesn't have meaningful line numbers
            line_end=len(content.split('\n')),
            embedding=[]
        )
        
        # Generate embedding
        embedding = parser.get_embedding(content, f"HTML section: {heading}")
        constructs.append((construct, embedding))
    
    # Extract code blocks
    code_blocks = _extract_html_code_blocks(soup)
    for i, block in enumerate(code_blocks):
        language = block.get('language', 'unknown')
        code = block.get('code', '')
        
        # Skip very short code blocks
        if len(code) < 10:
            continue
            
        # Create construct for code block
        construct = models.CodeConstruct(
            filename=source_url,
            repository='web',
            git_commit='',
            code=code,
            construct_type='web_html_code_block',
            name=f"Code block ({language}) {i+1}",
            description=f"HTML code block in {language}",
            line_start=1,  # HTML doesn't have meaningful line numbers
            line_end=len(code.split('\n')),
            embedding=[]
        )
        
        # Generate embedding
        embedding = parser.get_embedding(code, f"Code block in {language}")
        constructs.append((construct, embedding))
    
    return constructs

def _extract_main_content(soup: BeautifulSoup) -> str:
    """Extract the main content from HTML."""
    # First, try to find common content containers
    main_candidates = [
        soup.find('main'),
        soup.find('article'),
        soup.find(id=re.compile(r'content|main', re.I)),
        soup.find(class_=re.compile(r'content|article|main', re.I))
    ]
    
    # Use the first viable candidate
    for candidate in main_candidates:
        if candidate and len(candidate.text.strip()) > 100:
            return candidate.get_text(separator='\n', strip=True)
    
    # If no good candidates, use the body content with nav/header/footer removed
    for elem in soup.find_all(['header', 'nav', 'footer', 'aside']):
        elem.decompose()
    
    return soup.body.get_text(separator='\n', strip=True) if soup.body else soup.get_text(separator='\n', strip=True)

def _extract_html_sections(soup: BeautifulSoup) -> List[Dict[str, str]]:
    """Extract sections from HTML based on heading elements."""
    sections = []
    headings = soup.find_all(['h1', 'h2', 'h3', 'h4'])
    
    for i, heading in enumerate(headings):
        heading_text = heading.get_text(strip=True)
        if not heading_text:
            continue
            
        # Get content: all elements until the next heading of same or higher level
        content_elements = []
        current = heading.next_sibling
        
        while current:
            if current.name in ['h1', 'h2', 'h3', 'h4']:
                # Stop at next heading of same or higher importance
                if current.name <= heading.name:
                    break
            content_elements.append(current)
            current = current.next_sibling
            
        # Convert elements to text
        content = '\n'.join([
            elem.get_text(separator='\n', strip=True) if hasattr(elem, 'get_text') else str(elem).strip()
            for elem in content_elements if elem and (hasattr(elem, 'get_text') or str(elem).strip())
        ])
        
        sections.append({
            'heading': heading_text,
            'content': f"{heading_text}\n\n{content}"
        })
    
    return sections

def _extract_html_code_blocks(soup: BeautifulSoup) -> List[Dict[str, str]]:
    """Extract code blocks from HTML."""
    code_blocks = []
    
    # Look for <pre> and <code> elements
    for pre in soup.find_all('pre'):
        code = pre.find('code')
        if code:
            # Try to determine language from class
            language = 'unknown'
            if code.get('class'):
                # Check for common class patterns like "language-python" or "python"
                for cls in code['class']:
                    if cls.startswith('language-'):
                        language = cls[9:]  # Extract 'python' from 'language-python'
                        break
                    elif cls in ['python', 'javascript', 'java', 'cpp', 'c', 'bash', 'json', 'html', 'css']:
                        language = cls
                        break
            
            code_blocks.append({
                'language': language,
                'code': code.get_text(strip=True)
            })
        else:
            # <pre> without <code> might still be code
            code_blocks.append({
                'language': 'unknown',
                'code': pre.get_text(strip=True)
            })
    
    # Also look for code blocks that might be in div elements with specific classes
    for div in soup.find_all(['div', 'span'], class_=re.compile(r'code|highlight|snippet', re.I)):
        code = div.get_text(strip=True)
        if code and len(code) > 20:  # Only include substantial blocks
            language = 'unknown'
            if div.get('class'):
                for cls in div['class']:
                    if cls.startswith('language-'):
                        language = cls[9:]
                        break
                    elif cls in ['python', 'javascript', 'java', 'cpp', 'c', 'bash', 'json', 'html', 'css']:
                        language = cls
                        break
            
            code_blocks.append({
                'language': language,
                'code': code
            })
    
    return code_blocks

def parse_web_markdown(markdown_content: str, source_url: str) -> List[Tuple[models.CodeConstruct, List[float]]]:
    """Parse Markdown content from the web.
    
    This converts the Markdown to HTML and then uses the HTML parser,
    as web Markdown often lacks the tree-sitter structure of a local file.
    
    Args:
        markdown_content: Raw markdown content
        source_url: Original source URL (used as filename)
        
    Returns:
        List of tuples containing (CodeConstruct, embedding)
    """
    # Convert Markdown to HTML
    html_content = markdown.markdown(markdown_content, extensions=['fenced_code', 'tables'])
    
    # Process using the HTML parser
    return parse_html_document(html_content, source_url)

def process_web_document(url: str) -> List[Tuple[models.CodeConstruct, List[float]]]:
    """Fetch and process a web document based on its content type.
    
    This is the main entry point for processing web documents.
    
    Args:
        url: URL of the web document
        
    Returns:
        List of tuples containing (CodeConstruct, embedding)
    
    Raises:
        ValueError: If the URL is invalid or content type is unsupported
        requests.RequestException: For network or HTTP errors
    """
    content, content_type = fetch_web_document(url)
    
    if content_type == 'html':
        return parse_html_document(content, url)
    elif content_type == 'markdown':
        return parse_web_markdown(content, url)
    else:
        raise ValueError(f"Unsupported web document type: {content_type}")
