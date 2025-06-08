"""Models for data validation and database operations."""
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy import Column, String, Integer, DateTime, Float, func, Text
from sqlalchemy.dialects.postgresql import ARRAY
from sqlalchemy.sql.expression import cast
from pgvector.sqlalchemy import Vector
from sqlalchemy import select, text
from .database import Base
from pydantic import BaseModel, Field

# =============================================================================
# Pydantic Models for Request/Response Validation
# =============================================================================

class CodeConstruct(BaseModel):
    """Pydantic model for request/response validation."""
    filename: str = Field(description="Source filename of the code construct")
    repository: str = Field(description="Name of the repository containing the code")
    git_commit: str = Field(description="Git commit hash of last change")
    code: str = Field(description="Extracted code from the construct")
    construct_type: str = Field(description="Type of code construct (e.g. function, class)")
    name: str = Field(description="Name of the function or class")
    description: str = Field(description="AI-generated description of the code construct")
    embedding: List[float] = Field(description="Vector embedding of the code and description")
    line_start: int = Field(description="Starting line number in source file")
    line_end: int = Field(description="Ending line number in source file")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    @classmethod
    def from_search_result(cls, result: Dict[str, Any]) -> 'CodeConstruct':
        """Reconstruct a CodeConstruct object from a search result.
        
        Args:
            result: Dictionary containing search result fields from similar_code
                   Must include all required fields (use for_reconstruction=True
                   when searching to ensure all needed fields are present)
        
        Returns:
            CodeConstruct: A new CodeConstruct instance
            
        Raises:
            ValueError: If required fields are missing from the result
        """
        required_fields = {
            'filename', 'repository', 'git_commit', 'code', 'construct_type',
            'name', 'description', 'line_start', 'line_end'
        }
        
        missing = required_fields - set(result.keys())
        if missing:
            raise ValueError(
                f"Missing required fields for reconstruction: {missing}. "
                "Did you use for_reconstruction=True when searching?"
            )
            
        # Convert timestamps if present
        created_at = result.get('created_at')
        if isinstance(created_at, str):
            created_at = datetime.fromisoformat(created_at.replace('Z', '+00:00'))
            
        updated_at = result.get('updated_at')
        if isinstance(updated_at, str):
            updated_at = datetime.fromisoformat(updated_at.replace('Z', '+00:00'))
            
        return cls(
            filename=result['filename'],
            repository=result['repository'],
            git_commit=result['git_commit'],
            code=result['code'],
            construct_type=result['construct_type'],
            name=result['name'],
            description=result['description'],
            embedding=result.get('embedding', []),  # Optional
            line_start=result['line_start'],
            line_end=result['line_end'],
            created_at=created_at or datetime.utcnow(),
            updated_at=updated_at or datetime.utcnow()
        )

class Import(BaseModel):
    """Pydantic model for code imports."""
    filename: str = Field(description="Source filename containing the import")
    repository: str = Field(description="Name of the repository")
    module_name: str = Field(description="Name of the imported module")
    import_type: str = Field(description="Type of import (import or from-import)")
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

# =============================================================================
# SQLAlchemy Models for Database Operations
# =============================================================================

class CodeEmbedding(Base):
    """SQLAlchemy model for storing code embeddings and metadata."""
    __tablename__ = 'code_embeddings'

    # Primary key as concatenation of filename + name + type
    id = Column(Text, primary_key=True)
    
    # Code metadata
    filename = Column(String, nullable=False)
    repository = Column(String, nullable=False)
    git_commit = Column(String, nullable=False)
    code = Column(Text, nullable=False)
    construct_type = Column(String, nullable=False)
    name = Column(String)
    description = Column(Text)
    
    # Vector embedding (768 dimensions for text-embedding-004)
    embedding = Column(Vector(768))
    
    # Location information
    line_start = Column(Integer, nullable=False)
    line_end = Column(Integer, nullable=False)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    @classmethod
    def create_indexes(cls, engine):
        """Create necessary indexes including vector similarity index if they don't exist."""
        # Enable pgvector extension if not already enabled
        with engine.connect() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector;"))
            
            # Check if table exists first
            result = conn.execute(text(
                "SELECT EXISTS (SELECT FROM pg_tables WHERE tablename = 'code_embeddings');"
            ))
            table_exists = result.scalar()
            
            if not table_exists:
                # Create tables via SQLAlchemy only if they don't exist
                Base.metadata.create_all(engine)
                
                # Create additional indexes
                conn.execute(text("""
                    -- Single-column indexes for common filters
                    CREATE INDEX IF NOT EXISTS idx_code_embeddings_filename 
                    ON code_embeddings(filename);

                    CREATE INDEX IF NOT EXISTS idx_code_embeddings_repository
                    ON code_embeddings(repository);

                    CREATE INDEX IF NOT EXISTS idx_code_embeddings_construct_type 
                    ON code_embeddings(construct_type);
                    
                    -- Composite index for repository+filename lookups
                    CREATE INDEX IF NOT EXISTS idx_code_embeddings_repo_file
                    ON code_embeddings(repository, filename);
                    
                    -- IVF index for fast similarity search (optional)
                    -- CREATE INDEX IF NOT EXISTS idx_code_embeddings_embedding 
                    -- ON code_embeddings USING ivfflat (embedding vector_cosine_ops)
                    -- WITH (lists = 100);
                """))
            conn.commit()
    
    @classmethod
    def store_embedding(cls, session, construct: CodeConstruct, embedding: List[float]) -> None:
        """Store or update a code construct with its embedding."""
        # Generate unique ID - include repository to avoid collisions across repos
        construct_id = f"{construct.repository}:{construct.filename}:{construct.name}:{construct.construct_type}"
        
        # Check if construct exists
        instance = session.query(cls).filter_by(id=construct_id).first()
        
        if instance:
            # Update existing
            for key, value in construct.model_dump().items():
                if key != 'created_at' and hasattr(instance, key):
                    setattr(instance, key, value)
            instance.embedding = embedding
            instance.updated_at = datetime.utcnow()
        else:
            # Create new
            instance = cls(
                id=construct_id,
                embedding=embedding,
                **construct.model_dump(exclude={'created_at', 'updated_at', 'embedding'})
            )
            session.add(instance)
    
    @classmethod
    def similar_code(cls, session, query_embedding: List[float], limit: int = 5,
                    min_similarity: float = 0.7, include_code: bool = True,
                    include_description: bool = True, include_embedding: bool = False,
                    for_reconstruction: bool = False) -> List[dict]:
        """Find similar code constructs using vector similarity search.
        
        Args:
            session: SQLAlchemy session
            query_embedding: Vector to compare against
            limit: Maximum number of results to return
            min_similarity: Minimum similarity threshold (0-1)
            include_code: Whether to include code content in results
            include_description: Whether to include descriptions in results
            include_embedding: Whether to include embeddings in results
            for_reconstruction: If True, returns all fields needed for CodeConstruct
        
        Returns:
            List of dictionaries containing matched code constructs
        """
        # Cast query embedding array to vector
        vector_param = cast(query_embedding, Vector)
        
        # Calculate cosine similarity
        similarity = (1 - func.cosine_distance(cls.embedding, vector_param)).cast(Float)
        
        # Build query dynamically based on requested fields
        query_fields = [
            cls.id,
            cls.filename,
            cls.repository,
            cls.construct_type,
            cls.name,
            cls.line_start,
            cls.line_end,
            similarity.label('similarity')
        ]
        
        if include_code or for_reconstruction:
            query_fields.append(cls.code)
        if include_description or for_reconstruction:
            query_fields.append(cls.description)
        if include_embedding or for_reconstruction:
            query_fields.append(cls.embedding)
        if for_reconstruction:
            query_fields.extend([
                cls.git_commit,
                cls.created_at,
                cls.updated_at
            ])
        
        results = (
            session.query(*query_fields)
            .filter(similarity > min_similarity)
            .order_by(similarity.desc())
            .limit(limit)
            .all()
        )
        
        return [
            {
                'id': result.id,
                'repository': result.repository,  # Always include repository
                'filename': result.filename,
                'type': result.construct_type,
                'name': result.name,
                'line_start': result.line_start,
                'line_end': result.line_end,
                'similarity': float(result.similarity),
                **({"code": result.code} if (include_code or for_reconstruction) else {}),
                **({"description": result.description} if (include_description or for_reconstruction) else {}),
                **({"embedding": result.embedding} if (include_embedding or for_reconstruction) else {}),
                **({"git_commit": result.git_commit,
                    "created_at": result.created_at,
                    "updated_at": result.updated_at,
                    "model_type": "CodeConstruct",  # For reconstruction hint
                    "construct_type": result.construct_type  # Original type
                    } if for_reconstruction else {})
            }
            for result in results
        ]
