#!/usr/bin/env python
"""
OncoCITE extraction — paper-spec CLI entry point (Claude Agent SDK).

Matches the install-and-run commands documented in the OncoCITE manuscript
(Supplementary Note S2.3):

    pip install -r requirements.txt
    python run_extraction.py --input paper.pdf --output results/

Thin wrapper around `scripts/run_extraction.py` that accepts a direct PDF
path. For the full CLI (paper_id lookup against a papers directory,
checkpoint resume, etc.) see `scripts/run_extraction.py`.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

# Re-use the full pipeline entry point already shipped under scripts/
from scripts.run_extraction import run_extraction as _run_extraction  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(
        prog="run_extraction.py",
        description=(
            "Run the OncoCITE (Claude Agent SDK) multi-agent extraction "
            "pipeline on a scientific paper PDF and emit a structured "
            "evidence-items JSON."
        ),
    )
    parser.add_argument(
        "--input",
        required=True,
        type=Path,
        help="Path to the source PDF file.",
    )
    parser.add_argument(
        "--output",
        required=True,
        type=Path,
        help="Output directory (will be created if it does not exist).",
    )
    parser.add_argument(
        "--paper-id",
        default=None,
        help="Optional paper identifier; defaults to the PDF filename stem.",
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="Disable verbose logging.",
    )
    args = parser.parse_args()

    pdf_path: Path = args.input.expanduser().resolve()
    output_dir: Path = args.output.expanduser().resolve()

    if not pdf_path.is_file():
        print(f"ERROR: input PDF not found: {pdf_path}", file=sys.stderr)
        return 2

    paper_id = args.paper_id or pdf_path.stem
    output_dir.mkdir(parents=True, exist_ok=True)

    # Route OUTPUTS_DIR at the requested location for this invocation.
    os.environ.setdefault("OUTPUTS_DIR", str(output_dir))

    # Stage the PDF into a dedicated folder so the underlying pipeline's
    # paper_id ↔ folder convention is satisfied.
    staging_root = output_dir / ".staging"
    staging_root.mkdir(parents=True, exist_ok=True)
    paper_folder = staging_root / paper_id
    paper_folder.mkdir(parents=True, exist_ok=True)
    staged_pdf = paper_folder / f"{paper_id}.pdf"
    if not staged_pdf.exists():
        shutil.copy2(pdf_path, staged_pdf)

    verbose = not args.quiet
    print("=" * 70)
    print("OncoCITE — CIViC evidence extraction (Claude Agent SDK)")
    print("=" * 70)
    print(f"Input PDF:  {pdf_path}")
    print(f"Paper ID:   {paper_id}")
    print(f"Output dir: {output_dir}")
    print("=" * 70)

    started = datetime.now()
    result = asyncio.run(
        _run_extraction(
            paper_id=paper_id,
            papers_dir=str(staging_root),
            verbose=verbose,
        )
    )
    duration = (datetime.now() - started).total_seconds()

    final_path = output_dir / f"{paper_id}_extraction.json"
    payload = {
        "paper_id": paper_id,
        "pdf_path": str(pdf_path),
        "duration_seconds": duration,
        "extraction": result,
    }
    final_path.write_text(json.dumps(payload, indent=2, default=str))

    items = (
        (result or {}).get("final_extractions")
        or (result or {}).get("evidence_items")
        or (result or {}).get("draft_extractions")
        or []
    )
    print()
    print(f"Done in {duration:.1f}s — {len(items)} evidence items → {final_path}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
