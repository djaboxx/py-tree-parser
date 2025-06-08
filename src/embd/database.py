"""SQLAlchemy database configuration and models."""
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, DeclarativeBase
from . import config

# Create SQLAlchemy engine
engine = create_engine(config.POSTGRES_URI)

# Create session factory
Session = sessionmaker(bind=engine)

# Base class for declarative models
class Base(DeclarativeBase):
    """Base class for all SQLAlchemy models."""
    pass

# Create all tables
def init_db():
    """Initialize database schema."""
    # Import all models that inherit from Base
    from . import models
    
    Base.metadata.create_all(engine)
