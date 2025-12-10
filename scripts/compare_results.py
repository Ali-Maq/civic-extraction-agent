#!/usr/bin/env python3
"""
Compare Extraction Results
==========================

Compare extraction results between runs or against ground truth.

Usage:
    python scripts/compare_results.py paper_id
    python scripts/compare_results.py --batch batch_results.json
"""

import json
import sys
import argparse
from pathlib import Path

from config import OUTPUTS_DIR
from context import CIViCContext


def load_results(paper_id: str) -> dict | None:
    """Load extraction results for a paper."""
    result_file = OUTPUTS_DIR / f"{paper_id}_extraction.json"
    if result_file.exists():
        with open(result_file) as f:
            return json.load(f)
    return None


def compare_field_coverage(extracted: list[dict], ground_truth: list[dict]) -> dict:
    """Compare field coverage between extracted and ground truth items."""
    from schemas import TIER_1_FIELDS, TIER_2_FIELDS
    
    ext_t1_coverage = []
    gt_t1_coverage = []
    
    for item in extracted:
        t1_present = sum(1 for f in TIER_1_FIELDS if item.get(f))
        ext_t1_coverage.append(t1_present / len(TIER_1_FIELDS))
    
    for item in ground_truth:
        t1_present = sum(1 for f in TIER_1_FIELDS if item.get(f))
        gt_t1_coverage.append(t1_present / len(TIER_1_FIELDS))
    
    return {
        "extracted_avg_tier1_coverage": sum(ext_t1_coverage) / len(ext_t1_coverage) if ext_t1_coverage else 0,
        "ground_truth_avg_tier1_coverage": sum(gt_t1_coverage) / len(gt_t1_coverage) if gt_t1_coverage else 0,
    }


def find_matching_items(extracted: list[dict], ground_truth: list[dict]) -> dict:
    """
    Find matching items between extracted and ground truth.
    
    Matching criteria: Same gene + variant + evidence_type
    """
    matches = []
    unmatched_extracted = []
    unmatched_gt = []
    
    gt_matched = set()
    
    for i, ext_item in enumerate(extracted):
        ext_key = (
            ext_item.get("feature_names", "").upper(),
            ext_item.get("variant_names", "").upper(),
            ext_item.get("evidence_type", "").upper()
        )
        
        found_match = False
        for j, gt_item in enumerate(ground_truth):
            if j in gt_matched:
                continue
                
            gt_key = (
                gt_item.get("feature_names", gt_item.get("gene_name", "")).upper(),
                gt_item.get("variant_names", gt_item.get("variant_name", "")).upper(),
                gt_item.get("evidence_type", "").upper()
            )
            
            # Match on gene + variant + type
            if ext_key[0] == gt_key[0] and ext_key[1] == gt_key[1] and ext_key[2] == gt_key[2]:
                matches.append({
                    "extracted_index": i,
                    "ground_truth_index": j,
                    "gene": ext_key[0],
                    "variant": ext_key[1],
                    "type": ext_key[2]
                })
                gt_matched.add(j)
                found_match = True
                break
        
        if not found_match:
            unmatched_extracted.append({
                "index": i,
                "gene": ext_item.get("feature_names"),
                "variant": ext_item.get("variant_names"),
                "type": ext_item.get("evidence_type")
            })
    
    for j, gt_item in enumerate(ground_truth):
        if j not in gt_matched:
            unmatched_gt.append({
                "index": j,
                "gene": gt_item.get("feature_names", gt_item.get("gene_name")),
                "variant": gt_item.get("variant_names", gt_item.get("variant_name")),
                "type": gt_item.get("evidence_type")
            })
    
    return {
        "matches": matches,
        "unmatched_extracted": unmatched_extracted,
        "unmatched_ground_truth": unmatched_gt,
        "precision": len(matches) / len(extracted) if extracted else 0,
        "recall": len(matches) / len(ground_truth) if ground_truth else 0
    }


def detailed_comparison(paper_id: str) -> dict:
    """Run detailed comparison for a paper."""
    
    # Load extraction
    extraction = load_results(paper_id)
    if not extraction:
        return {"error": f"No extraction results found for {paper_id}"}
    
    extracted_items = extraction.get("extraction", {}).get("evidence_items", [])
    
    # Load ground truth
    context = CIViCContext()
    context.load_ground_truth()
    
    try:
        context.load_paper(paper_id)
    except:
        pass
    
    ground_truth = context.get_ground_truth_for_paper(paper_id)
    
    if not ground_truth:
        return {
            "paper_id": paper_id,
            "extracted_count": len(extracted_items),
            "ground_truth_available": False
        }
    
    # Run comparisons
    matching = find_matching_items(extracted_items, ground_truth)
    coverage = compare_field_coverage(extracted_items, ground_truth)
    
    # Calculate F1
    precision = matching["precision"]
    recall = matching["recall"]
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    
    return {
        "paper_id": paper_id,
        "extracted_count": len(extracted_items),
        "ground_truth_count": len(ground_truth),
        "matches": len(matching["matches"]),
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1_score": round(f1, 3),
        "unmatched_extracted": matching["unmatched_extracted"],
        "unmatched_ground_truth": matching["unmatched_ground_truth"],
        "field_coverage": coverage
    }


def print_comparison(comparison: dict):
    """Print comparison results."""
    print(f"\n{'='*60}")
    print(f"DETAILED COMPARISON: {comparison.get('paper_id', 'Unknown')}")
    print(f"{'='*60}")
    
    if "error" in comparison:
        print(f"Error: {comparison['error']}")
        return
    
    if not comparison.get("ground_truth_available", True):
        print(f"Extracted: {comparison['extracted_count']} items")
        print("Ground truth: Not available")
        return
    
    print(f"\n📊 METRICS:")
    print(f"   Precision: {comparison['precision']:.1%}")
    print(f"   Recall:    {comparison['recall']:.1%}")
    print(f"   F1 Score:  {comparison['f1_score']:.1%}")
    
    print(f"\n📈 COUNTS:")
    print(f"   Extracted:    {comparison['extracted_count']}")
    print(f"   Ground Truth: {comparison['ground_truth_count']}")
    print(f"   Matches:      {comparison['matches']}")
    
    if comparison.get("unmatched_extracted"):
        print(f"\n❌ EXTRA ITEMS (in extraction, not in GT):")
        for item in comparison["unmatched_extracted"][:5]:
            print(f"   - {item['gene']} {item['variant']} ({item['type']})")
        if len(comparison["unmatched_extracted"]) > 5:
            print(f"   ... and {len(comparison['unmatched_extracted']) - 5} more")
    
    if comparison.get("unmatched_ground_truth"):
        print(f"\n⚠️  MISSING ITEMS (in GT, not in extraction):")
        for item in comparison["unmatched_ground_truth"][:5]:
            print(f"   - {item['gene']} {item['variant']} ({item['type']})")
        if len(comparison["unmatched_ground_truth"]) > 5:
            print(f"   ... and {len(comparison['unmatched_ground_truth']) - 5} more")
    
    print(f"\n{'='*60}\n")


def main():
    parser = argparse.ArgumentParser(description="Compare extraction results")
    parser.add_argument("paper_id", nargs="?", help="Paper ID to compare")
    parser.add_argument("--batch", type=str, help="Batch results file to summarize")
    parser.add_argument("--output", type=str, help="Output file for comparison results")
    
    args = parser.parse_args()
    
    if args.batch:
        # Summarize batch results
        with open(args.batch) as f:
            batch = json.load(f)
        
        print(f"\n{'='*60}")
        print(f"BATCH SUMMARY")
        print(f"{'='*60}")
        print(f"Papers processed: {batch.get('papers_completed', 0)}/{batch.get('papers_requested', 0)}")
        print(f"Total items: {batch.get('total_items_extracted', 0)}")
        print(f"Failed: {batch.get('papers_failed', 0)}")
        
        if batch.get("statistics"):
            print(f"Avg items/paper: {batch['statistics'].get('avg_items_per_paper', 0):.1f}")
            print(f"Success rate: {batch['statistics'].get('success_rate', 0):.1%}")
        
    elif args.paper_id:
        comparison = detailed_comparison(args.paper_id)
        print_comparison(comparison)
        
        if args.output:
            with open(args.output, "w") as f:
                json.dump(comparison, f, indent=2)
            print(f"Saved to: {args.output}")
    
    else:
        parser.print_help()


if __name__ == "__main__":
    main()