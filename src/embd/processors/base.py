"""Base class for all content processors."""

import logging
from abc import ABC, abstractmethod
from typing import List, Tuple, Optional
from .. import models
from ..embedding import EmbeddingGenerator

logger = logging.getLogger(__name__)

class BaseProcessor(ABC):
    """Base class for processing content and generating embeddings."""
    
    def __init__(self, embedding_generator: Optional[EmbeddingGenerator] = None):
        """Initialize processor with optional embedding generator.
        
        Args:
            embedding_generator: EmbeddingGenerator instance or None to create new one
        """
        self.embedding_generator = embedding_generator or EmbeddingGenerator()
        
    @abstractmethod
    def process(self) -> Tuple[List[Tuple[models.CodeConstruct, List[float]]], List[models.Import]]:
        """Process content and return code constructs with embeddings and imports.
        
        Returns:
            Tuple containing:
            - List of (CodeConstruct, embedding) tuples
            - List of Import objects
        """
        pass
        
    def _generate_embedding(self, content: str, description: str = "") -> List[float]:
        """Generate embedding for content using configured generator.
        
        Args:
            content: Content to generate embedding for
            description: Optional description or context
            
        Returns:
            List[float]: Generated embedding vector
        """
        return self.embedding_generator.generate(content, description)
