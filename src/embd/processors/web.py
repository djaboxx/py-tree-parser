"""Web content processor for fetching and processing web documents."""

import logging
import asyncio
import aiohttp
from typing import List, Tuple, Optional, Dict, Any, cast
from bs4 import BeautifulSoup, Tag
from bs4.element import NavigableString
from urllib.parse import urlparse

from ..embedding import EmbeddingGenerator
from .. import models
from .base import BaseProcessor

logger = logging.getLogger(__name__)

class WebProcessor(BaseProcessor):
    """Processes web documents with proper code block handling."""
    
    def __init__(self, url: str, embedding_generator: Optional[EmbeddingGenerator] = None):
        """Initialize processor.
        
        Args:
            url: URL to process
            embedding_generator: Optional embedding generator instance
        """
        super().__init__(embedding_generator)
        self.url = url
        
    async def fetch_content(self) -> Tuple[str, str]:
        """Fetch content from URL.
        
        Returns:
            Tuple of (content, content_type)
        """
        async with aiohttp.ClientSession() as session:
            async with session.get(self.url) as response:
                response.raise_for_status()
                content_type = response.headers.get('content-type', '').lower()
                content = await response.text()
                return content, content_type
                
    def extract_code_blocks(self, soup: BeautifulSoup) -> List[Dict[str, str]]:
        """Extract code blocks from HTML, preserving formatting.
        
        Args:
            soup: BeautifulSoup object of the HTML
            
        Returns:
            List of dicts with 'code' and 'language' keys
        """
        code_blocks = []
        
        for pre in soup.find_all('pre'):
            pre_tag = cast(Tag, pre)
            code_tag = cast(Optional[Tag], pre_tag.find('code'))
            if code_tag is not None:
                # Try to determine language from class
                language = 'unknown'
                classes = code_tag.get('class') or []
                if classes:
                    for cls in classes:
                        if isinstance(cls, str):  # Ensure cls is a string
                            if cls.startswith('language-'):
                                language = cls[9:]  # Remove 'language-' prefix
                                break
                            elif cls in ['python', 'javascript', 'java', 'cpp', 'c', 
                                       'bash', 'json', 'html', 'css']:
                                language = cls
                                break
                
                # Preserve whitespace and formatting
                code_text = code_tag.get_text(separator='\n', strip=False)
                code_blocks.append({
                    'code': code_text,
                    'language': language
                })
                
        return code_blocks
        
    def process(self) -> Tuple[List[Tuple[models.CodeConstruct, List[float]]], List[models.Import]]:
        """Process web document.
        
        Returns:
            Tuple containing:
            - List of (CodeConstruct, embedding) tuples
            - List of Import objects (empty for web documents)
        """
        content, content_type = asyncio.run(self.fetch_content())
        constructs_with_embeddings = []
        
        try:
            # Process based on content type
            if 'text/html' in content_type:
                soup = BeautifulSoup(content, 'html.parser')
                
                # Process code blocks
                for block in self.extract_code_blocks(soup):
                    construct = models.CodeConstruct(
                        filename=self.url,
                        repository='web',
                        git_commit='',
                        code=block['code'],
                        construct_type='code_block',
                        name=f"Code Block ({block['language']})",
                        description=f"Code block in {block['language']} from {self.url}",
                        line_start=0,  # Web documents don't have line numbers
                        line_end=0,
                        embedding=[]
                    )
                    embedding = self._generate_embedding(block['code'], construct.description)
                    constructs_with_embeddings.append((construct, embedding))
                    
                # Process text content
                for section in soup.find_all(['h1', 'h2', 'h3', 'p']):
                    section_tag = cast(Tag, section)
                    text = section_tag.get_text(strip=True)
                    tag_name = section_tag.name or 'text'  # Fallback if name is None
                    if text:
                        construct = models.CodeConstruct(
                            filename=self.url,
                            repository='web',
                            git_commit='',
                            code=text,
                            construct_type='text',
                            name=tag_name,
                            description=f"{tag_name.upper()} section from {self.url}",
                            line_start=0,
                            line_end=0,
                            embedding=[]
                        )
                        embedding = self._generate_embedding(text, construct.description)
                        constructs_with_embeddings.append((construct, embedding))
                        
            elif 'text/markdown' in content_type or self.url.endswith(('.md', '.mdx')):
                # Process markdown similarly to local markdown files
                pass
                
        except Exception as e:
            logger.error(f"Error processing web document {self.url}: {e}")
            
        return constructs_with_embeddings, []  # Web documents don't have imports
