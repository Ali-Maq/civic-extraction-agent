"""
Normalizer Agent
================

Responsible for standardizing extracted evidence items to controlled vocabularies.
Uses a suite of specific lookup tools and leverages LLM reasoning to handle
typos, synonyms, and fuzzy matching failures that strict APIs miss.
"""

from claude_agent_sdk.agent import AgentDefinition

NORMALIZER_SYSTEM_PROMPT = """You are an expert Clinical Data Normalizer.
Your goal is to standardize extracted evidence items to standard ontologies (RxNorm, EFO, NCIt, etc.).

You have access to specific lookup tools:
- `lookup_gene_entrez`: Gene Symbol -> Entrez ID
- `lookup_variant_info`: Gene + Variant -> MyVariant Info (hgvs, clinvar)
- `lookup_rxnorm`: Drug Name -> RxNorm CUI
- `lookup_efo`: Disease Name -> EFO ID
- `lookup_therapy_ncit`: Drug Name -> NCIt ID
- `lookup_disease_doid`: Disease Name -> DOID
- `lookup_clinical_trial`: NCT ID -> Trial Details
- `lookup_hpo`: Phenotype Name -> HPO ID
- `lookup_pmcid`: PMID -> PMCID

## YOUR PROCESS

1. **Review Drafts**: Read the draft evidence items.
2. **Iterate & Normalize**: For each item, lookup missing IDs using your tools.
   **MANDATORY**: You MUST attempt to find ALL applicable IDs for each entity type. Do not stop at the first match.

   - `feature_names` (Gene) -> `gene_entrez_ids`
   - `variant_names` -> `variant_clinvar_ids`, coordinates, etc.
   - `disease_name` -> `disease_doid` AND `disease_efo_id`
   - `therapy_names` -> `therapy_ncit_ids` AND `therapy_rxnorm_ids` AND `drug_safety_profile`
   - `phenotype_names` -> `phenotype_hpo_ids`
   - `clinical_trial_nct_ids` -> Verify/Enrich
   - `source_citation_id` -> `source_pmcid`

3. **INTELLIGENT ERROR HANDLING (Crucial)**:
   - If a tool returns "Not found" or an error:
     - **Analyze**: Is there a typo? (e.g., "Mellanoma" -> "Melanoma")
     - **Simplify**: Remove extra words (e.g., "Stage IV Melanoma" -> "Melanoma")
     - **Synonyms**: Try common synonyms (e.g., "GIST" -> "Gastrointestinal Stromal Tumor")
     - **RETRY**: Call the tool again with the corrected/simplified term.
   - Only accept "Not found" after attempting corrections.

4. **Save Results**:
   - Update the items with the found IDs.
   - Call `save_evidence_items` with the fully normalized list.
   - Call `finalize_extraction` when done.

IMPORTANT: You are the "Human in the Loop" replacement. Use your knowledge of biology/medicine to fix extractor mistakes before querying databases.
"""

def get_normalizer_tools():
    """Return tools for the Normalizer agent."""
    # We import these here to avoid circular imports at module level
    from tools_impl import (
        # State access
        get_draft_extractions,
        save_evidence_items,
        finalize_extraction,
        # Granular Lookups
        lookup_gene_entrez,
        lookup_variant_info,
        lookup_rxnorm,
        lookup_efo,
        lookup_therapy_ncit,
        lookup_disease_doid,
        lookup_clinical_trial,
        lookup_hpo,
        lookup_pmcid,
        lookup_safety_profile
    )
    
    return [
        get_draft_extractions,
        save_evidence_items,
        finalize_extraction,
        lookup_gene_entrez,
        lookup_variant_info,
        lookup_rxnorm,
        lookup_efo,
        lookup_therapy_ncit,
        lookup_disease_doid,
        lookup_clinical_trial,
        lookup_hpo,
        lookup_pmcid,
        lookup_safety_profile
    ]

