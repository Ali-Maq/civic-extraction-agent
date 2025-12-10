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
from datetime import datetime
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from config import OUTPUTS_DIR, PAPERS_DIR
from context import CIViCContext, set_current_context
from hooks.logging_hooks import (
    start_new_log_session, clear_tool_usage_log, logger
)
from hooks.safety_hooks import set_ground_truth_access
from client import CivicExtractionClient


async def run_extraction(paper_id: str, papers_dir: str = None, verbose: bool = True) -> dict:
    """Run extraction with Reader-first architecture."""
    
    start_time = datetime.now()
    
    if papers_dir is None:
        papers_dir = PAPERS_DIR
    
    # Handle full path vs paper_id
    input_path = Path(paper_id)
    if input_path.is_file() and input_path.suffix.lower() == '.pdf':
        # User passed a PDF file directly
        # We need to set papers_dir to the parent of this file's folder, 
        # and paper_id to the folder name (assuming CIViC structure: folder/file.pdf)
        # OR if the file is just loose, we treat its parent as papers_dir.
        
        # However, context.load_paper expects paper_id to be a folder name inside papers_dir.
        # So if we have /a/b/paper/paper.pdf
        # papers_dir = /a/b
        # paper_id = paper
        
        # If the PDF name doesn't match folder name, context.load_paper might fail finding the PDF 
        # unless we adjust it. But usually CIViC structure is strict.
        # Let's assume input is /path/to/PAPER_ID/PAPER_ID.pdf
        
        paper_id = input_path.parent.name
        papers_dir = input_path.parent.parent
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
    
    try:
        # Phase 1: Reader
        if verbose:
            print("\n--- Phase 1: Reader (Image Processing) ---")
        await client.run_reader_phase()
        
        # Verify content was extracted
        if not context.paper_content:
            raise RuntimeError("Reader agent failed to save paper content.")
            
        if verbose:
            print(f"✓ Extracted content: {len(context.paper_content.get('statistics', []))} stats, {len(context.paper_content.get('tables', []))} tables")
        
        # Phase 2: Orchestrator
        if verbose:
            print("\n--- Phase 2: Orchestrator (Text Analysis) ---")
        await client.run_orchestrator_phase()
        
    except Exception as e:
        import traceback
        logger.error(f"Extraction error: {e}")
        if verbose:
            traceback.print_exc()
        return {"error": str(e), "paper_id": paper_id}
    
    # Compile results
    end_time = datetime.now()
    items = context.state.final_extractions if context.state.is_complete else context.state.draft_extractions
    
    results = {
        "paper_id": paper_id,
        "paper_info": {
            "author": context.paper.author,
            "year": context.paper.year,
            "num_pages": context.paper.num_pages,
            "paper_type": context.state.extraction_plan.get("paper_type") if context.state.extraction_plan else None
        },
        "extraction": {
            "items": len(items),
            "iterations": context.state.iteration_count,
            "complete": context.state.is_complete,
            "evidence_items": items
        },
        "plan": context.state.extraction_plan,
        "final_critique": context.state.critique,
        "paper_content": getattr(context, 'paper_content', None),
        "timing": {
            "start": start_time.isoformat(),
            "end": end_time.isoformat(),
            "seconds": (end_time - start_time).total_seconds()
        },
        "log_file": str(log_file)
    }
    
    # Save output
    output_path = Path(OUTPUTS_DIR) / f"{paper_id}_extraction.json"
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    duration = (end_time - start_time).total_seconds()
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
