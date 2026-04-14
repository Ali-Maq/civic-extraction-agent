"""
Workflow state tools (paper Supplementary Table S15).

Four MCP tools that the primary repo exposes alongside the existing
extraction / validation / normalization tools so the full set of 22
specialized tools from Table S15 is registered on the MCP server:

    get_workflow_status    — retrieve phase/iteration/paper_id
    log_agent_action       — append to the audit trail
    save_checkpoint        — save intermediate state under a label
    restore_checkpoint     — restore saved state by label

State is held in an in-memory dict per MCP server process. Persistent
checkpoint storage for long-running extractions is handled separately by
the Claude Agent SDK's `outputs/checkpoints/{paper_id}/*.json` flow.
"""

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, Optional

from claude_agent_sdk import tool


_WORKFLOW_STATE: Dict[str, Any] = {
    "current_phase": "idle",
    "iteration": 0,
    "last_update": None,
    "paper_id": None,
    "checkpoints": {},
    "agent_log": [],
}


def _touch(paper_id: Optional[str] = None, phase: Optional[str] = None) -> None:
    _WORKFLOW_STATE["last_update"] = datetime.now(timezone.utc).isoformat()
    if paper_id is not None:
        _WORKFLOW_STATE["paper_id"] = paper_id
    if phase is not None:
        _WORKFLOW_STATE["current_phase"] = phase


@tool("get_workflow_status", "Retrieve the current workflow phase, iteration, and paper_id.", {})
async def get_workflow_status(_args: Dict[str, Any]) -> Dict[str, Any]:
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(
                    {
                        "current_phase": _WORKFLOW_STATE["current_phase"],
                        "iteration": _WORKFLOW_STATE["iteration"],
                        "last_update": _WORKFLOW_STATE["last_update"],
                        "paper_id": _WORKFLOW_STATE["paper_id"],
                        "checkpoints": sorted(_WORKFLOW_STATE["checkpoints"].keys()),
                        "agent_log_entries": len(_WORKFLOW_STATE["agent_log"]),
                    }
                ),
            }
        ]
    }


@tool(
    "log_agent_action",
    "Append an entry to the audit trail of agent actions.",
    {"agent": str, "action": str, "detail": str},
)
async def log_agent_action(args: Dict[str, Any]) -> Dict[str, Any]:
    entry = {
        "agent": args.get("agent"),
        "action": args.get("action"),
        "detail": args.get("detail"),
        "ts": datetime.now(timezone.utc).isoformat(),
    }
    _WORKFLOW_STATE["agent_log"].append(entry)
    _touch()
    return {
        "content": [
            {"type": "text", "text": json.dumps({"logged": True, "entries": len(_WORKFLOW_STATE["agent_log"])})}
        ]
    }


@tool(
    "save_checkpoint",
    "Save an intermediate workflow checkpoint under the given label.",
    {"label": str, "state": dict},
)
async def save_checkpoint(args: Dict[str, Any]) -> Dict[str, Any]:
    label = args["label"]
    _WORKFLOW_STATE["checkpoints"][label] = args.get("state", {})
    _touch()
    return {
        "content": [
            {"type": "text", "text": json.dumps({"saved": True, "label": label})}
        ]
    }


@tool(
    "restore_checkpoint",
    "Restore a previously saved workflow checkpoint by label.",
    {"label": str},
)
async def restore_checkpoint(args: Dict[str, Any]) -> Dict[str, Any]:
    label = args["label"]
    if label not in _WORKFLOW_STATE["checkpoints"]:
        return {
            "content": [
                {"type": "text", "text": json.dumps({"restored": False, "reason": f"no checkpoint named {label!r}"})}
            ]
        }
    _touch()
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps({"restored": True, "label": label, "state": _WORKFLOW_STATE["checkpoints"][label]}),
            }
        ]
    }
