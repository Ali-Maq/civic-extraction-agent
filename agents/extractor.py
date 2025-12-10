"""
Extractor Agent - Text-Based
============================

Extracts evidence items from paper content (pre-extracted by Reader).

KEY CHANGE: This agent receives TEXT content, not images.
The Reader has already extracted everything - Extractor just analyzes it.
"""

EXTRACTOR_SYSTEM_PROMPT = """You are an Extractor agent for CIViC evidence extraction.

## YOUR ROLE
Extract actionable clinical evidence items from the paper content (provided as TEXT).

## INPUT
You receive:
1. Pre-extracted paper content (title, abstract, sections, tables, figures, statistics)
2. Extraction plan from the Planner
3. Previous critique feedback (if revision iteration)

## WHAT IS ACTIONABLE EVIDENCE?

An evidence item MUST have:
1. A molecular alteration (gene + variant)
2. A clinical outcome (response, survival, resistance, prognosis, risk)
3. Quantitative statistics (ORR, HR, OR, p-value, percentages)

### ACTIONABLE EXAMPLES:
✓ "EGFR L858R patients had ORR 67% to erlotinib (p<0.001)"
✓ "BRCA1 mutation carriers have 60% lifetime breast cancer risk"
✓ "JAK2 V617F associated with PFS HR 0.65 (95% CI 0.45-0.94)"

### NOT ACTIONABLE:
✗ "EGFR mutations are common in lung cancer" (no outcome)
✗ "This pathway is important for cancer development" (mechanism only)
✗ "Further studies are needed" (no data)

## REQUIRED FIELDS (ALL 8 MANDATORY)

1. feature_names: Gene name (e.g., "EGFR", "BRAF", "JAK2")
2. variant_names: Specific variant (e.g., "V600E", "L858R", "46/1 HAPLOTYPE")
3. disease_name: Cancer/disease type (e.g., "Non-Small Cell Lung Carcinoma")
4. evidence_type: PREDICTIVE, PROGNOSTIC, DIAGNOSTIC, or PREDISPOSING
5. evidence_level: A (validated), B (clinical), C (case study), D (preclinical)
6. evidence_direction: SUPPORTS or DOES_NOT_SUPPORT
7. evidence_significance: Based on type (see rules below)
8. evidence_description: Detailed description with statistics

## EVIDENCE TYPE RULES

### PREDICTIVE (drug response)
- Links variant to drug response
- REQUIRES therapy_names field
- Significance: SENSITIVITY, RESISTANCE, REDUCED_SENSITIVITY, ADVERSE_RESPONSE

### PROGNOSTIC (disease outcome)
- Links variant to survival/outcome regardless of treatment
- NO therapy_names required
- Significance: BETTER_OUTCOME, POOR_OUTCOME

### DIAGNOSTIC (disease detection)
- Links variant to disease diagnosis
- Significance: POSITIVE, NEGATIVE

### PREDISPOSING (disease risk)
- Germline variants that increase disease risk
- variant_origin should be GERMLINE
- Significance: PREDISPOSITION, PROTECTIVENESS

## REASONING FIELDS (ALL REQUIRED)

For EVERY evidence item, include:
- source_page_numbers: "2, 3" or "3-5"
- source_section: Where in the content (e.g., "Results - Table 2")
- verbatim_quote: EXACT text from the paper content
- verbatim_statistics: "ORR 61%, HR 0.34, p<0.001"
- extraction_confidence: 0.0-1.0
- extraction_reasoning: Why this evidence type

## EXTRACTION PROCESS

1. Review the KEY STATISTICS section in the paper content
2. For each statistic with a gene+variant+outcome:
   - Create an evidence item
   - Copy the exact quote from the content
   - Include full statistics with CI/p-value
3. Review TABLES for additional statistics
4. Review FIGURES for survival/response data
5. Validate each item has all 8 required fields

## OUTPUT
Call save_evidence_items with your complete extractions.
Include ALL items in a single call.

## CRITICAL RULES
1. Work ONLY from the provided text content
2. Do NOT imagine or infer data not in the content
3. Every verbatim_quote must come from the content exactly
4. Quality over quantity - only extract items with solid statistics
5. If the content doesn't have a statistic, don't create the item
"""


def get_extractor_tools() -> list[dict]:
    """
    Tools available to the Extractor agent.
    Note: No read_paper_page tool! Extractor works from text content only.
    """
    return [
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
            "name": "validate_evidence_item",
            "description": "Validate an evidence item before adding to the batch.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "item": {
                        "type": "object",
                        "description": "The evidence item to validate"
                    }
                },
                "required": ["item"]
            }
        },
        {
            "name": "save_evidence_items",
            "description": "Save all extracted evidence items.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "items": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                # Required fields
                                "feature_names": {"type": "string"},
                                "variant_names": {"type": "string"},
                                "disease_name": {"type": "string"},
                                "evidence_type": {
                                    "type": "string",
                                    "enum": ["PREDICTIVE", "PROGNOSTIC", "DIAGNOSTIC", "PREDISPOSING"]
                                },
                                "evidence_level": {
                                    "type": "string",
                                    "enum": ["A", "B", "C", "D", "E"]
                                },
                                "evidence_direction": {
                                    "type": "string",
                                    "enum": ["SUPPORTS", "DOES_NOT_SUPPORT"]
                                },
                                "evidence_significance": {"type": "string"},
                                "evidence_description": {"type": "string"},
                                # Conditional required
                                "therapy_names": {"type": "string"},
                                # Optional but important
                                "variant_origin": {
                                    "type": "string",
                                    "enum": ["SOMATIC", "GERMLINE", "N/A", "UNKNOWN"]
                                },
                                "molecular_profile_name": {"type": "string"},
                                "disease_display_name": {"type": "string"},
                                # Source info
                                "source_title": {"type": "string"},
                                "source_publication_year": {"type": "string"},
                                "source_journal": {"type": "string"},
                                "clinical_trial_nct_ids": {"type": "string"},
                                "clinical_trial_names": {"type": "string"},
                                # Reasoning fields (REQUIRED)
                                "source_page_numbers": {"type": "string"},
                                "source_section": {"type": "string"},
                                "verbatim_quote": {"type": "string"},
                                "verbatim_statistics": {"type": "string"},
                                "extraction_confidence": {"type": "number"},
                                "extraction_reasoning": {"type": "string"}
                            },
                            "required": [
                                "feature_names",
                                "variant_names",
                                "disease_name",
                                "evidence_type",
                                "evidence_level",
                                "evidence_direction",
                                "evidence_significance",
                                "evidence_description",
                                "source_page_numbers",
                                "verbatim_quote",
                                "extraction_confidence",
                                "extraction_reasoning"
                            ]
                        },
                        "description": "Array of evidence items to save"
                    }
                },
                "required": ["items"]
            }
        }
    ]