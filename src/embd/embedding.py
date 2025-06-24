"""Embedding generation using Google's Gemini API."""

import logging
import time
from typing import List, Optional, Literal, Union
from rich.live import Live
from rich.panel import Panel
from rich.align import Align
from rich.console import Console
from rich.text import Text
from google import genai
from google.genai import types
from . import config

logger = logging.getLogger(__name__)

# Supported task types for embedding generation
TaskType = Literal[
    "SEMANTIC_SIMILARITY",
    "CLASSIFICATION", 
    "CLUSTERING",
    "RETRIEVAL_DOCUMENT",
    "RETRIEVAL_QUERY",
    "QUESTION_ANSWERING",
    "FACT_VERIFICATION",
    "CODE_RETRIEVAL_QUERY"
]

class EmbeddingGenerator:
    """Centralized embedding generation using Gemini API."""
    
    def __init__(self, task_type: Optional[TaskType] = None):
        """Initialize the Gemini client with API key from config.
        
        Args:
            task_type: Optional task type for optimizing embeddings.
                      If not provided, uses raw embeddings.
        """
        self.client = genai.Client(api_key=config.GEMINI_API_KEY)
        self.task_type = task_type
        self.default_embedding = [0.0] * config.EMBEDDING_DIMENSION
        self.console = Console()
        self.status_panel = Panel("Initializing...", title="Embedding Status")
        self.total_tokens = 0
        self.successful_embeddings = 0
        self.failed_embeddings = 0
        self.start_time = time.time()
        self.current_file = "No file"
        
    def _update_status_panel(self, current_action: str, is_error: bool = False) -> None:
        """Update the status panel with current stats."""
        # Temporarily disabled for debugging
        return

    def set_current_file(self, filename: str) -> None:
        """Set the current file being processed.
        
        Args:
            filename: Name or path of the current file
        """
        self.current_file = filename or "No file"
        self._update_status_panel("File changed")

    def _truncate_text(self, text: str) -> tuple[str, int]:
        """Truncate text to stay within token limit.
        
        Args:
            text: Text to truncate
            
        Returns:
            Tuple containing:
            - Truncated text
            - Estimated token count
        """
        # Rough estimate: 1 token ≈ 4 characters
        # Use a conservative estimate to account for special tokens
        char_limit = config.EMBEDDING_TOKEN_LIMIT * 3
        
        if len(text) > char_limit:
            truncated = text[:char_limit]
            # Try to break at a newline or space to avoid cutting words
            last_newline = truncated.rfind('\n')
            last_space = truncated.rfind(' ')
            break_point = max(last_newline, last_space)
            if break_point > 0:
                truncated = truncated[:break_point]
            
            # Estimate tokens (rough approximation)
            token_estimate = len(truncated.split())
            return truncated, token_estimate
        
        return text, len(text.split())

    def generate(self, content: str, description: str = "", filename: Optional[str] = None) -> List[float]:
        """Generate embeddings for content with optional description.
        
        Args:
            content: The main text to generate embeddings for
            description: Optional description or context for the content
            filename: Optional filename being processed
            
        Returns:
            List[float]: The generated embedding vector
        """
        if filename:
            self.set_current_file(filename)
        # with Live(self.status_panel, refresh_per_second=4) as live:
        if True:  # Temporarily disable Live display for debugging
            try:
                # Prepare and truncate content
                combined_text = f"{content}\n\nDescription: {description}" if description else content
                truncated_text, tokens = self._truncate_text(combined_text)
                self._update_status_panel(
                    f"Processing content ({tokens} tokens)" + 
                    (" [truncated]" if truncated_text != combined_text else "")
                )
                
                embedding_config = types.EmbedContentConfig(
                    task_type=self.task_type
                ) if self.task_type else None
                
                # Make API call
                self._update_status_panel("Calling Gemini API...")
                result = self.client.models.embed_content(
                    model="gemini-embedding-exp-03-07",
                    contents=truncated_text,
                    config=embedding_config
                )
                
                if not result or not result.embeddings:
                    self.failed_embeddings += 1
                    self._update_status_panel("No embedding returned from API", is_error=True)
                    return self.default_embedding
                
                # Process results
                self._update_status_panel("Processing API response...")
                values = result.embeddings[0].values
                
                if not values:
                    self.failed_embeddings += 1
                    self._update_status_panel("No embedding values in response", is_error=True)
                    return self.default_embedding
                
                embedding_values = [float(val) for val in values]
                if len(embedding_values) != config.EMBEDDING_DIMENSION:
                    self.failed_embeddings += 1
                    self._update_status_panel(
                        f"Wrong embedding dimension: {len(embedding_values)} (expected {config.EMBEDDING_DIMENSION})", 
                        is_error=True
                    )
                    return self.default_embedding
                
                # Update stats
                self.successful_embeddings += 1
                self.total_tokens += tokens
                self._update_status_panel("Successfully generated embedding")
                return embedding_values
                
            except Exception as e:
                self.failed_embeddings += 1
                error_msg = str(e)
                self._update_status_panel(f"Error: {error_msg}", is_error=True)
                logger.error(f"Error generating embedding: {error_msg}")
                return self.default_embedding
            
    def generate_batch(self, items: List[tuple[str, str]], filenames: Optional[List[str]] = None) -> List[List[float]]:
        """Generate embeddings for multiple content items in batch.
        
        Args:
            items: List of (content, description) tuples
            filenames: Optional list of filenames being processed
            
        Returns:
            List[List[float]]: List of embedding vectors
        """
        if filenames:
            self.set_current_file(f"Batch: {len(filenames)} files")
        with Live(self.status_panel, refresh_per_second=4) as live:
            try:
                self._update_status_panel(f"Preparing batch of {len(items)} items...")
                combined_texts = []
                total_batch_tokens = 0
                
                for content, desc in items:
                    text = f"{content}\n\nDescription: {desc}" if desc else content
                    truncated_text, tokens = self._truncate_text(text)
                    total_batch_tokens += tokens
                    combined_texts.append(truncated_text)
                
                self._update_status_panel(f"Processing batch ({total_batch_tokens} total tokens)")
                
                embedding_config = types.EmbedContentConfig(
                    task_type=self.task_type
                ) if self.task_type else None
                
                # Make API call
                self._update_status_panel("Calling Gemini API for batch...")
                result = self.client.models.embed_content(
                    model="gemini-embedding-exp-03-07",
                    contents=combined_texts,
                    config=embedding_config
                )
                
                if not result or not result.embeddings:
                    self.failed_embeddings += len(items)
                    self._update_status_panel("No embeddings returned from API for batch", is_error=True)
                    return [self.default_embedding] * len(items)
                
                # Process results
                self._update_status_panel("Processing batch API response...")
                embeddings = []
                
                for i, embedding_result in enumerate(result.embeddings):
                    if not embedding_result.values:
                        self.failed_embeddings += 1
                        self._update_status_panel(f"No values for item {i} in batch", is_error=True)
                        embeddings.append(self.default_embedding)
                        continue
                        
                    values = [float(val) for val in embedding_result.values]
                    if len(values) != config.EMBEDDING_DIMENSION:
                        self.failed_embeddings += 1
                        self._update_status_panel(
                            f"Wrong dimension for item {i}: {len(values)}", 
                            is_error=True
                        )
                        embeddings.append(self.default_embedding)
                        continue
                        
                    self.successful_embeddings += 1
                    embeddings.append(values)
                
                self.total_tokens += total_batch_tokens
                self._update_status_panel(f"Successfully processed {len(embeddings)} embeddings")
                return embeddings
                
            except Exception as e:
                self.failed_embeddings += len(items)
                error_msg = str(e)
                self._update_status_panel(f"Batch Error: {error_msg}", is_error=True)
                logger.error(f"Error generating batch embeddings: {error_msg}")
                return [self.default_embedding] * len(items)
            

