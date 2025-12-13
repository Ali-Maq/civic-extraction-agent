#!/usr/bin/env python3
"""
Run Extraction - Reader-First Architecture
==========================================

This script executes the CIViC evidence extraction pipeline using the Claude Agent SDK.
It implements the Reader-First architecture where pages are read once as images,
and downstream agents (Planner, Extractor, Critic) work from the extracted text.
"""

import asyncio
import sys
import os
import json
import shutil
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import OUTPUTS_DIR, PAPERS_DIR
from context import CIViCContext, set_current_context
from context.state import ExtractionPlan
from hooks.logging_hooks import (
    start_new_log_session, clear_tool_usage_log, logger
)
from hooks.safety_hooks import set_ground_truth_access
from client import CivicExtractionClient


async def run_extraction(paper_id: str, papers_dir: str = None, verbose: bool = True) -> dict:
    """Run extraction with Reader-first architecture."""

    start_time = datetime.now()

    def _normalize_authors(value):
        if not value:
            return None
        if isinstance(value, list):
            value = ", ".join([str(v).strip() for v in value if str(v).strip()])
        else:
            value = str(value).strip()
        if not value or value.lower() == "unknown":
            return None
        return value

    def _normalize_year(value):
        if value is None:
            return None
        if isinstance(value, (int, float)):
            value = str(int(value))
        else:
            value = str(value).strip()
        if not value or value.lower() == "unknown":
            return None
        return value

    if papers_dir is None:
        papers_dir = PAPERS_DIR
    
    # Handle full path vs paper_id
    input_path = Path(paper_id)
    if input_path.is_file() and input_path.suffix.lower() == '.pdf':
        # User passed a PDF file directly.
        pdf_parent = input_path.parent
        pdf_stem = input_path.stem

        if pdf_parent.name == pdf_stem:
            # Already in a dedicated folder named after the paper_id.
            paper_id = pdf_parent.name
            papers_dir = pdf_parent.parent
        else:
            # Shared folder: create/use a dedicated subfolder to avoid checkpoint collisions.
            paper_id = pdf_stem
            target_folder = pdf_parent / paper_id
            target_folder.mkdir(parents=True, exist_ok=True)
            target_pdf = target_folder / input_path.name
            if not target_pdf.exists():
                shutil.copy2(input_path, target_pdf)
            papers_dir = pdf_parent
    elif input_path.is_dir():
        paper_id = input_path.name
        papers_dir = input_path.parent
    else:
        # It's likely just an ID string, keep defaults
        pass
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"CIViC Evidence Extraction (Reader-First)")
        print(f"Paper: {paper_id}")
        print(f"{'='*60}\n")
    
    # Initialize logging
    log_file = start_new_log_session(paper_id)
    clear_tool_usage_log()
    logger.info(f"=== NEW EXTRACTION SESSION: {paper_id} ===")
    
    # Block ground truth
    set_ground_truth_access(False)
    
    # Initialize context
    context = CIViCContext()
    if papers_dir:
        context.papers_dir = Path(papers_dir)
    
    # Load paper
    try:
        context.load_paper(paper_id) # CIViCContext defaults papers_dir to config.PAPERS_DIR if not passed
    except (ValueError, FileNotFoundError) as e:
        logger.error(f"Failed to load paper: {e}")
        return {"error": str(e), "paper_id": paper_id}
    
    set_current_context(context)
    
    if verbose:
        print(f"Loaded: {context.paper.num_pages} pages")
    
    logger.info(f"Paper loaded: {context.paper.num_pages} pages")
    
    # Initialize Client
    client = CivicExtractionClient(verbose=verbose)
    
    # Check for Reader Checkpoint
    checkpoint_dir = Path(OUTPUTS_DIR) / "checkpoints" / paper_id
    reader_checkpoint = checkpoint_dir / "01_reader_output.json"
    
    loaded_from_checkpoint = False
    
    if reader_checkpoint.exists():
        if verbose:
            print(f"\n--- Phase 1: Reader (SKIPPED - Found Checkpoint) ---")
            print(f"Loading from: {reader_checkpoint}")
        
        try:
            with open(reader_checkpoint, "r") as f:
                checkpoint_data = json.load(f)
                
            context.paper_content = checkpoint_data.get("paper_content")
            context.paper_content_text = checkpoint_data.get("paper_content_text", "")

            # Sync basic metadata from Reader into PaperInfo (author/year) when loading checkpoint
            pc = context.paper_content or {}
            if context.paper:
                if pc.get("authors"):
                    # authors may be list or string
                    if isinstance(pc["authors"], list):
                        context.paper.author = ", ".join(pc["authors"])
                    else:
                        context.paper.author = str(pc["authors"])
                if pc.get("year"):
                    context.paper.year = str(pc["year"])
            
            # Re-generate text if missing from checkpoint but content exists
            if not context.paper_content_text and context.paper_content:
                from tools.paper_content_tools import _generate_paper_context_text
                context.paper_content_text = _generate_paper_context_text(context.paper_content)
                
            if context.paper_content:
                loaded_from_checkpoint = True
                logger.info("Loaded Reader output from checkpoint")
                
                if verbose:
                    stats = context.paper_content.get('statistics', [])
                    tables = context.paper_content.get('tables', [])
                    print(f"✓ Loaded {len(stats)} stats, {len(tables)} tables")

                # Check for Planner Checkpoint (02)
                planner_checkpoint = checkpoint_dir / "02_planner_output.json"
                if planner_checkpoint.exists():
                    try:
                        with open(planner_checkpoint, "r") as f:
                            data = json.load(f)
                            if "plan" in data:
                                context.state.extraction_plan = ExtractionPlan(**data["plan"])
                                if verbose:
                                    print(f"✓ Loaded Extraction Plan from checkpoint")
                    except Exception as e:
                        logger.warning(f"Failed to load planner checkpoint: {e}")

                # Check for Extractor Checkpoint (03)
                extractor_checkpoint = checkpoint_dir / "03_extractor_output.json"
                if extractor_checkpoint.exists():
                    try:
                        with open(extractor_checkpoint, "r") as f:
                            data = json.load(f)
                            # Handle structure: {"extraction": {"draft_extractions": [...]}}
                            drafts = data.get("extraction", {}).get("draft_extractions", [])
                            if drafts:
                                context.state.draft_extractions = drafts
                                if verbose:
                                    print(f"✓ Loaded {len(drafts)} draft items from checkpoint")
                    except Exception as e:
                        logger.warning(f"Failed to load extractor checkpoint: {e}")

            else:
                logger.warning("Checkpoint found but missing content. Re-running Reader.")
                
        except Exception as e:
            logger.error(f"Failed to load checkpoint: {e}. Re-running Reader.")

    if not loaded_from_checkpoint:
        try:
            # Phase 1: Reader
            if verbose:
                print("\n--- Phase 1: Reader (Image Processing) ---")
            await client.run_reader_phase()
            
            # Verify content was extracted
            if not context.paper_content:
                raise RuntimeError("Reader agent failed to save paper content.")

            # Sync basic metadata from Reader into PaperInfo (author/year)
            pc = context.paper_content or {}
            if context.paper:
                if pc.get("authors"):
                    if isinstance(pc["authors"], list):
                        context.paper.author = ", ".join(pc["authors"])
                    else:
                        context.paper.author = str(pc["authors"])
                if pc.get("year"):
                    context.paper.year = str(pc["year"])
                
            if verbose:
                stats = context.paper_content.get('statistics', [])
                tables = context.paper_content.get('tables', [])
                print(f"✓ Extracted content: {len(stats)} stats, {len(tables)} tables")
            
            # SAVE CHECKPOINT
            try:
                checkpoint_dir.mkdir(parents=True, exist_ok=True)
                checkpoint_data = {
                    "paper_id": paper_id,
                    "timestamp": datetime.now().isoformat(),
                    "paper_content": context.paper_content,
                    "paper_content_text": context.paper_content_text,
                }
                with open(reader_checkpoint, "w") as f:
                    json.dump(checkpoint_data, f, indent=2, default=str)
                logger.info(f"Saved Reader checkpoint to {reader_checkpoint}")
            except Exception as e:
                logger.error(f"Failed to save checkpoint: {e}")

        except Exception as e:
            import traceback
            logger.error(f"Extraction error: {e}")
            if verbose:
                traceback.print_exc()
            return {"error": str(e), "paper_id": paper_id}
            
    # Phase 2: Orchestrator
    try:
        if verbose:
            print("\n--- Phase 2: Orchestrator (Text Analysis) ---")
        await client.run_orchestrator_phase()

        # If Critic requested revisions, let orchestrator loop until APPROVE or max_iterations
        # This relies on agent logic to delegate back to Extractor with the critique context.
        safety_counter = 0
        while (
            not context.state.is_complete
            and context.state.critique
            and context.state.critique.get("overall_assessment") == "NEEDS_REVISION"
            and context.state.iteration_count < context.state.max_iterations
        ):
            safety_counter += 1
            if verbose:
                print(f"\n--- Orchestrator re-run for revisions (iteration {context.state.iteration_count + 1}) ---")
            await client.run_orchestrator_phase()
            # Avoid runaway loops in case agents don't converge
            if safety_counter > context.state.max_iterations + 1:
                break

        # Guard: if orchestration never reached APPROVE/complete, allow additional runs
        guard_counter = 0
        critique_assessment = (context.state.critique or {}).get("overall_assessment")
        while (
            (
                not context.state.is_complete
                or critique_assessment is None
                or critique_assessment == "REJECT"
            )
            and context.state.iteration_count < context.state.max_iterations
        ):
            guard_counter += 1
            if verbose:
                reason = (
                    "incomplete run"
                    if not context.state.is_complete
                    else f"critique status: {critique_assessment or 'missing'}"
                )
                print(
                    "\n--- Orchestrator guard re-run "
                    f"(iteration {context.state.iteration_count + 1}, {reason}) ---"
                )
            await client.run_orchestrator_phase()
            critique_assessment = (context.state.critique or {}).get("overall_assessment")
            if guard_counter > context.state.max_iterations + 1:
                break

    except Exception as e:
        import traceback
        logger.error(f"Extraction error: {e}")
        if verbose:
            traceback.print_exc()
        return {"error": str(e), "paper_id": paper_id}

    # Compile results
    end_time = datetime.now()
    critique_assessment = (context.state.critique or {}).get("overall_assessment")
    is_finalized = context.state.is_complete and critique_assessment == "APPROVE"
    items = context.state.final_extractions if is_finalized else context.state.draft_extractions
    
    reader_metadata = getattr(context, "paper_content", {}) or {}
    reader_author = _normalize_authors(reader_metadata.get("authors"))
    reader_year = _normalize_year(reader_metadata.get("year"))

    paper_author = _normalize_authors(context.paper.author if context.paper else None)
    paper_year = _normalize_year(context.paper.year if context.paper else None)

    author_value = reader_author or paper_author or "Unknown"
    year_value = reader_year or paper_year or "Unknown"

    if context.paper:
        context.paper.author = author_value
        context.paper.year = year_value

    paper_type = (
        context.state.extraction_plan.paper_type if context.state.extraction_plan else None
    ) or (context.paper_content.get("paper_type") if context.paper_content else None)

    # Keep state.paper_info aligned with the latest metadata
    if context.state:
        if context.paper:
            context.state.paper_info = context.paper
        if isinstance(context.state.paper_info, dict):
            context.state.paper_info.update(
                {
                    "author": author_value,
                    "year": year_value,
                    "num_pages": context.paper.num_pages if context.paper else 0,
                    "paper_type": paper_type or "",
                }
            )

    results = {
        "paper_id": paper_id,
        "paper_info": {
            "author": author_value,
            "year": year_value,
            "num_pages": context.paper.num_pages,
            "paper_type": paper_type,
        },
        "extraction": {
            "items": len(items),
            "iterations": context.state.iteration_count,
            "complete": context.state.is_complete,
            "evidence_items": items
        },
        "plan": context.state.extraction_plan.__dict__ if context.state.extraction_plan else None,
        "final_critique": context.state.critique,
        "paper_content": getattr(context, 'paper_content', None),
        "timing": {
            "start": start_time.isoformat(),
            "end": end_time.isoformat(),
            "seconds": (end_time - start_time).total_seconds()
        },
        "log_file": str(log_file)
    }

    duration = (end_time - start_time).total_seconds()

    if not is_finalized:
        error_msg = (
            "Extraction incomplete or not approved after maximum iterations"
            if context.state.iteration_count >= context.state.max_iterations
            else "Extraction incomplete or missing approval"
        )
        logger.warning(
            f"=== PARTIAL: {len(items)} draft items in {duration:.1f}s | {error_msg} ==="
        )
        if verbose:
            print(f"\n⚠️ Partial run: {len(items)} draft items in {duration:.1f}s")
            print(f"Reason: {error_msg}")
        return {
            "error": error_msg,
            "paper_id": paper_id,
            "iterations": context.state.iteration_count,
            "critique": context.state.critique,
            "draft_extractions": context.state.draft_extractions,
        }

    # Save output (only when finalized and approved)
    output_path = Path(OUTPUTS_DIR) / f"{paper_id}_extraction.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)

    logger.info(f"=== COMPLETE: {len(items)} items in {duration:.1f}s ===")

    if verbose:
        print(f"\n✓ Complete: {len(items)} items in {duration:.1f}s")
        print(f"Output: {output_path}")
    
    return results


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python run_extraction.py <paper_id>")
        sys.exit(1)
    
    paper_input = sys.argv[1]
    
    try:
        result = asyncio.run(run_extraction(paper_input))
        if "error" in result:
            print(f"✗ Failed: {result['error']}")
            sys.exit(1)
    except KeyboardInterrupt:
        print("\nCancelled.")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Error: {e}")
        sys.exit(1)
