import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional

from config import OUTPUTS_DIR


def _session_log_path(paper_id: str) -> Path:
    log_dir = Path(OUTPUTS_DIR) / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    return log_dir / f"{paper_id}_session.jsonl"


def log_event(paper_id: str, event: dict[str, Any]) -> None:
    """
    Append a structured event to the per-paper session log.
    """
    if not paper_id:
        return
    path = _session_log_path(paper_id)
    record = {
        "ts": datetime.utcnow().isoformat() + "Z",
        **event,
    }
    try:
        with path.open("a") as f:
            f.write(json.dumps(record) + "\n")
    except Exception:
        # Silent fail; logging should not break pipeline
        pass


def read_session(paper_id: str) -> list[dict[str, Any]]:
    """
    Read the session log for a paper, if present.
    """
    path = _session_log_path(paper_id)
    if not path.exists():
        return []
    out = []
    try:
        with path.open() as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    out.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
    except Exception:
        return []
    return out
