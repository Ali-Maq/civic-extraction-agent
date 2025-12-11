
import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
# Add civic_extraction to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from context import set_current_context, CIViCContext
from tools.normalization_tools import normalize_evidence_item_async

async def run_phase2_test(extractor_json_path):
    """Test Phase 2 Normalization (ClinicalTrials + HPO) using checkpoint."""
    print(f"=== TESTING PHASE 2 NORMALIZATION ===")
    
    # 1. Load saved state
    with open(extractor_json_path, 'r') as f:
        saved_data = json.load(f)
    
    draft_items = saved_data.get('extraction', {}).get('draft_extractions', [])
    if not draft_items:
        print("❌ No draft items found in checkpoint.")
        return

    # 2. Pick an item and INJECT Phase 2 fields for testing
    # (Since the original extraction might not have them)
    test_item = draft_items[0].copy()
    
    print("\n--- Injecting Test Data ---")
    test_item["clinical_trial_nct_ids"] = "NCT00470470"  # Real trial
    test_item["phenotype_names"] = "Pruritus, Nausea"  # Real HPO terms
    
    # Test Factor lookup by faking a FACTOR type
    test_item_factor = test_item.copy()
    test_item_factor["feature_names"] = "Estrogen Receptor"
    test_item_factor["feature_types"] = "FACTOR"
    
    # Test Typo Robustness
    test_item_typo = test_item.copy()
    test_item_typo["therapy_names"] = "Imatanib" # Typo
    
    # Test PMCID Lookup
    test_item_pmid = test_item.copy()
    test_item_pmid["source_citation_id"] = "23775962" # Hodi 2013 PMID
    
    print(f"Item 1 (Standard): {test_item['feature_names']} {test_item['variant_names']}")
    print(f"Item 2 (Factor): {test_item_factor['feature_names']} (FACTOR)")
    print(f"Item 3 (Typo): {test_item_typo['therapy_names']} (Should be Imatinib)")
    print(f"Item 4 (PMID): {test_item_pmid['source_citation_id']} (Should get PMCID)")
    
    # 3. Run Normalization
    print("\n--- Running Normalization ---")
    normalized = await normalize_evidence_item_async(test_item)
    normalized_factor = await normalize_evidence_item_async(test_item_factor)
    normalized_typo = await normalize_evidence_item_async(test_item_typo)
    normalized_pmcid = await normalize_evidence_item_async(test_item_pmid)
    
    # 4. Verify Results
    print("\n--- Verification ---")
    
    # Check Clinical Trial
    ct_names = normalized.get("clinical_trial_names", "")
    if "Imatinib Mesylate" in ct_names:
        print(f"✅ Clinical Trial Enriched: {ct_names}")
    else:
        print(f"❌ Clinical Trial FAILED: {ct_names}")

    # Check HPO
    hpo_ids = normalized.get("phenotype_hpo_ids", "")
    if "HP:0000989" in hpo_ids:
        print(f"✅ HPO Lookup Success: {hpo_ids}")
    else:
        print(f"❌ HPO Lookup FAILED: {hpo_ids}")
        
    # Check Factor
    factor_id = normalized_factor.get("factor_ncit_ids", "")
    if "NCIT:" in factor_id:
        print(f"✅ Factor NCIt Lookup Success: {factor_id}")
    else:
        print(f"❌ Factor NCIt Lookup FAILED: {factor_id}")
        
    # Check Typo
    rxnorm = normalized_typo.get("therapy_rxnorm_ids", "")
    if "282388" in rxnorm: # Imatinib RXCUI
        print(f"✅ Typo Corrected (Imatanib -> Imatinib): {rxnorm}")
    else:
        print(f"❌ Typo Correction FAILED: {rxnorm}")
        
    # Check PMCID
    pmcid = normalized_pmcid.get("source_pmcid", "")
    if "PMC" in pmcid:
        print(f"✅ PMCID Lookup Success: {pmcid}")
    else:
        print(f"❌ PMCID Lookup FAILED: {pmcid}")



    # Check Tier 2 Fields List
    added_fields = normalized.get("_normalization", {}).get("tier2_fields_added", [])
    if "phenotype_hpo_ids" in added_fields:
        print("✅ 'phenotype_hpo_ids' tracked in Tier 2 list")
    
    # Check Errors
    errors = normalized.get("_normalization", {}).get("lookup_errors", [])
    if errors:
        print(f"⚠️ Lookup Errors: {errors}")
    else:
        print("✅ No Lookup Errors")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_phase2.py <path_to_extractor_output.json>")
        sys.exit(1)
    
    asyncio.run(run_phase2_test(sys.argv[1]))

