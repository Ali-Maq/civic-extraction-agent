"""
Tools Module
============

MCP tools for CIViC evidence extraction.
"""

from claude_agent_sdk import create_sdk_mcp_server

from .paper_tools import read_paper_page, get_paper_info
from .validation_tools import validate_evidence_item, check_actionability
from .extraction_tools import (
    save_extraction_plan,
    save_evidence_items,
    save_critique,
    get_extraction_plan,
    get_draft_extractions,
    increment_iteration,
)
from .normalization_tools import (
    finalize_extraction,
    get_tier2_coverage,
)


def create_civic_tools_server():
    """
    Create MCP server with all CIViC extraction tools.
    
    Returns:
        MCP server instance ready for use with ClaudeSDKClient
    """
    return create_sdk_mcp_server(
        name="civic_tools",
        version="1.0.0",
        tools=[
            # Paper reading
            read_paper_page,
            get_paper_info,
            
            # Validation
            validate_evidence_item,
            check_actionability,
            
            # State management
            save_extraction_plan,
            save_evidence_items,
            save_critique,
            get_extraction_plan,
            get_draft_extractions,
            increment_iteration,
            
            # Normalization
            finalize_extraction,
            get_tier2_coverage,
        ]
    )


__all__ = [
    "create_civic_tools_server",
    # Paper tools
    "read_paper_page",
    "get_paper_info",
    # Validation tools
    "validate_evidence_item",
    "check_actionability",
    # Extraction tools
    "save_extraction_plan",
    "save_evidence_items",
    "save_critique",
    "get_extraction_plan",
    "get_draft_extractions",
    "increment_iteration",
    # Normalization tools
    "finalize_extraction",
    "get_tier2_coverage",
]