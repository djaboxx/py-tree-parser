"""Processor registry and base classes for content processing."""

from typing import Dict, Type, List
from .base import BaseProcessor

# Registry of available processors
_processors: Dict[str, Type[BaseProcessor]] = {}

def register_processor(name: str, processor_class: Type[BaseProcessor]) -> None:
    """Register a new processor.
    
    Args:
        name: Name to register the processor under
        processor_class: Processor class to register
    """
    if not issubclass(processor_class, BaseProcessor):
        raise ValueError(f"Processor class must inherit from BaseProcessor")
    _processors[name] = processor_class
    
def get_processor(name: str) -> Type[BaseProcessor]:
    """Get a registered processor by name.
    
    Args:
        name: Name of the processor to get
        
    Returns:
        The processor class
        
    Raises:
        KeyError: If no processor is registered with that name
    """
    try:
        return _processors[name]
    except KeyError:
        raise KeyError(f"No processor registered with name '{name}'")

def list_processors() -> List[str]:
    """Get list of registered processor names."""
    return list(_processors.keys())

# Register built-in processors
from .local import LocalFileProcessor
from .web import WebProcessor

register_processor('local', LocalFileProcessor)
register_processor('web', WebProcessor)
