"""Semantic code search using pgvector and Gemini."""
from typing import List, Dict, Any
import math
from .database import Session
from . import models
from . import config
from google import genai
from google.genai import types

# Setup Gemini client
client = genai.Client(api_key=config.GEMINI_API_KEY)

def search_code(query: str, limit: int = 5, min_similarity: float = 0.7,
             include_code: bool = True, include_description: bool = True,
             include_embedding: bool = False, for_reconstruction: bool = False) -> List[Dict[str, Any]]:
    """Search for code constructs semantically similar to the query.
    
    Args:
        query: Natural language query to search for
        limit: Maximum number of results to return
        min_similarity: Minimum similarity score (0-1)
        include_code: Whether to include full code content in results
        include_description: Whether to include descriptions in results
        include_embedding: Whether to include embedding vectors in results
        for_reconstruction: If True, returns all fields needed for CodeConstruct
    
    Returns:
        List of dicts containing matched constructs with requested fields
    """
    try:
        # Generate embedding for the query
        result = client.models.embed_content(
            model=config.EMBEDDING_MODEL,
            contents=query,
            config=types.EmbedContentConfig(task_type="RETRIEVAL_QUERY")  # Specify query embedding
        )
        
        if not result or not result.embeddings or not result.embeddings[0].values:
            print("Failed to generate embedding for query")
            return []
            
        query_embedding = [float(val) for val in result.embeddings[0].values]
        if len(query_embedding) != config.EMBEDDING_DIMENSION:
            print(f"Warning: Unexpected query embedding dimension: {len(query_embedding)}")
            return []
        
        # Search for similar code in PostgreSQL
        with Session() as session:
            matches = models.CodeEmbedding.similar_code(
                session=session,
                query_embedding=query_embedding,
                limit=limit,
                min_similarity=min_similarity,
                include_code=include_code,
                include_description=include_description,
                include_embedding=include_embedding,
                for_reconstruction=for_reconstruction
            )
        
        # Filter out any matches with invalid similarity scores
        matches = [m for m in matches if m['similarity'] is not None and not math.isnan(m['similarity'])]
        if not matches:
            print("No matches found with valid similarity scores")
            return []
        
        return matches
        
    except Exception as e:
        print(f"Error during semantic search: {str(e)}")
        return []
