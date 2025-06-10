"""
embd - A tool for embedding code constructs with Gemini and storing them in MongoDB
"""

from .models import CodeConstruct, Import
from .parser import parse_file, parse_file_as_whole, get_git_tracked_files

# Import web processing functionality if dependencies are available
try:
    from .web_parser import process_web_document, parse_html_document, parse_web_markdown
    __all__ = ["CodeConstruct", "Import", "parse_file", "parse_file_as_whole", "get_git_tracked_files", 
              "process_web_document", "parse_html_document", "parse_web_markdown"]
except ImportError:
    __all__ = ["CodeConstruct", "Import", "parse_file", "parse_file_as_whole", "get_git_tracked_files"]

__version__ = "0.1.0"
