"""
CIViC Extraction Tools Implementation
=====================================

Tool definitions for the Claude Agent SDK.
These wrappers connect the SDK's @tool system to the underlying implementation logic.
"""

from typing import Dict, Any, List
import json
from claude_agent_sdk import tool
from hooks.logging_hooks import logger
from context import get_current_context

# Import underlying implementations
from tools.paper_tools import (
    get_paper_info as _get_info,
    read_paper_page as _read_page,
)
from tools.extraction_tools import (
    save_extraction_plan as _save_plan,
    get_extraction_plan as _get_plan,
    save_evidence_items as _save_items,
    get_draft_extractions as _get_draft,
    save_critique as _save_critique,
    increment_iteration as _inc_iter
)
from tools.validation_tools import (
    check_actionability as _check_actionability,
    validate_evidence_item as _validate_item
)
from tools.normalization_tools import (
    normalize_extractions as _normalize,
    finalize_extraction as _finalize,
    get_tier2_coverage as _get_coverage
)
from tools.paper_content_tools import (
    _generate_paper_context_text
)


@tool(
    "get_paper_info",
    "Get metadata about the current paper",
    {}
)
async def get_paper_info(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get paper metadata."""
    result = _get_info()
    return {"content": [{"type": "text", "text": json.dumps(result)}]}

# Note: read_paper_page is already an @tool-decorated SdkMcpTool from tools.paper_tools
read_paper_page = _read_page


@tool(
    "save_paper_content",
    "Save complete extracted paper content (Reader agent only)",
    {
        "title": str,
        "authors": list,
        "journal": str,
        "year": int,
        "paper_type": str,
        "abstract": str,
        "sections": list,
        "tables": list,
        "figures": list,
        "statistics": list,
        "genes": list,
        "variants": list,
        "diseases": list,
        "therapies": list,
        "clinical_trials": list,
    }
)
async def save_paper_content(args: Dict[str, Any]) -> Dict[str, Any]:
    """Save extracted paper content from Reader agent."""
    context = get_current_context()
    
    # Store in context
    context.paper_content = {
        "title": args.get("title", ""),
        "authors": args.get("authors", []),
        "journal": args.get("journal", ""),
        "year": args.get("year", 0),
        "paper_type": args.get("paper_type", ""),
        "abstract": args.get("abstract", ""),
        "sections": args.get("sections", []),
        "tables": args.get("tables", []),
        "figures": args.get("figures", []),
        "statistics": args.get("statistics", []),
        "genes": args.get("genes", []),
        "variants": args.get("variants", []),
        "diseases": args.get("diseases", []),
        "therapies": args.get("therapies", []),
        "clinical_trials": args.get("clinical_trials", []),
    }
    
    # Generate text context
    context.paper_content_text = _generate_paper_context_text(context.paper_content)
    
    logger.info(f"[READER] Paper content saved: {args.get('title', 'Unknown')}")
    logger.info(f"[READER]   Type: {args.get('paper_type')}")
    logger.info(f"[READER]   Tables: {len(args.get('tables', []))}")
    logger.info(f"[READER]   Statistics: {len(args.get('statistics', []))}")
    
    return {
        "content": [{
            "type": "text",
            "text": json.dumps({
                "status": "saved",
                "title": args.get("title"),
                "paper_type": args.get("paper_type"),
                "tables_count": len(args.get("tables", [])),
                "statistics_count": len(args.get("statistics", [])),
            })
        }]
    }


@tool(
    "get_paper_content",
    "Get the extracted paper content (for Planner/Extractor/Critic)",
    {}
)
async def get_paper_content(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get paper content extracted by Reader."""
    context = get_current_context()
    
    if not hasattr(context, 'paper_content') or not context.paper_content:
        return {
            "content": [{
                "type": "text",
                "text": json.dumps({
                    "error": "Paper content not yet extracted. Reader agent must run first."
                })
            }]
        }
    
    return {
        "content": [{
            "type": "text",
            "text": context.paper_content_text
        }]
    }


@tool(
    "save_extraction_plan",
    "Save the extraction plan",
    {
        "paper_type": str,
        "expected_evidence_items": int,
        "key_variants": list,
        "key_therapies": list,
        "key_diseases": list,
        "focus_sections": list,
        "extraction_notes": str,
    }
)
async def save_extraction_plan(args: Dict[str, Any]) -> Dict[str, Any]:
    """Save extraction plan from Planner."""
    result = _save_plan(**args)
    return {"content": [{"type": "text", "text": json.dumps(result)}]}


@tool(
    "get_extraction_plan",
    "Get the current extraction plan",
    {}
)
async def get_extraction_plan(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get extraction plan."""
    result = _get_plan()
    return {"content": [{"type": "text", "text": json.dumps(result)}]}


@tool(
    "check_actionability",
    "Check if a claim is actionable clinical evidence",
    {"claim": str}
)
async def check_actionability(args: Dict[str, Any]) -> Dict[str, Any]:
    """Check actionability of a claim."""
    result = _check_actionability(args["claim"])
    return {"content": [{"type": "text", "text": json.dumps(result)}]}


@tool(
    "validate_evidence_item",
    "Validate an evidence item against CIViC rules",
    {"item": dict}
)
async def validate_evidence_item(args: Dict[str, Any]) -> Dict[str, Any]:
    """Validate evidence item."""
    result = _validate_item(args["item"])
    return {"content": [{"type": "text", "text": json.dumps(result)}]}


@tool(
    "save_evidence_items",
    "Save extracted evidence items",
    {"items": list}
)
async def save_evidence_items(args: Dict[str, Any]) -> Dict[str, Any]:
    """Save evidence items from Extractor."""
    result = _save_items(args["items"])
    return {"content": [{"type": "text", "text": json.dumps(result)}]}


@tool(
    "get_draft_extractions",
    "Get current draft extractions",
    {}
)
async def get_draft_extractions(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get draft extractions."""
    result = _get_draft()
    return {"content": [{"type": "text", "text": json.dumps(result)}]}


@tool(
    "save_critique",
    "Save critique results",
    {
        "overall_assessment": str,
        "item_feedback": str,
        "missing_items": str,
        "extra_items": str,
        "summary": str,
    }
)
async def save_critique(args: Dict[str, Any]) -> Dict[str, Any]:
    """Save critique from Critic."""
    result = _save_critique(**args)
    return {"content": [{"type": "text", "text": json.dumps(result)}]}


@tool(
    "increment_iteration",
    "Increment the iteration counter",
    {}
)
async def increment_iteration(args: Dict[str, Any]) -> Dict[str, Any]:
    """Increment iteration."""
    result = _inc_iter()
    return {"content": [{"type": "text", "text": json.dumps(result)}]}


@tool(
    "normalize_extractions",
    "Add database IDs to extractions",
    {}
)
async def normalize_extractions(args: Dict[str, Any]) -> Dict[str, Any]:
    """Normalize extractions."""
    result = _normalize()
    return {"content": [{"type": "text", "text": json.dumps(result)}]}


@tool(
    "finalize_extraction",
    "Finalize the extraction",
    {}
)
async def finalize_extraction(args: Dict[str, Any]) -> Dict[str, Any]:
    """Finalize extraction."""
    result = _finalize()
    return {"content": [{"type": "text", "text": json.dumps(result)}]}


@tool(
    "get_tier2_coverage",
    "Get Tier 2 field coverage statistics",
    {}
)
async def get_tier2_coverage(args: Dict[str, Any]) -> Dict[str, Any]:
    """Get tier 2 coverage."""
    result = _get_coverage()
    return {"content": [{"type": "text", "text": json.dumps(result)}]}

