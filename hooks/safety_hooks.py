"""
Safety Hooks
============

Safety controls for the extraction process.

NOTE: Ground truth is no longer in the extraction system.
These hooks are now simplified stubs for backwards compatibility.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


# =============================================================================
# LEGACY FUNCTIONS - Kept for backwards compatibility
# Ground truth is no longer in extraction context, so these are no-ops
# =============================================================================

def set_ground_truth_access(allowed: bool) -> None:
    """
    Legacy function - ground truth is no longer in extraction context.
    
    This function is kept for backwards compatibility with existing scripts
    that call it, but it does nothing since ground truth was removed.
    """
    pass  # No-op - ground truth doesn't exist in extraction context


def get_ground_truth_access() -> bool:
    """
    Legacy function - always returns False.
    
    Ground truth is not available during extraction.
    """
    return False


async def block_ground_truth(
    tool_input: dict[str, Any],
    tool_result: Any,
    context: Any
) -> dict[str, Any]:
    """
    Legacy hook function - kept for backwards compatibility.
    
    Ground truth tools are no longer registered, so this hook
    will never actually be triggered. It just passes through.
    
    Args:
        tool_input: The input to the tool
        tool_result: The result from the tool (unused)
        context: Hook context (unused)
    
    Returns:
        The unmodified tool_input
    """
    # No-op - just pass through
    # Ground truth tools aren't even registered anymore
    return tool_input


# Permission handler for tool tracing (if needed)
async def trace_permission_handler(
    tool_name: str,
    tool_input: dict[str, Any],
    context: dict[str, Any]
) -> dict[str, Any]:
    """
    Permission handler that logs tool calls.
    
    This can be used with can_use_tool in ClaudeAgentOptions for tracing.
    """
    from datetime import datetime
    
    # Log the tool call
    timestamp = datetime.now().isoformat()
    
    # Summarize input (avoid logging huge data like images)
    input_summary = {}
    if isinstance(tool_input, dict):
        if "page_num" in tool_input:
            input_summary["page_num"] = tool_input["page_num"]
        if "items" in tool_input:
            items = tool_input["items"]
            if isinstance(items, list):
                input_summary["items_count"] = len(items)
            elif isinstance(items, str):
                try:
                    import json
                    parsed = json.loads(items)
                    input_summary["items_count"] = len(parsed) if isinstance(parsed, list) else 1
                except:
                    input_summary["items"] = "string"
        if "overall_assessment" in tool_input:
            input_summary["assessment"] = tool_input["overall_assessment"]
    
    logger.info(f"[TOOL_CALL] {timestamp} | {tool_name} | {input_summary}")
    
    # Allow all tools - no ground truth to block anymore
    return {
        "behavior": "allow",
        "updatedInput": tool_input
    }