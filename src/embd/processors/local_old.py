"""Local file processor for git-tracked files."""

import os
import logging
import subprocess
from typing import List, Tuple, Optional, Set, Any
from pathlib import Path
from tree_sitter import Parser
from tree_sitter_languages import get_language, get_parser

from ..embedding import EmbeddingGenerator
from .. import models
from .. import config
from .base import BaseProcessor
from pathlib import Path
from fnmatch import fnmatch

logger = logging.getLogger(__name__)

class LocalFileProcessor(BaseProcessor):
    ""def _capture_matches(self, query_text: str, node: Any, language: Any) -> List[Tuple[str, Any]]:
        """Helper to handle tree-sitter query captures safely."""
        logger.debug(f"Running tree-sitter query:\n{query_text}")rocesses local files that are tracked by git."""
    
    def __init__(self, 
                repo_path: str, 
                embedding_generator: Optional[EmbeddingGenerator] = None,
                include_patterns: Optional[List[str]] = None,
                exclude_patterns: Optional[List[str]] = None):
        """Initialize processor.
        
        Args:
            repo_path: Path to git repository
            embedding_generator: Optional embedding generator instance
            include_patterns: List of glob patterns for files to include
            exclude_patterns: List of glob patterns for files to exclude
        """
        super().__init__(embedding_generator)
        self.repo_path = os.path.abspath(repo_path)
        self._processed_files: Set[str] = set()
        
        # Initialize patterns
        self.include_patterns = include_patterns or config.DEFAULT_INCLUDE_PATTERNS
        self.exclude_patterns = exclude_patterns or config.DEFAULT_EXCLUDE_PATTERNS
        
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
        
    def should_process_file(self, file_path: str) -> bool:
        """Check if a file should be processed based on include/exclude patterns.
        
        Args:
            file_path: Path to the file to check
            
        Returns:
            bool: True if the file should be processed
        """
        # Convert to relative path for pattern matching
        rel_path = os.path.relpath(file_path, self.repo_path)
        
        # Check exclude patterns first
        for pattern in self.exclude_patterns:
            if fnmatch(rel_path, pattern):
                return False
        
        # Then check include patterns
        for pattern in self.include_patterns:
            if fnmatch(rel_path, pattern):
                return True
        
        return False

    def list_processable_files(self) -> List[tuple[str, str]]:
        """List all files that would be processed based on current patterns.
        
        Returns:
            List of tuples containing (absolute_path, relative_path)
        """
        tracked_files = self.get_tracked_files()
        processable = []
        
        for file_path in tracked_files:
            if self.should_process_file(file_path):
                rel_path = os.path.relpath(file_path, self.repo_path)
                processable.append((file_path, rel_path))
        
        return processable

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
        
        # Get files using the same logic as list_processable_files()
        processable_files = self.list_processable_files()
        logger.info(f"Found {len(processable_files)} files to process")
        
        for file_path, rel_path in processable_files:
            logger.info(f"Processing file: {rel_path}")
            
            if file_path in self._processed_files:
                logger.info(f"Skipping already processed file: {rel_path}")
                continue
                
            try:
                file_constructs, file_imports = self.process_file(file_path)
                logger.info(f"Found {len(file_constructs)} constructs in {rel_path}")
                constructs_with_embeddings.extend(file_constructs)
                imports.extend(file_imports)
                self._processed_files.add(file_path)
            except Exception as e:
                logger.error(f"Error processing {rel_path}: {e}")
                
        logger.info(f"Processed {len(self._processed_files)} files total")
        logger.info(f"Found {len(constructs_with_embeddings)} total constructs")
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
                            embedding = self.embedding_generator.generate(
                                code, 
                                description, 
                                filename=file_path
                            ) if self.embedding_generator else []
                            
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
                lines = content.splitlines()
                
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
                '.rs': 'rust',
            }
            lang_name = language_map.get(ext)
            if not lang_name:
                logger.warning(f"Unsupported file type: {ext}, processing as plain text")
                return self._process_text_file(file_path, content, lines)
            
            constructs_with_embeddings = []
            imports = []
            
            # Initialize tree-sitter parser
            logger.info(f"Processing {lang_name} file: {file_path}")
            try:
                language = get_language(lang_name)
                parser = Parser()
                parser.set_language(language)
                
                tree = parser.parse(content.encode())
                if not tree or not tree.root_node:
                    raise ValueError("Failed to parse file")
                logger.info("Successfully parsed file with tree-sitter")
                
                # Debug the tree structure
                logger.debug(f"AST root type: {tree.root_node.type}")
                logger.debug(f"Number of top-level nodes: {len(tree.root_node.children)}")
                for child in tree.root_node.children:
                    logger.debug(f"Top-level node: {child.type}")
                    
            except Exception as e:
                logger.error(f"Tree-sitter error for {file_path}: {str(e)}")
                return self._process_text_file(file_path, content, lines)
            
            # First, process the whole file as a reference construct
            description = f"Complete {lang_name} file: {os.path.basename(file_path)}"
            file_embedding = self.embedding_generator.generate(
                content, 
                description,
                filename=file_path
            ) if self.embedding_generator else []
            
            file_construct = models.CodeConstruct(
                name=os.path.basename(file_path),
                construct_type="source_file",
                filename=file_path,
                code=content,
                description=description,
                repository="",  # Will be set by main.py
                git_commit=self.current_commit,
                embedding=file_embedding,
                line_start=1,
                line_end=len(lines)
            )
            constructs_with_embeddings.append((file_construct, file_embedding))
            
            # Process imports for Python
            if lang_name == 'python':
                # Find import statements
                for node in tree.root_node.children:
                    if node.type in ['import_statement', 'import_from_statement']:
                        import_text = content[node.start_byte:node.end_byte]
                        line_start = node.start_point[0] + 1
                        line_end = node.end_point[0] + 1
                        
                        # Parse the import statement
                        is_from = import_text.startswith('from')
                        parts = import_text.split()
                        if is_from and len(parts) >= 4:  # from module import name
                            module_name = parts[1]
                            import_type = "from-import"
                        elif not is_from and len(parts) >= 2:  # import module
                            module_name = parts[1].split('.')[0]  # Get root module
                            import_type = "import"
                        else:
                            continue
                            
                        imports.append(models.Import(
                            filename=file_path,
                            repository="",  # Will be set by main.py
                            module_name=module_name,
                            import_type=import_type,
                            line_start=line_start,
                            line_end=line_end,
                            git_commit=self.current_commit
                        ))
            
            # Process classes and functions
            if lang_name == 'python':
                # Process all nodes recursively
                def process_nodes(nodes, parent_class=None):
                    for node in nodes:
                        if node.type == 'class_definition':
                            name_node = node.child_by_field_name('name')
                            if not name_node:
                                continue
                                
                            class_name = content[name_node.start_byte:name_node.end_byte]
                            class_code = content[node.start_byte:node.end_byte]
                            line_start = node.start_point[0] + 1
                            line_end = node.end_point[0] + 1
                            
                            description = f"Class {class_name} in {os.path.basename(file_path)}"
                            
                            # Generate embedding for the class
                            embedding = self.embedding_generator.generate(
                                class_code,
                                description,
                                filename=file_path
                            ) if self.embedding_generator else []
                            
                            construct = models.CodeConstruct(
                                name=class_name,
                                construct_type="class",
                                filename=file_path,
                                code=class_code,
                                description=description,
                                repository="",  # Will be set by main.py
                                git_commit=self.current_commit,
                                embedding=embedding,
                                line_start=line_start,
                                line_end=line_end
                            )
                            constructs_with_embeddings.append((construct, embedding))
                            
                            # Process methods within the class
                            body_node = node.child_by_field_name('body')
                            if body_node:
                                for child in body_node.children:
                                    if child.type == 'function_definition':
                                        method_name_node = child.child_by_field_name('name')
                                        if not method_name_node:
                                            continue
                                            
                                        method_name = f"{class_name}.{content[method_name_node.start_byte:method_nameNode.end_byte]}"
                                        method_code = content[child.start_byte:child.end_byte]
                                        method_line_start = child.start_point[0] + 1
                                        method_line_end = child.end_point[0] + 1
                                        
                                        description = f"Method {method_name} in {os.path.basename(file_path)}"
                                        
                                        # Generate embedding for the method
                                        embedding = self.embedding_generator.generate(
                                            method_code,
                                            description,
                                            filename=file_path
                                        ) if self.embedding_generator else []
                                        
                                        construct = models.CodeConstruct(
                                            name=method_name,
                                            construct_type="method",
                                            filename=file_path,
                                            code=method_code,
                                            description=description,
                                            repository="",  # Will be set by main.py
                                            git_commit=self.current_commit,
                                            embedding=embedding,
                                            line_start=method_line_start,
                                            line_end=method_line_end
                                        )
                                        constructs_with_embeddings.append((construct, embedding))
                        
                        elif node.type == 'function_definition' and not parent_class:
                            # Top-level function
                            name_node = node.child_by_field_name('name')
                            if not name_node:
                                continue
                                
                            func_name = content[name_node.start_byte:name_node.end_byte]
                            func_code = content[node.start_byte:node.end_byte]
                            line_start = node.start_point[0] + 1
                            line_end = node.end_point[0] + 1
                            
                            description = f"Function {func_name} in {os.path.basename(file_path)}"
                            
                            # Generate embedding for the function
                            embedding = self.embedding_generator.generate(
                                func_code,
                                description,
                                filename=file_path
                            ) if self.embedding_generator else []
                            
                            construct = models.CodeConstruct(
                                name=func_name,
                                construct_type="function",
                                filename=file_path,
                                code=func_code,
                                description=description,
                                repository="",  # Will be set by main.py
                                git_commit=self.current_commit,
                                embedding=embedding,
                                line_start=line_start,
                                line_end=line_end
                            )
                            constructs_with_embeddings.append((construct, embedding))
                
                # Process all top-level nodes
                process_nodes(tree.root_node.children)
            
            return constructs_with_embeddings, imports
                
        except Exception as e:
            logger.error(f"Error processing code file {file_path}: {e}")
            logger.exception(e)
            return [], []
        
    def _process_text_file(self, file_path: str, content: str, lines: List[str]) -> Tuple[List[Tuple[models.CodeConstruct, List[float]]], List[models.Import]]:
        """Process a file as plain text when tree-sitter parsing fails."""
        constructs_with_embeddings = []
        
        description = f"Text file: {os.path.basename(file_path)}"
        embedding = self.embedding_generator.generate(
            content,
            description,
            filename=file_path
        ) if self.embedding_generator else []
        
        construct = models.CodeConstruct(
            name=os.path.basename(file_path),
            construct_type="text_file",
            filename=file_path,
            code=content,
            description=description,
            repository="",  # Will be set by main.py
            git_commit=self.current_commit,
            embedding=embedding,
            line_start=1,
            line_end=len(lines)
        )
        constructs_with_embeddings.append((construct, embedding))
        return constructs_with_embeddings, []
        
    def _capture_matches(self, query_text: str, node: Any, language: Any) -> List[Tuple[str, Any]]:
        """Helper to handle tree-sitter query captures safely.
        
        Args:
            query_text: The query pattern
            node: The node to query
            language: The tree-sitter language
            
        Returns:
            List of (capture_name, node) tuples
        """
        try:
            query = language.query(query_text)
            captures = []
            for n in query.captures(node):
                captures.append((n.capture, n.node))
            return captures
        except Exception as e:
            logger.warning(f"Tree-sitter query failed: {e}")
            return []
    
    def _get_node_text(self, node: Any, content: str) -> str:
        """Get text content for a node."""
        return content[node.start_byte:node.end_byte]
    
    def _get_node_lines(self, node: Any) -> Tuple[int, int]:
        """Get line numbers for a node."""
        return (node.start_point[0] + 1, node.end_point[0] + 1)
    
    def _get_construct(self, 
                    node: Any,
                    content: str,
                    construct_type: str,
                    file_path: str,
                    name: str,
                    description: str) -> Tuple[models.CodeConstruct, List[float]]:
        """Create a CodeConstruct with embedding for a node.
        
        Args:
            node: The tree-sitter node
            content: Source file content
            construct_type: Type of construct (class, method, function)
            file_path: Path to source file
            name: Name of the construct
            description: Description for the construct
            
        Returns:
            Tuple of (construct, embedding)
        """
        code = self._get_node_text(node, content)
        line_start, line_end = self._get_node_lines(node)
        
        embedding = self.embedding_generator.generate(
            code,
            description,
            filename=file_path
        ) if self.embedding_generator else []
        
        construct = models.CodeConstruct(
            name=name,
            construct_type=construct_type,
            filename=file_path,
            code=code,
            description=description,
            repository="",  # Will be set by main.py
            git_commit=self.current_commit,
            embedding=embedding,
            line_start=line_start,
            line_end=line_end
        )
        
        return construct, embedding
