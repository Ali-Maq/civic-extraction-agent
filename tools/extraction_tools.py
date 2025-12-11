"""
Extraction State Tools
======================

MCP tools for managing extraction state (plans, items, critiques).
"""

import json
import os
from datetime import datetime
from pathlib import Path
from claude_agent_sdk import tool
from typing import Any

from context import require_context
from context.state import ExtractionPlan
from schemas import REQUIRED_FIELDS
from config import OUTPUTS_DIR

def _dump_checkpoint(filename: str, extra_data: dict = None):
    """Helper to save checkpoint to disk."""
    try:
        ctx = require_context()
        if not ctx.paper: return # Can't save if paper_id unknown
        
        paper_id = ctx.paper.paper_id
        checkpoint_dir = OUTPUTS_DIR / "checkpoints" / paper_id
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        checkpoint_path = checkpoint_dir / filename
        
        # Base data from context state
        data = {
            "paper_id": paper_id,
            "timestamp": datetime.now().isoformat(),
            # Include minimal context to allow resume
            "paper_content": ctx.paper_content,
            # "paper_content_text": ctx.paper_content_text, # Optional, can be regenerated
        }
        
        # Merge extra data
        if extra_data:
            data.update(extra_data)
            
        with open(checkpoint_path, "w") as f:
            json.dump(data, f, indent=2, default=str)
            
    except Exception as e:
        print(f"Warning: Failed to save checkpoint {filename}: {e}")

@tool(
    "save_extraction_plan",
    "Save the extraction strategy created by the Planner agent. Must be called before extraction.",
    {
        "paper_type": str,
        "expected_items": int,
        "key_variants": list,
        "key_therapies": list,
        "key_diseases": list,
        "focus_sections": list,
        "extraction_notes": str
    }
)
async def save_extraction_plan(args: dict[str, Any]) -> dict[str, Any]:
    """
    Save extraction plan to context.
    
    This should be called by the Planner agent after analyzing the paper.
    """
    ctx = require_context()
    
    plan = {
        "paper_type": args.get("paper_type", "UNKNOWN"),
        "expected_items": args.get("expected_items", 0),
        "key_variants": args.get("key_variants", []),
        "key_therapies": args.get("key_therapies", []),
        "key_diseases": args.get("key_diseases", []),
        "focus_sections": args.get("focus_sections", []),
        "extraction_notes": args.get("extraction_notes", ""),
    }
    
    # Validate paper_type
    valid_types = ["REVIEW", "PRIMARY", "CASE_REPORT", "GUIDELINE", "UNKNOWN"]
    if plan["paper_type"] not in valid_types:
        return {
            "content": [{
                "type": "text",
                "text": f"Error: Invalid paper_type '{plan['paper_type']}'. Must be one of {valid_types}"
            }],
            "is_error": True
        }
    
    # Save to context
    ctx.state.extraction_plan = ExtractionPlan(**plan)
    
    # Update paper info
    if ctx.paper:
        ctx.paper.paper_type = plan["paper_type"]
        ctx.paper.expected_item_count = plan["expected_items"]
    
    # SAVE CHECKPOINT 02
    _dump_checkpoint("02_planner_output.json", {"plan": plan})

    # Generate summary
    summary = f"Plan saved: {plan['paper_type']}, expecting {plan['expected_items']} items"
    
    if plan["paper_type"] == "REVIEW":
        summary += "\n⚠️ WARNING: Review papers typically yield 0-2 evidence items. Be very conservative."
    
    return {
        "content": [{"type": "text", "text": summary}]
    }


@tool(
    "get_extraction_plan",
    "Get the current extraction plan. Use this to understand what to extract.",
    {}
)
async def get_extraction_plan(args: dict[str, Any]) -> dict[str, Any]:
    """Get extraction plan from context."""
    ctx = require_context()
    
    if ctx.state.extraction_plan is None:
        return {
            "content": [{
                "type": "text",
                "text": "No extraction plan yet. The Planner agent should run first."
            }],
            "is_error": True
        }
    
    # Include critique feedback if available (for iterations)
    result = ctx.state.extraction_plan.copy()
    
    if ctx.state.critique:
        result["previous_critique"] = {
            "assessment": ctx.state.critique.get("overall_assessment"),
            "feedback": ctx.state.critique.get("item_feedback", []),
            "missing_items": ctx.state.critique.get("missing_items", []),
            "summary": ctx.state.critique.get("summary", "")
        }
        result["iteration"] = ctx.state.iteration_count
    
    return {
        "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
    }


@tool(
    "save_evidence_items",
    "Save extracted evidence items for Critic review. Each item must have the 8 required fields.",
    {"items": list}
)
async def save_evidence_items(args: dict[str, Any]) -> dict[str, Any]:
    """
    Save draft extractions to context.
    
    This should be called by the Extractor agent after finding evidence items.
    """
    ctx = require_context()
    items = args.get("items", [])
    
    # Handle case where items is passed as JSON string (MCP serialization issue)
    if isinstance(items, str):
        try:
            items = json.loads(items)
        except json.JSONDecodeError:
            return {
                "content": [{
                    "type": "text",
                    "text": "Error: items parameter must be a list of evidence items, received invalid JSON string"
                }],
                "is_error": True
            }
    
    # Ensure items is a list
    if not isinstance(items, list):
        return {
            "content": [{
                "type": "text",
                "text": f"Error: items must be a list, received {type(items).__name__}"
            }],
            "is_error": True
        }
    
    if not items:
        return {
            "content": [{"type": "text", "text": "Warning: No items provided. Saving empty list."}]
        }
    
    # Validate each item
    validation_summary = []
    for i, item in enumerate(items):
        missing = [f for f in REQUIRED_FIELDS if not item.get(f)]
        validation_summary.append({
            "index": i,
            "valid": len(missing) == 0,
            "missing_required": missing,
            "gene": item.get("feature_names", "?"),
            "variant": item.get("variant_names", "?"),
            "type": item.get("evidence_type", "?"),
        })
    
    # Save to context
    ctx.state.draft_extractions = items
    
    # SAVE CHECKPOINT 03
    _dump_checkpoint("03_extractor_output.json", {
        "extraction": {
            "draft_extractions": items,
            "iteration": ctx.state.iteration_count
        }
    })

    # Calculate stats
    valid_count = sum(1 for v in validation_summary if v["valid"])
    invalid_count = len(items) - valid_count
    
    result = {
        "saved": len(items),
        "valid": valid_count,
        "invalid": invalid_count,
        "items_summary": validation_summary
    }
    
    if invalid_count > 0:
        result["warning"] = f"{invalid_count} items have missing required fields. Please fix before submitting."
    
    return {
        "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
    }


@tool(
    "get_draft_extractions",
    "Get the current draft extractions and any previous critique for review or iteration.",
    {}
)
async def get_draft_extractions(args: dict[str, Any]) -> dict[str, Any]:
    """Get draft extractions and context for review."""
    ctx = require_context()
    
    result = {
        "count": len(ctx.state.draft_extractions),
        "items": ctx.state.draft_extractions,
        "iteration": ctx.state.iteration_count,
        "max_iterations": ctx.state.max_iterations,
    }
    
    # Include plan context
    if ctx.state.extraction_plan:
        # Handle Pydantic model or dict
        if hasattr(ctx.state.extraction_plan, "paper_type"):
            paper_type = ctx.state.extraction_plan.paper_type
            expected_items = ctx.state.extraction_plan.expected_items
        else:
            paper_type = ctx.state.extraction_plan.get("paper_type")
            expected_items = ctx.state.extraction_plan.get("expected_items")
            
        result["plan"] = {
            "paper_type": paper_type,
            "expected_items": expected_items,
        }
    
    # Include previous critique if any
    if ctx.state.critique:
        result["previous_critique"] = ctx.state.critique
    
    return {
        "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
    }


@tool(
    "save_critique",
    "Save the Critic's assessment of draft extractions. Use overall_assessment: APPROVE, NEEDS_REVISION, or REJECT.",
    {
        "overall_assessment": str,
        "item_feedback": list,
        "missing_items": list,
        "extra_items": list,
        "summary": str
    }
)
async def save_critique(args: dict[str, Any]) -> dict[str, Any]:
    """
    Save critique to context.
    
    This should be called by the Critic agent after reviewing extractions.
    """
    ctx = require_context()
    
    assessment = args.get("overall_assessment", "").upper()
    valid_assessments = ["APPROVE", "NEEDS_REVISION", "REJECT"]
    
    if assessment not in valid_assessments:
        return {
            "content": [{
                "type": "text",
                "text": f"Error: Invalid assessment '{assessment}'. Must be one of {valid_assessments}"
            }],
            "is_error": True
        }
    
    critique = {
        "overall_assessment": assessment,
        "item_feedback": args.get("item_feedback", []),
        "missing_items": args.get("missing_items", []),
        "extra_items": args.get("extra_items", []),
        "summary": args.get("summary", ""),
        "iteration": ctx.state.iteration_count,
    }
    
    # Save to context
    ctx.state.critique = critique
    
    # Determine recommendation
    needs_revision = assessment == "NEEDS_REVISION"
    can_iterate = ctx.state.iteration_count < ctx.state.max_iterations
    
    if assessment == "APPROVE":
        recommendation = "FINALIZE"
        message = "✅ Extraction approved. Ready to normalize and finalize."
    elif assessment == "REJECT":
        recommendation = "FINALIZE"
        message = "❌ Extraction rejected. Will finalize with current items (or empty)."
    elif needs_revision and can_iterate:
        recommendation = "ITERATE"
        message = f"🔄 Revision needed. Iteration {ctx.state.iteration_count + 1} of {ctx.state.max_iterations} available."
    else:
        recommendation = "FINALIZE"
        message = f"⚠️ Max iterations ({ctx.state.max_iterations}) reached. Will finalize with current items."
    
    result = {
        "assessment": assessment,
        "needs_revision": needs_revision,
        "can_iterate": can_iterate,
        "recommendation": recommendation,
        "message": message
    }
    
    return {
        "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
    }


@tool(
    "increment_iteration",
    "Increment the iteration counter before re-extraction. Call this before going back to extractor.",
    {}
)
async def increment_iteration(args: dict[str, Any]) -> dict[str, Any]:
    """Increment iteration count before re-extraction."""
    ctx = require_context()
    
    if ctx.state.iteration_count >= ctx.state.max_iterations:
        return {
            "content": [{
                "type": "text",
                "text": f"Error: Already at max iterations ({ctx.state.max_iterations}). Cannot iterate further."
            }],
            "is_error": True
        }
    
    ctx.state.iteration_count += 1
    
    return {
        "content": [{
            "type": "text",
            "text": f"Iteration {ctx.state.iteration_count} of {ctx.state.max_iterations}. Ready for re-extraction."
        }]
    }