"""CLI module for the embd package."""

from .base import ProcessorCLI
from .repo import main as repo_main
from .web import main as web_main
from .search import main as search_main

__all__ = ['ProcessorCLI', 'repo_main', 'web_main', 'search_main']
