"""
Logging Hooks
=============

Hooks for logging tool usage and agent activity.
Provides audit trail for debugging and analysis.

NOTE: The Claude Agent SDK has an internal bug where it sometimes
passes string data to hooks and then fails to parse the return value.
These errors are NON-FATAL - the extraction continues successfully.
The errors appear as "Error in hook callback hook_1: ..." in the console.
This is a known SDK issue, not a problem with our code.
"""

import json
import logging
from datetime import datetime
from pathlib import Path
from typing import Any, Optional, Dict, Union

# =============================================================================
# LOGGING CONFIGURATION
# =============================================================================

# Create logs directory
LOGS_DIR = Path(__file__).parent.parent / "logs"
LOGS_DIR.mkdir(exist_ok=True)

# Configure logger with both file and console handlers
logger = logging.getLogger("civic.hooks")
logger.setLevel(logging.DEBUG)

# Prevent duplicate handlers if module is reloaded
if not logger.handlers:
    # File handler - detailed logs
    log_file = LOGS_DIR / f"extraction_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    # Console handler - less verbose
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # Log startup
    logger.info(f"Logging initialized. Log file: {log_file}")

# Track tool usage for session
_tool_usage_log: list[dict] = []

# Track current log file path
_current_log_file: Optional[Path] = log_file if 'log_file' in dir() else None


def get_log_file_path() -> Optional[Path]:
    """Get the current log file path."""
    return _current_log_file


def start_new_log_session(paper_id: str) -> Path:
    """Start a new log file for a specific paper extraction."""
    global _current_log_file
    
    # Create paper-specific log file
    log_file = LOGS_DIR / f"{paper_id}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"
    
    # Remove old file handlers and add new one
    for handler in logger.handlers[:]:
        if isinstance(handler, logging.FileHandler):
            handler.close()
            logger.removeHandler(handler)
    
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_formatter = logging.Formatter(
        '%(asctime)s | %(levelname)-8s | %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_formatter)
    logger.addHandler(file_handler)
    
    _current_log_file = log_file
    logger.info(f"=== NEW EXTRACTION SESSION: {paper_id} ===")
    
    return log_file


def get_tool_usage_log() -> list[dict]:
    """Get the current session's tool usage log."""
    return _tool_usage_log.copy()


def clear_tool_usage_log() -> None:
    """Clear the tool usage log for a new session."""
    global _tool_usage_log
    _tool_usage_log = []


async def log_tool_usage(
    input_data: Union[Dict[str, Any], str],
    tool_use_id: Optional[str],
    context: Any
) -> Dict[str, Any]:
    """
    PreToolUse hook that logs all tool invocations.
    
    Creates an audit trail of what tools were called and when.
    Useful for debugging and understanding agent behavior.
    """
    # Handle case where input_data is a string (SDK sometimes passes serialized data)
    if isinstance(input_data, str):
        try:
            import json
            input_data = json.loads(input_data)
        except (json.JSONDecodeError, TypeError):
            # If it's not JSON, just log what we can
            log_msg = f"[TOOL] (unparseable input: {str(input_data)[:50]}...)"
            logger.info(log_msg)
            print(log_msg)
            return {}
    
    if not isinstance(input_data, dict):
        return {}
    
    tool_name = input_data.get("tool_name", "unknown")
    tool_input = input_data.get("tool_input", {})
    
    # Create log entry
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "tool_name": tool_name,
        "tool_use_id": tool_use_id,
        "input_summary": _summarize_input(tool_name, tool_input)
    }
    
    _tool_usage_log.append(log_entry)
    
    # Format log message
    log_msg = f"[TOOL] {tool_name}"
    
    # Add relevant details based on tool type
    if "page_num" in tool_input:
        log_msg += f" (page {tool_input['page_num']})"
    elif "items" in tool_input:
        log_msg += f" ({len(tool_input['items'])} items)"
    elif "item" in tool_input:
        gene = tool_input.get("item", {}).get("feature_names", "?")
        variant = tool_input.get("item", {}).get("variant_names", "?")
        log_msg += f" ({gene} {variant})"
    
    # Log to both logger and console
    logger.info(log_msg)
    print(log_msg)
    
    # Don't block - return empty dict
    return {}


async def log_tool_result(
    input_data: Union[Dict[str, Any], str],
    tool_use_id: Optional[str],
    context: Any
) -> Dict[str, Any]:
    """
    PostToolUse hook that logs tool results.
    
    Can be used to track success/failure of tool calls.
    """
    # Handle string input
    if isinstance(input_data, str):
        try:
            import json
            input_data = json.loads(input_data)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    if not isinstance(input_data, dict):
        return {}
    
    tool_name = input_data.get("tool_name", "unknown")
    result = input_data.get("result", {})
    
    is_error = result.get("is_error", False)

    # Extract a small snippet for visibility
    snippet = result.get("content", [{}])
    if isinstance(snippet, list) and snippet:
        snippet_text = snippet[0].get("text", "")
    else:
        snippet_text = str(result)

    log_msg = f"[TOOL RESULT] {tool_name} | error={is_error} | snippet={snippet_text[:200]}"
    logger.info(log_msg)
    print(log_msg)

    if is_error:
        error_msg = f"[TOOL ERROR] {tool_name}: {snippet_text[:300]}"
        logger.warning(error_msg)
        print(error_msg)
    
    return {}


async def log_subagent_stop(
    input_data: Union[Dict[str, Any], str],
    tool_use_id: Optional[str],
    context: Any
) -> Dict[str, Any]:
    """
    SubagentStop hook that logs when subagents complete.
    
    Useful for tracking workflow progress.
    """
    # Handle string input
    if isinstance(input_data, str):
        try:
            import json
            input_data = json.loads(input_data)
        except (json.JSONDecodeError, TypeError):
            return {}
    
    if not isinstance(input_data, dict):
        return {}
    
    agent_name = input_data.get("agent_name", "unknown")
    stop_reason = input_data.get("stop_reason", "completed")
    
    log_entry = {
        "timestamp": datetime.now().isoformat(),
        "event": "subagent_stop",
        "agent_name": agent_name,
        "stop_reason": stop_reason
    }
    
    _tool_usage_log.append(log_entry)
    
    log_msg = f"[SUBAGENT] {agent_name} - {stop_reason}"
    logger.info(log_msg)
    print(log_msg)
    
    return {}


def _summarize_input(tool_name: str, tool_input: dict) -> str:
    """Create a brief summary of tool input for logging."""
    if not isinstance(tool_input, dict):
        return "unknown"
    
    if "page_num" in tool_input:
        return f"page={tool_input['page_num']}"
    
    if "items" in tool_input:
        items = tool_input['items']
        if isinstance(items, list):
            return f"items={len(items)}"
        elif isinstance(items, str):
            # Items passed as JSON string - try to count
            try:
                import json
                parsed = json.loads(items)
                if isinstance(parsed, list):
                    return f"items={len(parsed)}"
            except:
                pass
            return f"items=string({len(items)} chars)"
        return f"items={type(items).__name__}"
    
    if "item" in tool_input:
        item = tool_input["item"]
        if isinstance(item, dict):
            return f"gene={item.get('feature_names', '?')}, variant={item.get('variant_names', '?')}"
        return "item=?"
    
    if "paper_type" in tool_input:
        return f"type={tool_input['paper_type']}, expected={tool_input.get('expected_items', '?')}"
    
    if "overall_assessment" in tool_input:
        return f"assessment={tool_input['overall_assessment']}"
    
    if "claim" in tool_input:
        claim = tool_input["claim"]
        if isinstance(claim, str):
            return f"claim={claim[:50]}..." if len(claim) > 50 else f"claim={claim}"
        return "claim=?"
    
    # Default: return keys
    try:
        return f"keys={list(tool_input.keys())}"
    except:
        return "unknown"