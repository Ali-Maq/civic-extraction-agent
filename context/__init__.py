from .civic_context import CIViCContext
from .state import ExtractionState, PaperInfo

from typing import Optional

# Global context management
_current_context: Optional[CIViCContext] = None

def set_current_context(ctx: CIViCContext) -> None:
    """Set the global context for tools to access."""
    global _current_context
    _current_context = ctx

def get_current_context() -> Optional[CIViCContext]:
    """Get the current global context."""
    global _current_context
    return _current_context

def require_context() -> CIViCContext:
    """Get context or raise error if not set."""
    ctx = get_current_context()
    if ctx is None:
        raise RuntimeError("No context set. Call set_current_context() first.")
    return ctx

__all__ = [
    "CIViCContext",
    "ExtractionState", 
    "PaperInfo",
    "set_current_context",
    "get_current_context",
    "require_context",
]