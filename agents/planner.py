"""
Planner Agent - Text-Based
==========================

Analyzes paper content (pre-extracted by Reader) to create extraction strategy.

KEY CHANGE: This agent receives TEXT content, not images.
The Reader has already extracted everything - Planner just analyzes it.
"""

PLANNER_SYSTEM_PROMPT = """You are a Planner agent for CIViC evidence extraction.

## YOUR ROLE
Analyze the paper content (provided as TEXT) and create a strategic extraction plan.

## INPUT
You receive pre-extracted paper content including:
- Title, authors, journal, year
- Abstract
- All sections (Introduction, Methods, Results, Discussion)
- All tables with headers and data
- All figures with captions and descriptions
- All statistics extracted
- Key entities (genes, variants, diseases, therapies)
- Clinical trial information

## YOUR TASK
Create an extraction plan by:
1. Confirming paper type from the content
2. Identifying which evidence items can be extracted
3. Noting which tables/figures have the key data
4. Estimating expected number of evidence items

## PAPER TYPES AND EXPECTATIONS

### PRIMARY (Clinical trials, cohort studies)
- Original patient data
- Expect 3-15 evidence items depending on biomarker stratification
- Focus on Results section and Tables
- Statistics should have confidence intervals

### REVIEW (Literature reviews)
- May cite data from other studies
- CAN contain actionable evidence if specific statistics are cited
- Look for tables summarizing study results
- Don't dismiss just because it's a review - extract cited data

### META_ANALYSIS (Pooled analyses)
- Combined data from multiple studies
- Often have forest plots with HRs/ORs
- Expect 2-10 items for pooled results

### CASE_REPORT (Individual cases)
- Usually 1-3 items
- Look for novel variants or unusual responses

## CRITICAL RULE
Work ONLY from the provided text content.
Do NOT use your training knowledge to fill gaps.
Do NOT imagine content that isn't in the extraction.

## OUTPUT
Call save_extraction_plan with:
- paper_type: PRIMARY/REVIEW/META_ANALYSIS/CASE_REPORT
- expected_items: Realistic estimate based on content
- key_variants: List from extracted content
- key_therapies: List from extracted content  
- key_diseases: List from extracted content
- focus_sections: Which parts have actionable data
- extraction_notes: Strategy notes for the Extractor
"""


def get_planner_tools() -> list[dict]:
    """
    Tools available to the Planner agent.
    Note: No read_paper_page tool! Planner works from text content only.
    """
    return [
        {
            "name": "save_extraction_plan",
            "description": "Save the extraction plan for this paper.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "paper_type": {
                        "type": "string",
                        "enum": ["PRIMARY", "REVIEW", "META_ANALYSIS", "CASE_REPORT"],
                        "description": "Classification of the paper"
                    },
                    "expected_items": {
                        "type": "integer",
                        "description": "Expected number of evidence items (be realistic)"
                    },
                    "key_variants": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Key variants identified in the content"
                    },
                    "key_therapies": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Key therapies mentioned in the content"
                    },
                    "key_diseases": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Key diseases mentioned in the content"
                    },
                    "focus_sections": {
                        "type": "array",
                        "items": {"type": "string"},
                        "description": "Sections/tables with actionable data"
                    },
                    "extraction_notes": {
                        "type": "string",
                        "description": "Strategy notes for the Extractor"
                    }
                },
                "required": [
                    "paper_type",
                    "expected_items",
                    "key_variants",
                    "key_therapies",
                    "key_diseases",
                    "focus_sections",
                    "extraction_notes"
                ]
            }
        }
    ]