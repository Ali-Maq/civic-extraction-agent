"""
Agents Module
=============

Agent definitions for CIViC evidence extraction.

NEW ARCHITECTURE (Reader-First):
    Reader → Planner → Extractor → Critic
    
The Reader extracts paper content ONCE, then all downstream agents
work from text context (no more redundant image reading).
"""

# New architecture imports
from .reader import (
    PaperContent,
    TableData,
    FigureData,
    StatisticData,
    SectionContent,
    READER_SYSTEM_PROMPT,
    READER_TASK_PROMPT,
    get_reader_tools,
    create_paper_content_from_tool_call,
)

from .orchestrator import (
    ORCHESTRATOR_SYSTEM_PROMPT,
    PLANNER_TASK_TEMPLATE,
    EXTRACTOR_TASK_TEMPLATE,
    CRITIC_TASK_TEMPLATE,
    format_plan_summary,
    format_critique_section,
)

from .planner import (
    PLANNER_SYSTEM_PROMPT,
    get_planner_tools,
)

from .extractor import (
    EXTRACTOR_SYSTEM_PROMPT,
    get_extractor_tools,
)

from .critic import (
    CRITIC_SYSTEM_PROMPT,
    get_critic_tools,
)

# Backwards compatibility aliases
ORCHESTRATOR_PROMPT = ORCHESTRATOR_SYSTEM_PROMPT
PLANNER_PROMPT = PLANNER_SYSTEM_PROMPT
EXTRACTOR_PROMPT = EXTRACTOR_SYSTEM_PROMPT
CRITIC_PROMPT = CRITIC_SYSTEM_PROMPT

# Legacy function stubs for backwards compatibility
def planner_agent(*args, **kwargs):
    """Legacy function - use new architecture with Reader-first pattern."""
    raise NotImplementedError(
        "planner_agent() is deprecated. Use the new Reader-first architecture. "
        "See docs/READER_FIRST_ARCHITECTURE.md"
    )

def extractor_agent(*args, **kwargs):
    """Legacy function - use new architecture with Reader-first pattern."""
    raise NotImplementedError(
        "extractor_agent() is deprecated. Use the new Reader-first architecture. "
        "See docs/READER_FIRST_ARCHITECTURE.md"
    )

def critic_agent(*args, **kwargs):
    """Legacy function - use new architecture with Reader-first pattern."""
    raise NotImplementedError(
        "critic_agent() is deprecated. Use the new Reader-first architecture. "
        "See docs/READER_FIRST_ARCHITECTURE.md"
    )


__all__ = [
    # New architecture - Reader
    "PaperContent",
    "TableData",
    "FigureData",
    "StatisticData",
    "SectionContent",
    "READER_SYSTEM_PROMPT",
    "READER_TASK_PROMPT",
    "get_reader_tools",
    "create_paper_content_from_tool_call",
    
    # New architecture - Orchestrator
    "ORCHESTRATOR_SYSTEM_PROMPT",
    "PLANNER_TASK_TEMPLATE",
    "EXTRACTOR_TASK_TEMPLATE",
    "CRITIC_TASK_TEMPLATE",
    "format_plan_summary",
    "format_critique_section",
    
    # New architecture - Planner
    "PLANNER_SYSTEM_PROMPT",
    "get_planner_tools",
    
    # New architecture - Extractor
    "EXTRACTOR_SYSTEM_PROMPT",
    "get_extractor_tools",
    
    # New architecture - Critic
    "CRITIC_SYSTEM_PROMPT",
    "get_critic_tools",
    
    # Backwards compatibility
    "ORCHESTRATOR_PROMPT",
    "PLANNER_PROMPT",
    "EXTRACTOR_PROMPT",
    "CRITIC_PROMPT",
    "planner_agent",
    "extractor_agent",
    "critic_agent",
]