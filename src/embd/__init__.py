"""
embd - A tool for embedding code constructs with Gemini and storing them in MongoDB
"""

from .models import CodeConstruct, Import
from .parser import parse_file, get_git_tracked_files

__version__ = "0.1.0"
__all__ = ["CodeConstruct", "Import", "parse_file", "get_git_tracked_files"]
