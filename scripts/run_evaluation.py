#!/usr/bin/env python3
"""
CIViC Extraction Evaluation
===========================

Compare extraction results against ground truth.
Run this AFTER extraction to evaluate quality.

Usage:
    python scripts/run_evaluation.py <paper_id>
    python scripts/run_evaluation.py <paper_id> --detailed
"""

import json
import sys
from pathlib import Path
from datetime import datetime

from config import OUTPUTS_DIR
from context import CIViCContext


def load_extraction_results(paper_id: str) -> dict | None:
    """Load extraction results from output file."""
    output_file = OUTPUTS_DIR / f"{paper_id}_extraction.json"
    
    if not output_file.exists():
        print(f"Error: No extraction results found at {output_file}")
        print(f"Run extraction first: python scripts/run_extraction.py {paper_id}")
        return None
    
    with open(output_file) as f:
        return json.load(f)


def compare_to_ground_truth(extraction: dict, ground_truth: list) -> dict:
    """
    Compare extraction results to ground truth.
    
    Returns detailed comparison metrics.
    """
    extracted_items = extraction.get("extraction", {}).get("evidence_items", [])
    
    ext_count = len(extracted_items)
    gt_count = len(ground_truth)
    
    # Basic counts
    metrics = {
        "extracted_count": ext_count,
        "ground_truth_count": gt_count,
        "count_difference": ext_count - gt_count,
        "count_accuracy": min(ext_count, gt_count) / max(ext_count, gt_count) if max(ext_count, gt_count) > 0 else 0
    }
    
    # Evidence type comparison
    ext_types = set(item.get("evidence_type", "").upper() for item in extracted_items)
    gt_types = set(item.get("evidence_type", "").upper() for item in ground_truth)
    
    metrics["evidence_types"] = {
        "extracted": list(ext_types),
        "ground_truth": list(gt_types),
        "missing": list(gt_types - ext_types),
        "extra": list(ext_types - gt_types),
        "overlap": len(ext_types & gt_types) / len(gt_types) if gt_types else 0
    }
    
    # Variant comparison
    ext_variants = set(item.get("variant_names", "") for item in extracted_items if item.get("variant_names"))
    gt_variants = set(item.get("variant_names", "") for item in ground_truth if item.get("variant_names"))
    
    metrics["variants"] = {
        "extracted": list(ext_variants),
        "ground_truth": list(gt_variants),
        "missing": list(gt_variants - ext_variants),
        "extra": list(ext_variants - gt_variants),
        "overlap": len(ext_variants & gt_variants) / len(gt_variants) if gt_variants else 0
    }
    
    # Therapy comparison
    ext_therapies = set(item.get("therapy_names", "") for item in extracted_items if item.get("therapy_names"))
    gt_therapies = set(item.get("therapy_names", "") for item in ground_truth if item.get("therapy_names"))
    
    metrics["therapies"] = {
        "extracted": list(ext_therapies),
        "ground_truth": list(gt_therapies),
        "missing": list(gt_therapies - ext_therapies),
        "extra": list(ext_therapies - gt_therapies),
        "overlap": len(ext_therapies & gt_therapies) / len(gt_therapies) if gt_therapies else 0
    }
    
    # Disease comparison
    ext_diseases = set(item.get("disease_name", "").lower() for item in extracted_items if item.get("disease_name"))
    gt_diseases = set(item.get("disease_name", "").lower() for item in ground_truth if item.get("disease_name"))
    
    metrics["diseases"] = {
        "extracted": list(ext_diseases),
        "ground_truth": list(gt_diseases),
        "overlap": len(ext_diseases & gt_diseases) / len(gt_diseases) if gt_diseases else 0
    }
    
    # Calculate overall score
    count_score = metrics["count_accuracy"]
    type_score = metrics["evidence_types"]["overlap"]
    variant_score = metrics["variants"]["overlap"]
    therapy_score = metrics["therapies"]["overlap"] if gt_therapies else 1.0  # Don't penalize if no therapies in GT
    
    metrics["overall_score"] = round((count_score + type_score + variant_score + therapy_score) / 4, 3)
    
    # Determine grade
    score = metrics["overall_score"]
    if score >= 0.9:
        metrics["grade"] = "A"
    elif score >= 0.8:
        metrics["grade"] = "B"
    elif score >= 0.7:
        metrics["grade"] = "C"
    elif score >= 0.6:
        metrics["grade"] = "D"
    else:
        metrics["grade"] = "F"
    
    return metrics


def print_evaluation(paper_id: str, metrics: dict, detailed: bool = False):
    """Print evaluation results."""
    print(f"\n{'='*60}")
    print(f"EVALUATION REPORT: {paper_id}")
    print(f"{'='*60}")
    
    print(f"\n📊 OVERALL SCORE: {metrics['overall_score']:.1%} (Grade: {metrics['grade']})")
    
    print(f"\n📈 COUNTS:")
    print(f"   Extracted:    {metrics['extracted_count']}")
    print(f"   Ground Truth: {metrics['ground_truth_count']}")
    print(f"   Difference:   {metrics['count_difference']:+d}")
    
    print(f"\n🔬 EVIDENCE TYPES:")
    print(f"   Overlap: {metrics['evidence_types']['overlap']:.1%}")
    if metrics['evidence_types']['missing']:
        print(f"   Missing: {metrics['evidence_types']['missing']}")
    if metrics['evidence_types']['extra']:
        print(f"   Extra:   {metrics['evidence_types']['extra']}")
    
    print(f"\n🧬 VARIANTS:")
    print(f"   Overlap: {metrics['variants']['overlap']:.1%}")
    if metrics['variants']['missing']:
        print(f"   Missing: {metrics['variants']['missing']}")
    if metrics['variants']['extra']:
        print(f"   Extra:   {metrics['variants']['extra']}")
    
    print(f"\n💊 THERAPIES:")
    print(f"   Overlap: {metrics['therapies']['overlap']:.1%}")
    if metrics['therapies']['missing']:
        print(f"   Missing: {metrics['therapies']['missing']}")
    if metrics['therapies']['extra']:
        print(f"   Extra:   {metrics['therapies']['extra']}")
    
    if detailed:
        print(f"\n📋 DETAILED DATA:")
        print(f"\n   Extracted variants: {metrics['variants']['extracted']}")
        print(f"   Ground truth variants: {metrics['variants']['ground_truth']}")
        print(f"\n   Extracted therapies: {metrics['therapies']['extracted']}")
        print(f"   Ground truth therapies: {metrics['therapies']['ground_truth']}")
    
    print(f"\n{'='*60}\n")


def run_evaluation(paper_id: str, detailed: bool = False) -> dict:
    """Run full evaluation for a paper."""
    
    # Load extraction results
    extraction = load_extraction_results(paper_id)
    if extraction is None:
        return {"error": "No extraction results found"}
    
    # Load ground truth
    context = CIViCContext()
    context.load_ground_truth()
    context.load_paper(paper_id)
    
    ground_truth = context.get_ground_truth_for_paper()
    
    if not ground_truth:
        print(f"Warning: No ground truth available for {paper_id}")
        return {
            "paper_id": paper_id,
            "extracted_count": len(extraction.get("extraction", {}).get("evidence_items", [])),
            "ground_truth_count": 0,
            "note": "No ground truth available for comparison"
        }
    
    # Compare
    metrics = compare_to_ground_truth(extraction, ground_truth)
    metrics["paper_id"] = paper_id
    metrics["evaluated_at"] = datetime.now().isoformat()
    
    # Print results
    print_evaluation(paper_id, metrics, detailed)
    
    # Save evaluation results
    eval_file = OUTPUTS_DIR / f"{paper_id}_evaluation.json"
    with open(eval_file, "w") as f:
        json.dump(metrics, f, indent=2)
    print(f"Evaluation saved to: {eval_file}")
    
    return metrics


def main():
    if len(sys.argv) < 2:
        print("Usage: python scripts/run_evaluation.py <paper_id> [--detailed]")
        print("Example: python scripts/run_evaluation.py 00167_Denis_2015")
        sys.exit(1)
    
    paper_id = sys.argv[1]
    detailed = "--detailed" in sys.argv
    
    results = run_evaluation(paper_id, detailed)
    
    if "error" in results:
        print(f"Error: {results['error']}")
        sys.exit(1)


if __name__ == "__main__":
    main()