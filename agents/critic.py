"""
Critic Agent - Text-Based
=========================

Validates extracted evidence items against paper content (pre-extracted by Reader).

KEY CHANGE: This agent receives TEXT content, not images.
The Reader has already extracted everything - Critic validates against text.
"""

CRITIC_SYSTEM_PROMPT = """You are a Critic agent for CIViC evidence extraction validation.

## YOUR ROLE
Validate extracted evidence items against the paper content (provided as TEXT).

## INPUT
You receive:
1. Pre-extracted paper content (title, abstract, sections, tables, figures, statistics)
2. Extraction plan from the Planner
3. Evidence items to validate

## VALIDATION CHECKLIST

For EACH evidence item, verify:

### 1. Required Fields (ALL 8 must be present and valid)
- feature_names: Valid gene name
- variant_names: Specific variant (not just gene name)
- disease_name: Specific disease (not generic "cancer")
- evidence_type: PREDICTIVE/PROGNOSTIC/DIAGNOSTIC/PREDISPOSING
- evidence_level: A/B/C/D/E
- evidence_direction: SUPPORTS/DOES_NOT_SUPPORT
- evidence_significance: Matches evidence_type rules
- evidence_description: Contains statistics, not just narrative

### 2. Type-Specific Rules
- PREDICTIVE: MUST have therapy_names field
- PROGNOSTIC: Should NOT have therapy_names (outcome independent of treatment)
- PREDISPOSING: variant_origin should be GERMLINE

### 3. Significance Matching
- PREDICTIVE → SENSITIVITY, RESISTANCE, REDUCED_SENSITIVITY, ADVERSE_RESPONSE
- PROGNOSTIC → BETTER_OUTCOME, POOR_OUTCOME
- DIAGNOSTIC → POSITIVE, NEGATIVE
- PREDISPOSING → PREDISPOSITION, PROTECTIVENESS

### 4. Statistics Verification
- Compare verbatim_statistics to KEY STATISTICS in paper content
- Verify numbers match exactly
- Check confidence intervals are included
- Verify sample sizes if mentioned

### 5. Verbatim Quote Verification
- The verbatim_quote should appear in the paper content
- If it doesn't match, flag as an issue

### 6. Reasoning Quality
- Is extraction_reasoning coherent?
- Does evidence_type match the claim?
- Is confidence score appropriate?

## MISSING ITEM CHECK

Review the paper content for evidence NOT captured:
- Check KEY STATISTICS section
- Check TABLES section
- Check FIGURES section
- Any statistics with gene+variant+outcome not extracted?

## EXTRA ITEM CHECK

Look for items that shouldn't be there:
- Duplicate/redundant items
- Items without solid statistics
- Hallucinated data not in paper content

## OUTPUT FORMAT

Call save_critique with:
- overall_assessment: "APPROVE", "NEEDS_REVISION", or "REJECT"
- item_feedback: JSON with per-item validation
- missing_items: What should have been extracted
- extra_items: What should be removed
- summary: Overall assessment summary

## ASSESSMENT GUIDELINES

### APPROVE
- All items valid
- No critical missing items
- Statistics verified against content

### NEEDS_REVISION
- Some items need fixes (missing stats, wrong type)
- Some items should be removed
- Some items are missing from content

### REJECT (rare - only for fundamental issues)
- Completely wrong paper (extraction doesn't match content)
- Massive hallucination
- Zero valid items

## CRITICAL RULES
1. Work ONLY from the provided text content
2. Verify every statistic against the content
3. Be specific in feedback - say exactly what needs fixing
4. Quality matters more than quantity
"""


def get_critic_tools() -> list[dict]:
    """
    Tools available to the Critic agent.
    Note: No read_paper_page tool! Critic works from text content only.
    """
    return [
        {
            "name": "validate_evidence_item",
            "description": "Validate a single evidence item.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "item_index": {
                        "type": "integer",
                        "description": "Index of the item being validated"
                    },
                    "item": {
                        "type": "object",
                        "description": "The evidence item to validate"
                    }
                },
                "required": ["item_index", "item"]
            }
        },
        {
            "name": "check_actionability",
            "description": "Check if a potential evidence claim is actionable.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "claim": {
                        "type": "string",
                        "description": "The evidence claim to check"
                    }
                },
                "required": ["claim"]
            }
        },
        {
            "name": "save_critique",
            "description": "Save the critique results.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "overall_assessment": {
                        "type": "string",
                        "enum": ["APPROVE", "NEEDS_REVISION", "REJECT"],
                        "description": "Overall assessment of the extraction"
                    },
                    "item_feedback": {
                        "type": "string",
                        "description": "JSON string with per-item feedback"
                    },
                    "missing_items": {
                        "type": "string",
                        "description": "Evidence items that should have been extracted"
                    },
                    "extra_items": {
                        "type": "string",
                        "description": "Evidence items that should be removed"
                    },
                    "summary": {
                        "type": "string",
                        "description": "Overall summary of the critique"
                    }
                },
                "required": [
                    "overall_assessment",
                    "item_feedback",
                    "missing_items",
                    "extra_items",
                    "summary"
                ]
            }
        }
    ]