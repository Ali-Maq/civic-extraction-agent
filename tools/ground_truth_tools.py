"""
Ground Truth Tools
==================

Tools for accessing ground truth data.

IMPORTANT: These tools are BLOCKED during extraction to prevent "cheating".
They should only be used during evaluation (post-extraction).
"""

import json
from claude_agent_sdk import tool
from typing import Any

from context import require_context


@tool(
    "lookup_ground_truth",
    "Look up ground truth evidence items for the current paper. EVALUATION ONLY - blocked during extraction.",
    {}
)
async def lookup_ground_truth(args: dict[str, Any]) -> dict[str, Any]:
    """
    Get ground truth for current paper.
    
    NOTE: This tool is blocked during extraction via hooks.
    It only works during evaluation mode.
    """
    ctx = require_context()
    
    if ctx.paper is None:
        return {
            "content": [{"type": "text", "text": "No paper loaded"}],
            "is_error": True
        }
    
    items = ctx.get_ground_truth_for_paper()
    
    if not items:
        result = {
            "paper_id": ctx.paper.paper_id,
            "has_ground_truth": False,
            "item_count": 0,
            "note": "No ground truth found for this paper"
        }
    else:
        # Extract key summary info
        evidence_types = list(set(item.get("evidence_type", "") for item in items))
        variants = list(set(item.get("variant_names", "") for item in items if item.get("variant_names")))
        diseases = list(set(item.get("disease_name", "") for item in items if item.get("disease_name")))
        therapies = list(set(item.get("therapy_names", "") for item in items if item.get("therapy_names")))
        
        result = {
            "paper_id": ctx.paper.paper_id,
            "has_ground_truth": True,
            "item_count": len(items),
            "evidence_types": evidence_types,
            "variants": variants[:10],  # Limit for readability
            "diseases": diseases[:5],
            "therapies": therapies[:10],
            "items": items
        }
    
    return {
        "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
    }


@tool(
    "compare_to_ground_truth",
    "Compare draft extractions against ground truth. EVALUATION ONLY - blocked during extraction.",
    {}
)
async def compare_to_ground_truth(args: dict[str, Any]) -> dict[str, Any]:
    """
    Compare current extractions to ground truth.
    
    NOTE: This tool is blocked during extraction via hooks.
    """
    ctx = require_context()
    
    draft = ctx.state.draft_extractions or ctx.state.final_extractions
    gt_items = ctx.get_ground_truth_for_paper()
    
    if not gt_items:
        return {
            "content": [{
                "type": "text",
                "text": json.dumps({
                    "error": "No ground truth available",
                    "draft_count": len(draft),
                    "can_compare": False
                }, indent=2)
            }]
        }
    
    draft_count = len(draft)
    gt_count = len(gt_items)
    
    feedback = []
    
    # Count comparison
    if draft_count < gt_count:
        feedback.append(f"UNDER-EXTRACTION: Got {draft_count}, expected {gt_count}. Missing {gt_count - draft_count} items.")
    elif draft_count > gt_count:
        feedback.append(f"OVER-EXTRACTION: Got {draft_count}, expected {gt_count}. {draft_count - gt_count} extra items.")
    else:
        feedback.append(f"COUNT MATCH: Both have {draft_count} items.")
    
    # Evidence type comparison
    draft_types = set(item.get("evidence_type", "").upper() for item in draft)
    gt_types = set(item.get("evidence_type", "").upper() for item in gt_items)
    
    missing_types = gt_types - draft_types
    extra_types = draft_types - gt_types
    
    if missing_types:
        feedback.append(f"MISSING TYPES: Ground truth has {missing_types} not in extraction.")
    if extra_types:
        feedback.append(f"EXTRA TYPES: Extraction has {extra_types} not in ground truth.")
    
    # Variant comparison
    draft_variants = set(item.get("variant_names", "") for item in draft if item.get("variant_names"))
    gt_variants = set(item.get("variant_names", "") for item in gt_items if item.get("variant_names"))
    
    missing_variants = gt_variants - draft_variants
    extra_variants = draft_variants - gt_variants
    
    if missing_variants:
        feedback.append(f"MISSING VARIANTS: {missing_variants}")
    if extra_variants:
        feedback.append(f"EXTRA VARIANTS: {extra_variants}")
    
    # Therapy comparison
    draft_therapies = set(item.get("therapy_names", "") for item in draft if item.get("therapy_names"))
    gt_therapies = set(item.get("therapy_names", "") for item in gt_items if item.get("therapy_names"))
    
    missing_therapies = gt_therapies - draft_therapies
    if missing_therapies:
        feedback.append(f"MISSING THERAPIES: {missing_therapies}")
    
    # Calculate match score
    count_accuracy = min(draft_count, gt_count) / max(draft_count, gt_count) if max(draft_count, gt_count) > 0 else 0
    type_overlap = len(draft_types & gt_types) / len(gt_types) if gt_types else 0
    variant_overlap = len(draft_variants & gt_variants) / len(gt_variants) if gt_variants else 0
    
    match_score = (count_accuracy + type_overlap + variant_overlap) / 3
    
    result = {
        "draft_count": draft_count,
        "ground_truth_count": gt_count,
        "match_score": round(match_score, 2),
        "is_perfect_match": len(feedback) == 1 and "COUNT MATCH" in feedback[0],
        "evidence_types": {
            "draft": list(draft_types),
            "ground_truth": list(gt_types),
            "missing": list(missing_types),
            "extra": list(extra_types)
        },
        "variants": {
            "draft": list(draft_variants),
            "ground_truth": list(gt_variants),
            "missing": list(missing_variants),
            "extra": list(extra_variants)
        },
        "feedback": feedback
    }
    
    return {
        "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
    }


@tool(
    "find_similar_papers",
    "Find similar papers in ground truth to learn extraction patterns. EVALUATION ONLY.",
    {"variant": str, "disease": str, "evidence_type": str}
)
async def find_similar_papers(args: dict[str, Any]) -> dict[str, Any]:
    """Find similar papers for pattern learning."""
    ctx = require_context()
    
    if ctx.ground_truth_df is None:
        ctx.load_ground_truth()
    
    df = ctx.ground_truth_df.copy()
    
    # Apply filters
    variant = args.get("variant")
    disease = args.get("disease")
    evidence_type = args.get("evidence_type")
    
    if variant:
        df = df[df["variant_names"].str.contains(variant, case=False, na=False)]
    if disease:
        df = df[df["disease_name"].str.contains(disease, case=False, na=False)]
    if evidence_type:
        df = df[df["evidence_type"].str.contains(evidence_type, case=False, na=False)]
    
    if len(df) == 0:
        return {
            "content": [{
                "type": "text",
                "text": json.dumps({
                    "query": {"variant": variant, "disease": disease, "evidence_type": evidence_type},
                    "similar_papers": [],
                    "note": "No similar papers found"
                }, indent=2)
            }]
        }
    
    # Group by paper
    paper_stats = df.groupby("paper_folder").agg({
        "evidence_type": lambda x: list(x.unique()),
        "variant_names": lambda x: list(set(str(v) for v in x if v)),
        "disease_name": lambda x: list(set(str(d) for d in x if d)),
    }).reset_index()
    
    # Add counts
    counts = df.groupby("paper_folder").size().reset_index(name="item_count")
    paper_stats = paper_stats.merge(counts, on="paper_folder")
    paper_stats = paper_stats.sort_values("item_count", ascending=False)
    
    # Get top 5
    similar = []
    for _, row in paper_stats.head(5).iterrows():
        similar.append({
            "paper_id": row["paper_folder"],
            "item_count": int(row["item_count"]),
            "evidence_types": row["evidence_type"],
            "variants": row["variant_names"][:5],
            "diseases": row["disease_name"][:3]
        })
    
    result = {
        "query": {"variant": variant, "disease": disease, "evidence_type": evidence_type},
        "similar_papers": similar,
        "patterns": {
            "average_items": round(df.groupby("paper_folder").size().mean(), 1),
            "total_matching_items": len(df),
            "total_matching_papers": len(paper_stats)
        }
    }
    
    return {
        "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
    }


def get_extraction_statistics_sync(ctx) -> dict:
    """
    Get overall ground truth statistics.
    
    Synchronous helper function (not an MCP tool).
    """
    if ctx.ground_truth_df is None:
        ctx.load_ground_truth()
    
    df = ctx.ground_truth_df
    
    return {
        "total_evidence_items": len(df),
        "total_papers": df["paper_folder"].nunique(),
        "average_items_per_paper": round(len(df) / df["paper_folder"].nunique(), 2),
        "evidence_type_distribution": df["evidence_type"].value_counts().to_dict(),
        "evidence_level_distribution": df["evidence_level"].value_counts().to_dict(),
        "top_diseases": df["disease_name"].value_counts().head(10).to_dict(),
    }