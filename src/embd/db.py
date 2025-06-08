"""Database operations for storing and retrieving code constructs."""
from typing import List, Tuple
from .database import Session, engine
from . import models

def init_indexes():
    """Initialize database tables and indexes."""
    # Create tables and vector similarity indexes
    models.CodeEmbedding.create_indexes(engine)
    print("PostgreSQL tables and indexes created successfully")

def store_constructs(constructs_and_embeddings: List[Tuple[models.CodeConstruct, List[float]]]) -> None:
    """Store code constructs and their embeddings in PostgreSQL."""
    with Session() as session:
        try:
            # Store each construct with its embedding
            for construct, embedding in constructs_and_embeddings:
                # Store in PostgreSQL
                models.CodeEmbedding.store_embedding(
                    session=session,
                    construct=construct,
                    embedding=embedding
                )
            # Commit all changes
            session.commit()
        except Exception as e:
            session.rollback()
            print(f"Error storing constructs: {str(e)}")
            raise
