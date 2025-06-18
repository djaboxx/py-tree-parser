"""Local file processor for git-tracked files."""

import os
import logging
import subprocess
from typing import List, Tuple, Optional, Set
from pathlib import Path
from tree_sitter import Parser
from tree_sitter_languages import get_language, get_parser

from ..embedding import EmbeddingGenerator
from .. import models
from .base import BaseProcessor

logger = logging.getLogger(__name__)

class LocalFileProcessor(BaseProcessor):
    """Processes local files that are tracked by git."""
    
    def __init__(self, repo_path: str, embedding_generator: Optional[EmbeddingGenerator] = None):
        """Initialize processor.
        
        Args:
            repo_path: Path to git repository
            embedding_generator: Optional embedding generator instance
        """
        super().__init__(embedding_generator)
        self.repo_path = os.path.abspath(repo_path)
        self._processed_files: Set[str] = set()
        
        # Get current commit hash
        try:
            result = subprocess.run(
                ['git', 'rev-parse', 'HEAD'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            self.current_commit = result.stdout.strip()
        except subprocess.CalledProcessError:
            self.current_commit = "HEAD"
            logger.warning("Could not determine current git commit hash")
        
    def get_tracked_files(self) -> List[str]:
        """Get list of git tracked files in the repository."""
        try:
            result = subprocess.run(
                ['git', 'ls-files'],
                cwd=self.repo_path,
                capture_output=True,
                text=True,
                check=True
            )
            return [os.path.join(self.repo_path, f.strip()) 
                   for f in result.stdout.splitlines() if f.strip()]
        except subprocess.CalledProcessError as e:
            logger.error(f"Error getting tracked files: {e}")
            return []
            
    def process(self) -> Tuple[List[Tuple[models.CodeConstruct, List[float]]], List[models.Import]]:
        """Process all git-tracked files in the repository.
        
        Returns:
            Tuple containing:
            - List of (CodeConstruct, embedding) tuples
            - List of Import objects
        """
        constructs_with_embeddings = []
        imports = []
        
        for file_path in self.get_tracked_files():
            if file_path in self._processed_files:
                continue
                
            try:
                file_constructs, file_imports = self.process_file(file_path)
                constructs_with_embeddings.extend(file_constructs)
                imports.extend(file_imports)
                self._processed_files.add(file_path)
            except Exception as e:
                logger.error(f"Error processing {file_path}: {e}")
                
        return constructs_with_embeddings, imports
        
    def process_file(self, file_path: str) -> Tuple[List[Tuple[models.CodeConstruct, List[float]]], List[models.Import]]:
        """Process a single file.
        
        Args:
            file_path: Path to file to process
            
        Returns:
            Tuple containing:
            - List of (CodeConstruct, embedding) tuples
            - List of Import objects
        """
        if file_path.endswith(('.md', '.mdx', '.markdown')):
            return self.process_markdown(file_path)
        else:
            return self.process_code_file(file_path)
            
    def process_markdown(self, file_path: str) -> Tuple[List[Tuple[models.CodeConstruct, List[float]]], List[models.Import]]:
        """Process a markdown file to extract code blocks with language tags.
        
        Args:
            file_path: Path to markdown file
            
        Returns:
            Tuple containing:
            - List of (CodeConstruct, embedding) tuples
            - List of Import objects
        """
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            constructs_with_embeddings = []
            current_block = []
            current_language = None
            in_code_block = False
            line_num = 0
            block_start = 0
            
            for line in content.splitlines():
                line_num += 1
                if line.startswith('```'):
                    if in_code_block:
                        # End of code block
                        if current_block and current_language:
                            code = '\n'.join(current_block)
                            description = f"Code block in {current_language} from {os.path.basename(file_path)}"
                            
                            # Create embedding
                            embedding = self.embedding_generator.generate(code, description) if self.embedding_generator else []
                            
                            # Create construct with proper fields
                            construct = models.CodeConstruct(
                                name=f"{os.path.basename(file_path)}_{current_language}_block",
                                construct_type="markdown_code_block",
                                filename=file_path,
                                code=code,
                                description=description,
                                repository="",  # Will be set by main.py
                                git_commit=self.current_commit,
                                embedding=embedding,
                                line_start=block_start,
                                line_end=line_num
                            )
                            constructs_with_embeddings.append((construct, embedding))
                            
                        current_block = []
                        current_language = None
                        in_code_block = False
                    else:
                        # Start of code block
                        language = line[3:].strip()  # Get language after ```
                        if language:
                            current_language = language
                            in_code_block = True
                            block_start = line_num
                elif in_code_block:
                    current_block.append(line)
            
            return constructs_with_embeddings, []  # Markdown files don't have imports
            
        except Exception as e:
            logger.error(f"Error processing markdown file {file_path}: {e}")
            return [], []
        
    def process_code_file(self, file_path: str) -> Tuple[List[Tuple[models.CodeConstruct, List[float]]], List[models.Import]]:
        """Process a code file using tree-sitter for parsing.
        
        Args:
            file_path: Path to code file
            
        Returns:
            Tuple containing:
            - List of (CodeConstruct, embedding) tuples
            - List of Import objects
        """
        try:
            # Read file content
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            # Determine language from extension
            ext = os.path.splitext(file_path)[1].lower()
            language_map = {
                '.py': 'python',
                '.js': 'javascript',
                '.ts': 'typescript',
                '.java': 'java',
                '.c': 'c',
                '.cpp': 'cpp',
                '.go': 'go',
                '.rs': 'rust'
            }
            language = language_map.get(ext, 'text')
            description = f"Complete {language} file: {os.path.basename(file_path)}"
            
            # Create embedding
            embedding = self.embedding_generator.generate(content, description) if self.embedding_generator else []
            
            # Create construct with proper fields
            construct = models.CodeConstruct(
                name=os.path.basename(file_path),
                construct_type="source_file",
                filename=file_path,
                code=content,
                description=description,
                repository="",  # Will be set by main.py
                git_commit=self.current_commit,
                embedding=embedding,
                line_start=1,
                line_end=len(content.splitlines())
            )
            
            # TODO: Add tree-sitter parsing for finer-grained code constructs
            # TODO: Add import extraction
            return [(construct, embedding)], []
            
        except Exception as e:
            logger.error(f"Error processing code file {file_path}: {e}")
            return [], []
