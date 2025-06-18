"""Embedding generation using Google's Gemini API."""

import logging
from typing import List, Optional, Literal, Union
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
        
    def generate(self, content: str, description: str = "") -> List[float]:
        """Generate embeddings for content with optional description.
        
        Args:
            content: The main text to generate embeddings for
            description: Optional description or context for the content
            
        Returns:
            List[float]: The generated embedding vector
        """
        try:
            combined_text = f"{content}\n\nDescription: {description}" if description else content
            
            embedding_config = types.EmbedContentConfig(
                task_type=self.task_type
            ) if self.task_type else None
            
            result = self.client.models.embed_content(
                model="gemini-embedding-exp-03-07",
                contents=combined_text,
                config=embedding_config
            )
            
            if not result or not result.embeddings:
                logger.error("No embedding returned from Gemini API")
                return self.default_embedding
                
            embedding = result.embeddings[0]  # First embedding for single content
            # Convert the embedding values to a list of floats
            values = result.embeddings[0].values
            
            if not values:
                logger.error("No embedding values returned")
                return self.default_embedding
                
            embedding_values = [float(val) for val in values]
            if len(embedding_values) != config.EMBEDDING_DIMENSION:
                logger.error(f"Unexpected embedding dimension: {len(embedding_values)}")
                return self.default_embedding
                
            return embedding_values
            
        except Exception as e:
            logger.error(f"Error generating embedding: {str(e)}")
            return self.default_embedding
            
    def generate_batch(self, items: List[tuple[str, str]]) -> List[List[float]]:
        """Generate embeddings for multiple content items in batch.
        
        Args:
            items: List of (content, description) tuples
            
        Returns:
            List[List[float]]: List of embedding vectors
        """
        try:
            combined_texts = [
                f"{content}\n\nDescription: {desc}" if desc else content 
                for content, desc in items
            ]
            
            embedding_config = types.EmbedContentConfig(
                task_type=self.task_type
            ) if self.task_type else None
            
            result = self.client.models.embed_content(
                model="gemini-embedding-exp-03-07",
                contents=combined_texts,
                config=embedding_config
            )
            
            if not result or not result.embeddings:
                logger.error("No embeddings returned from Gemini API batch request")
                return [self.default_embedding] * len(items)
                
            embeddings = []
            for emb in result.embeddings:
                values = emb.values
                if not values:
                    logger.error("No embedding values returned for item in batch")
                    embeddings.append(self.default_embedding)
                    continue
                
                embedding_values = [float(val) for val in values]
                if len(embedding_values) != config.EMBEDDING_DIMENSION:
                    logger.error(f"Unexpected embedding dimension: {len(embedding_values)}")
                    embeddings.append(self.default_embedding)
                else:
                    embeddings.append(embedding_values)
            
            return embeddings
            
        except Exception as e:
            logger.error(f"Error generating batch embeddings: {str(e)}")
            return [self.default_embedding] * len(items)
