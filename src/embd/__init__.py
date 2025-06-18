"""Embedding generation and semantic code search system."""

from .embedding import EmbeddingGenerator
from .database_manager import DatabaseManager
from .processors.web import WebProcessor
from .processors.local import LocalFileProcessor
from .models import CodeConstruct, Import
from . import search

__all__ = [
    'EmbeddingGenerator',
    'DatabaseManager',
    'WebProcessor',
    'LocalFileProcessor',
    'CodeConstruct',
    'Import',
    'search'
]

__version__ = "0.2.0"
