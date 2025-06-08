"""PostgreSQL with pgvector integration for semantic search using SQLAlchemy."""
from typing import List, Optional, Dict, Any
from .database import Session
from .models import CodeEmbedding, CodeConstruct

def init_pg():
    """Initialize PostgreSQL database and tables."""
    # Create tables and indexes using SQLAlchemy models
    with Session() as session:
        CodeEmbedding.create_indexes(session.bind)

def store_embedding(construct: 'CodeConstruct', embedding: List[float]) -> None:
    """Store an embedding in PostgreSQL.
    
    Args:
        construct: CodeConstruct object containing the code and metadata
        embedding: Vector embedding for the code
    """
    with Session() as session:
        try:
            CodeEmbedding.store_embedding(
                session=session,
                construct=construct,
                embedding=embedding
            )
            session.commit()
        except Exception as e:
            session.rollback()
            raise

def similar_code(
    query_embedding: List[float],
    limit: int = 5,
    min_similarity: float = 0.7
) -> List[Dict[str, Any]]:
    """Find similar code constructs using vector similarity search."""
    with Session() as session:
        return CodeEmbedding.similar_code(
            session=session,
            query_embedding=query_embedding,
            limit=limit,
            min_similarity=min_similarity
        )


