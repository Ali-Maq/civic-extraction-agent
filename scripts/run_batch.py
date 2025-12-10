#!/usr/bin/env python3
"""
Batch Extraction Runner
=======================

Process multiple papers in sequence or parallel.

Usage:
    python scripts/run_batch.py paper1 paper2 paper3
    python scripts/run_batch.py --all --limit 10
    python scripts/run_batch.py --file papers.txt
"""

import asyncio
import json
import sys
import argparse
from pathlib import Path
from datetime import datetime

from config import PAPERS_DIR, OUTPUTS_DIR
from context import CIViCContext
from scripts.run_extraction import run_extraction


def get_all_paper_ids(limit: int | None = None) -> list[str]:
    """Get all paper IDs from the papers directory."""
    paper_dirs = [d for d in PAPERS_DIR.iterdir() if d.is_dir()]
    paper_ids = sorted([d.name for d in paper_dirs])
    
    if limit:
        paper_ids = paper_ids[:limit]
    
    return paper_ids


def get_papers_from_file(filepath: str) -> list[str]:
    """Read paper IDs from a file (one per line)."""
    with open(filepath) as f:
        return [line.strip() for line in f if line.strip() and not line.startswith("#")]


def get_papers_with_ground_truth() -> list[str]:
    """Get paper IDs that have ground truth available."""
    context = CIViCContext()
    context.load_ground_truth()
    
    if context.ground_truth_df is None:
        return []
    
    paper_ids = context.ground_truth_df["paper_folder"].unique().tolist()
    return sorted(paper_ids)


async def run_batch(
    paper_ids: list[str],
    verbose: bool = True,
    stop_on_error: bool = False
) -> dict:
    """
    Run extraction on multiple papers.
    
    Args:
        paper_ids: List of paper IDs to process
        verbose: Print progress
        stop_on_error: Stop if any paper fails
        
    Returns:
        Summary of batch results
    """
    start_time = datetime.now()
    
    results = {
        "papers_requested": len(paper_ids),
        "papers_completed": 0,
        "papers_failed": 0,
        "total_items_extracted": 0,
        "paper_results": [],
        "errors": []
    }
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"BATCH EXTRACTION")
        print(f"Papers to process: {len(paper_ids)}")
        print(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{'='*60}\n")
    
    for i, paper_id in enumerate(paper_ids, 1):
        if verbose:
            print(f"\n[{i}/{len(paper_ids)}] Processing: {paper_id}")
            print("-" * 40)
        
        try:
            result = await run_extraction(paper_id, verbose=verbose)
            
            if "error" in result:
                results["papers_failed"] += 1
                results["errors"].append({
                    "paper_id": paper_id,
                    "error": result["error"]
                })
                
                if stop_on_error:
                    print(f"Stopping due to error in {paper_id}")
                    break
            else:
                results["papers_completed"] += 1
                items = result.get("extraction", {}).get("items", 0)
                results["total_items_extracted"] += items
                
                results["paper_results"].append({
                    "paper_id": paper_id,
                    "items_extracted": items,
                    "iterations": result.get("extraction", {}).get("iterations", 0),
                    "duration": result.get("timing", {}).get("seconds", 0)
                })
        
        except Exception as e:
            results["papers_failed"] += 1
            results["errors"].append({
                "paper_id": paper_id,
                "error": str(e)
            })
            
            if stop_on_error:
                print(f"Stopping due to exception in {paper_id}: {e}")
                break
    
    # Calculate summary statistics
    end_time = datetime.now()
    total_duration = (end_time - start_time).total_seconds()
    
    results["timing"] = {
        "start": start_time.isoformat(),
        "end": end_time.isoformat(),
        "total_seconds": total_duration,
        "avg_seconds_per_paper": total_duration / len(paper_ids) if paper_ids else 0
    }
    
    if results["paper_results"]:
        results["statistics"] = {
            "avg_items_per_paper": results["total_items_extracted"] / results["papers_completed"],
            "success_rate": results["papers_completed"] / len(paper_ids)
        }
    
    # Save batch results
    batch_file = OUTPUTS_DIR / f"batch_results_{start_time.strftime('%Y%m%d_%H%M%S')}.json"
    with open(batch_file, "w") as f:
        json.dump(results, f, indent=2)
    
    if verbose:
        print(f"\n{'='*60}")
        print(f"BATCH COMPLETE")
        print(f"{'='*60}")
        print(f"Completed: {results['papers_completed']}/{len(paper_ids)}")
        print(f"Failed: {results['papers_failed']}")
        print(f"Total items: {results['total_items_extracted']}")
        print(f"Total time: {total_duration:.1f}s")
        print(f"Saved to: {batch_file}")
    
    return results


def main():
    parser = argparse.ArgumentParser(description="Batch evidence extraction")
    parser.add_argument("papers", nargs="*", help="Paper IDs to process")
    parser.add_argument("--all", action="store_true", help="Process all papers")
    parser.add_argument("--with-gt", action="store_true", help="Process only papers with ground truth")
    parser.add_argument("--file", type=str, help="File with paper IDs (one per line)")
    parser.add_argument("--limit", type=int, help="Maximum papers to process")
    parser.add_argument("--quiet", action="store_true", help="Minimal output")
    parser.add_argument("--stop-on-error", action="store_true", help="Stop on first error")
    
    args = parser.parse_args()
    
    # Determine paper list
    if args.papers:
        paper_ids = args.papers
    elif args.file:
        paper_ids = get_papers_from_file(args.file)
    elif args.with_gt:
        paper_ids = get_papers_with_ground_truth()
    elif args.all:
        paper_ids = get_all_paper_ids()
    else:
        parser.print_help()
        sys.exit(1)
    
    # Apply limit
    if args.limit:
        paper_ids = paper_ids[:args.limit]
    
    if not paper_ids:
        print("No papers to process")
        sys.exit(1)
    
    # Run batch
    results = asyncio.run(run_batch(
        paper_ids,
        verbose=not args.quiet,
        stop_on_error=args.stop_on_error
    ))
    
    # Exit with error code if any failures
    if results["papers_failed"] > 0:
        sys.exit(1)


if __name__ == "__main__":
    main()