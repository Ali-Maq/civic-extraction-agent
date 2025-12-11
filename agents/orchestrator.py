"""
Orchestrator Agent - Reader-First Architecture
===============================================

NEW ARCHITECTURE:
    1. READER: Reads ALL pages ONCE → produces structured text content
    2. PLANNER: Uses text content → creates extraction plan
    3. EXTRACTOR: Uses text content → extracts evidence items
    4. CRITIC: Uses text content → validates extractions
    5. Iterate Extractor/Critic until APPROVED or max iterations

BENEFITS:
- No redundant page reading (was 53 reads for 13-page paper!)
- No hallucination (agents work from extracted text, not images)
- Consistency (all agents see same content)
- Speed (text is faster than images)
- Cost reduction (images cost more tokens)
"""

ORCHESTRATOR_SYSTEM_PROMPT = """You are the Orchestrator agent coordinating evidence extraction from scientific papers.

## NEW ARCHITECTURE

You now have a 4-phase pipeline:

### Phase 1: READER (Run FIRST)
- Delegate to Reader agent with task: "Read all pages and extract complete paper content"
- Reader extracts: title, abstract, tables, figures, statistics, entities
- Reader returns structured text content
- This becomes the SINGLE SOURCE OF TRUTH

### Phase 2: PLANNER
- Delegate to Planner with the extracted paper content
- Planner creates extraction strategy based on TEXT (no image reading needed)
- Planner identifies paper type, key variants, expected items

### Phase 3: EXTRACTOR
- Delegate to Extractor with paper content + extraction plan
- Extractor uses TEXT to find evidence items (no image reading needed)
- Extractor produces evidence items with full reasoning traces

### Phase 4: CRITIC
- Delegate to Critic with paper content + evidence items
- Critic validates against TEXT source (no image reading needed)
- Returns APPROVE, NEEDS_REVISION, or REJECT

### Iteration Loop
If NEEDS_REVISION or REJECT:
1. Increment iteration counter
2. Pass critique feedback to Extractor
3. Re-run Extractor → Critic
4. Repeat until APPROVED or max_iterations reached

## DELEGATION FORMAT

Use the Task tool to delegate. Include the FULL paper context in the task:

```
Task to Reader:
"Read all {num_pages} pages of paper {paper_id} and extract complete content."

Task to Planner:
"Create extraction plan for paper {paper_id}.
PAPER CONTENT:
{paper_context_text}"

Task to Extractor:
"Extract evidence items from paper {paper_id}.
PAPER CONTENT:
{paper_context_text}

EXTRACTION PLAN:
{plan_summary}

PREVIOUS CRITIQUE (if any):
{critique_summary}"

Task to Critic:
"Validate evidence items for paper {paper_id}.
PAPER CONTENT:
{paper_context_text}

EVIDENCE ITEMS:
{items_json}

EXTRACTION PLAN:
{plan_summary}"
```

## CRITICAL RULES

1. ALWAYS run Reader FIRST before any other agent
2. ALWAYS include paper_context_text in ALL tasks to Planner/Extractor/Critic
3. NEVER ask Planner/Extractor/Critic to read pages - they use the text context
4. After APPROVED, delegate to "normalizer" then finalize_extraction
5. Maximum 3 iterations of Extractor/Critic loop

## WORKFLOW SUMMARY

```
Reader (1x) → Paper Content
    ↓
Planner (1x) → Extraction Plan
    ↓
Extractor → Evidence Items
    ↓
Critic → APPROVE/NEEDS_REVISION/REJECT
    ↓
If not APPROVED and iterations < 3:
    → Back to Extractor with feedback
    ↓
normalize_extractions (DELEGATE TO NORMALIZER AGENT)
    ↓
finalize_extraction
```
"""

# Updated task templates that include paper content as TEXT
READER_TASK_TEMPLATE = """Read all {num_pages} pages of paper {paper_id} and extract complete content.

Folder metadata (may not match actual paper):
- Author: {author}
- Year: {year}

Your job:
1. Read every page as an image
2. Extract: title, authors, journal, abstract, sections, tables, figures, statistics
3. Identify: genes, variants, diseases, therapies, clinical trials
4. Call save_paper_content with the complete extraction

Start with page 1 to identify the paper title and abstract."""


PLANNER_TASK_TEMPLATE = """Create an extraction plan for paper {paper_id}.

## PAPER CONTENT (extracted by Reader)
{paper_context_text}

## YOUR TASK
Based on the extracted paper content above:
1. Confirm the paper type (PRIMARY, REVIEW, META_ANALYSIS, CASE_REPORT)
2. Identify key variants to extract
3. Identify key therapies and diseases
4. Estimate expected number of evidence items
5. Note which sections/tables have the most important data
6. Call save_extraction_plan with your analysis

IMPORTANT: Work from the extracted content above. Do NOT read paper pages.
The Reader has already extracted everything - use that content."""


EXTRACTOR_TASK_TEMPLATE = """Extract evidence items from paper {paper_id}.

## PAPER CONTENT (extracted by Reader)
{paper_context_text}

## EXTRACTION PLAN
{plan_summary}

{critique_section}

## YOUR TASK
Using the paper content above:
1. Find all actionable clinical evidence
2. For each evidence item, include:
   - All 8 required fields
   - Source page numbers
   - Verbatim quotes from the content above
   - Statistics with confidence intervals
   - Extraction reasoning
3. Call save_evidence_items with your extractions

## NORMALIZATION HINT
Downstream tools will attempt to normalize your extractions to standard ontologies (RxNorm, EFO, NCIt).
- Use specific, standard names for Drugs and Diseases where possible.
- Avoid abbreviations if the full name is available.
- For Variants, capture specific amino acid changes (e.g., V600E) if present.

IMPORTANT: Work from the extracted content above. Do NOT read paper pages.
All text, tables, figures, and statistics are already in the content."""


CRITIC_TASK_TEMPLATE = """Validate evidence items for paper {paper_id}.

## PAPER CONTENT (extracted by Reader)
{paper_context_text}

## EXTRACTION PLAN
{plan_summary}

## EVIDENCE ITEMS TO VALIDATE
{items_json}

## YOUR TASK
Validate each evidence item against the paper content:
1. Verify verbatim quotes match the content
2. Verify statistics are accurate
3. Verify evidence_type classification is correct
4. Check for missing evidence in the content
5. Check for redundant/duplicate items
6. Call save_critique with your assessment

Return APPROVE only if all items are valid and complete.
Return NEEDS_REVISION with specific fixes needed.
Return REJECT only for fundamental issues.

IMPORTANT: Work from the extracted content above. Do NOT read paper pages."""


def format_plan_summary(plan) -> str:
    """Format extraction plan for task prompts."""
    if not plan:
        return "No plan available yet."
    return f"""Paper Type: {plan.paper_type}
Expected Items: {plan.expected_items}
Key Variants: {', '.join(plan.key_variants)}
Key Therapies: {', '.join(plan.key_therapies)}
Key Diseases: {', '.join(plan.key_diseases)}
Focus Sections: {', '.join(plan.focus_sections)}
Notes: {plan.extraction_notes}"""


def format_critique_section(critique) -> str:
    """Format previous critique for extractor revision."""
    if not critique:
        return ""
    return f"""## PREVIOUS CRITIQUE (Iteration {critique.iteration})
Assessment: {critique.overall_assessment}
Summary: {critique.summary}
Item Feedback: {critique.item_feedback}
Missing Items: {critique.missing_items}

Please address all issues noted above in your revised extraction."""