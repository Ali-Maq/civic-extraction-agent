"""
Tool registry for CIViC extraction.

Centralizes MCP server construction so client/orchestrator wiring stays thin.
Currently uses existing tool implementations unchanged; future refactors can
swap in streamlined schemas without touching callers.
"""

from claude_agent_sdk import create_sdk_mcp_server

# Import tools directly from their source files
from tools.paper_tools import (
    get_paper_info,
    read_paper_page,
)
from tools.paper_content_tools import (
    save_paper_content,
    get_paper_content,
)
from tools.extraction_tools import (
    save_extraction_plan,
    get_extraction_plan,
    save_evidence_items,
    get_draft_extractions,
    save_critique,
    increment_iteration,
)
from tools.validation_tools import (
    check_actionability,
    validate_evidence_item,
)
from tools.normalization_tools import (
    normalize_extractions,
    finalize_extraction,
    get_tier2_coverage,
)


def build_civic_mcp_server():
    """Create the civic MCP server with all registered tools."""
    return create_sdk_mcp_server(
        name="civic_tools",
        version="2.0.0",
        tools=[
            get_paper_info,
            read_paper_page,
            save_paper_content,
            get_paper_content,
            save_extraction_plan,
            get_extraction_plan,
            check_actionability,
            validate_evidence_item,
            save_evidence_items,
            get_draft_extractions,
            save_critique,
            increment_iteration,
            normalize_extractions,
            finalize_extraction,
            get_tier2_coverage,
        ],
    )


# Allowed tool sets per phase for convenience (mirrors client defaults)
READER_TOOLS = [
    "mcp__civic_tools__get_paper_info",
    "mcp__civic_tools__read_paper_page",
    "mcp__civic_tools__save_paper_content",
]

ORCHESTRATOR_AND_SUBAGENT_TOOLS = [
    "Task",
    "mcp__civic_tools__get_paper_info",
    "mcp__civic_tools__get_paper_content",
    "mcp__civic_tools__save_extraction_plan",
    "mcp__civic_tools__get_extraction_plan",
    "mcp__civic_tools__check_actionability",
    "mcp__civic_tools__validate_evidence_item",
    "mcp__civic_tools__save_evidence_items",
    "mcp__civic_tools__get_draft_extractions",
    "mcp__civic_tools__save_critique",
    "mcp__civic_tools__increment_iteration",
    "mcp__civic_tools__normalize_extractions",
    "mcp__civic_tools__finalize_extraction",
    "mcp__civic_tools__get_tier2_coverage",
]
