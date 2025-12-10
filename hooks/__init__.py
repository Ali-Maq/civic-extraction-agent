"""
Hooks Module
============

Safety and logging hooks for extraction workflow.

NOTE: The Claude Agent SDK has an internal bug where it sometimes
fails to parse hook return values. These errors are NON-FATAL and
appear as "Error in hook callback hook_1: ..." in the console.
The extraction continues successfully despite these errors.
"""

from .safety_hooks import (
    block_ground_truth,
    set_ground_truth_access,
    get_ground_truth_access,
)
from .logging_hooks import (
    log_tool_usage,
    log_tool_result,
    log_subagent_stop,
    start_new_log_session,
    get_log_file_path,
    get_tool_usage_log,
    clear_tool_usage_log,
    logger,
)

__all__ = [
    # Safety hooks
    "block_ground_truth",
    "set_ground_truth_access",
    "get_ground_truth_access",
    # Logging hooks
    "log_tool_usage",
    "log_tool_result",
    "log_subagent_stop",
    # Logging utilities
    "start_new_log_session",
    "get_log_file_path",
    "get_tool_usage_log",
    "clear_tool_usage_log",
    "logger",
]