"""Database management and operations for the embedding system."""
from typing import List, Tuple, Dict, Any, Optional
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn, TimeElapsedColumn
from sqlalchemy import create_engine, select
from sqlalchemy.orm import sessionmaker

from . import models
from . import config
from .models import CodeConstruct, CodeEmbedding

class DatabaseManager:
    """Manages all database operations including setup, storage, and retrieval."""

    def __init__(self):
        """Initialize the database manager with SQLAlchemy engine and session."""
        self.engine = create_engine(config.POSTGRES_URI)
        self.Session = sessionmaker(bind=self.engine)
        self.console = Console()

    def init_db(self):
        """Initialize database schema and required indexes."""
        # Import and create all models
        from . import models
        models.Base.metadata.create_all(self.engine)
        
        # Create vector similarity indexes
        self.init_indexes()

    def init_indexes(self):
        """Initialize vector similarity indexes."""
        models.CodeEmbedding.create_indexes(self.engine)
        self.console.print("[green]PostgreSQL tables and indexes created successfully[/green]")

    def store_constructs(self, constructs_data: List[Tuple[CodeConstruct, List[float]]],
                        show_progress: bool = True) -> None:
        """Store code constructs and their embeddings with optional progress tracking.
        
        Args:
            constructs_data: List of (CodeConstruct, embedding) tuples to store
            show_progress: Whether to show a progress bar
        """
        if show_progress:
            self._store_constructs_with_progress(constructs_data)
        else:
            self._store_constructs_simple(constructs_data)

    def _store_constructs_simple(self, constructs_data: List[Tuple[CodeConstruct, List[float]]]) -> None:
        """Store constructs without progress tracking."""
        with self.Session() as session:
            try:
                for construct, embedding in constructs_data:
                    CodeEmbedding.store_embedding(
                        session=session,
                        construct=construct,
                        embedding=embedding
                    )
                session.commit()
            except Exception as e:
                session.rollback()
                self.console.print(f"[bold red]Error storing constructs: {str(e)}")
                raise

    def _store_constructs_with_progress(self, constructs_data: List[Tuple[CodeConstruct, List[float]]]) -> None:
        """Store constructs with progress bar."""
        total_constructs = len(constructs_data)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            TextColumn("[cyan]{task.completed}/{task.total}"),
            TimeElapsedColumn(),
            console=self.console
        ) as progress:
            save_task = progress.add_task("[bold green]Saving to Database...", total=total_constructs)

            with self.Session() as session:
                try:
                    for construct, embedding in constructs_data:
                        CodeEmbedding.store_embedding(
                            session=session,
                            construct=construct,
                            embedding=embedding
                        )
                        progress.update(save_task, advance=1)
                    session.commit()
                except Exception as e:
                    session.rollback()
                    self.console.print(f"[bold red]Error storing constructs: {str(e)}")
                    raise

    def get_constructs_by_type(
        self,
        construct_type: str,
        limit: int = 10,
        include_code: bool = True,
        include_description: bool = True,
        include_embedding: bool = False
    ) -> List[dict]:
        """Retrieve code constructs of a specific type.
        
        Args:
            construct_type: Type of code construct to retrieve
            limit: Maximum number of results to return
            include_code: Whether to include code content
            include_description: Whether to include descriptions
            include_embedding: Whether to include embeddings
            
        Returns:
            List of dictionaries containing matched code constructs
        """
        with self.Session() as session:
            try:
                # Build query fields based on requested data
                query_fields = [
                    CodeEmbedding.id,
                    CodeEmbedding.filename,
                    CodeEmbedding.repository,
                    CodeEmbedding.construct_type,
                    CodeEmbedding.name,
                    CodeEmbedding.line_start,
                    CodeEmbedding.line_end,
                    CodeEmbedding.git_commit
                ]

                if include_code:
                    query_fields.append(CodeEmbedding.code)
                if include_description:
                    query_fields.append(CodeEmbedding.description)
                if include_embedding:
                    query_fields.append(CodeEmbedding.embedding)

                # Build and execute query
                stmt = select(*query_fields).where(
                    CodeEmbedding.construct_type == construct_type
                ).limit(limit)

                results = session.execute(stmt).mappings().all()
                return [dict(r) for r in results]

            except Exception as e:
                self.console.print(f"[bold red]Error retrieving constructs: {str(e)}")
                raise

    def search_similar_code(
        self,
        query_embedding: List[float],
        limit: int = 5,
        min_similarity: float = 0.7,
        include_code: bool = True,
        include_description: bool = True,
        include_embedding: bool = False,
        for_reconstruction: bool = False,
        construct_type: Optional[str] = None
    ) -> List[dict]:
        """Search for similar code using vector similarity.
        
        Args:
            query_embedding: The query embedding vector
            limit: Maximum number of results
            min_similarity: Minimum similarity threshold (0-1)
            include_code: Whether to include code content in results
            include_description: Whether to include descriptions in results
            include_embedding: Whether to include embeddings in results 
            for_reconstruction: Whether to include all fields needed for reconstruction
            construct_type: Optional filter by construct type
            
        Returns:
            List of similar code constructs with similarity scores
        """
        with self.Session() as session:
            query = models.CodeEmbedding.similar_code(
                session=session,
                query_embedding=query_embedding,
                limit=limit,
                min_similarity=min_similarity,
                include_code=include_code,
                include_description=include_description,
                include_embedding=include_embedding,
                for_reconstruction=for_reconstruction
            )
            # If construct_type is provided, filter results
            if construct_type:
                query = [r for r in query if r['type'] == construct_type]
            return query[:limit]

    def clear_constructs(self, repository: Optional[str] = None) -> None:
        """Clear all constructs from the database, optionally filtering by repository.
        
        Args:
            repository: Optional repository name to clear constructs for
        """
        with self.Session() as session:
            try:
                if repository:
                    session.query(CodeEmbedding).filter(
                        CodeEmbedding.repository == repository
                    ).delete()
                else:
                    session.query(CodeEmbedding).delete()
                session.commit()
            except Exception as e:
                session.rollback()
                self.console.print(f"[bold red]Error clearing constructs: {str(e)}")
                raise
