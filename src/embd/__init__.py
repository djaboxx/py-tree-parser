"""Embedding generation and semantic code search system."""

from .embedding import EmbeddingGenerator
from .database_manager import DatabaseManager
from .processors import get_processor, list_processors, register_processor
from .processors.base import BaseProcessor
from .models import CodeConstruct, Import

# For backward compatibility
WebProcessor = get_processor('web')
LocalFileProcessor = get_processor('local')

__all__ = [
    'EmbeddingGenerator',
    'DatabaseManager',
    'WebProcessor',
    'LocalFileProcessor',
    'CodeConstruct',
    'Import',
    'BaseProcessor',
    'get_processor',
    'list_processors',
    'register_processor'
]

__version__ = "0.3.0"
