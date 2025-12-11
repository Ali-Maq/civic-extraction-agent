
import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
# Add civic_extraction to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from tools.normalization_tools import normalize_evidence_item_async

async def run_robustness_test():
    """
    Test Phase 3: Robustness (Typos) and Missing Fields (PMCID).
    """
    print(f"=== TESTING ROBUSTNESS & PMCID ===")
    
    # Mock Item with Typos and a PMID
    test_item = {
        "feature_names": "KIT",
        "variant_names": "D820Y",
        "disease_name": "Mellanoma",  # Typo (Double l)
        "therapy_names": "Imatnib",   # Typo (Missing i)
        "source_citation_id": "PMID:23775962", # Hodi 2013 PMID
        "clinical_trial_nct_ids": "NCT00424515",
        "feature_types": "GENE"
    }
    
    print("\n--- Input Item ---")
    print(f"Disease: {test_item['disease_name']} (Expected: Melanoma -> EFO ID)")
    print(f"Therapy: {test_item['therapy_names']} (Expected: Imatinib -> RxNorm/NCIt)")
    print(f"PMID: {test_item['source_citation_id']} (Expected: PMCID lookup)")
    
    # Run Normalization
    print("\n--- Running Normalization ---")
    normalized = await normalize_evidence_item_async(test_item)
    
    # Verify Results
    print("\n--- Verification ---")
    
    # 1. Disease Typo Check
    efo_id = normalized.get("disease_efo_id")
    # Melanoma is EFO:0000756
    if efo_id == "EFO:0000756":
        print(f"✅ Disease Typo Handled: 'Mellanoma' -> {efo_id}")
    else:
        print(f"❌ Disease Typo FAILED: Got {efo_id}")

    # 2. Therapy Typo Check
    # Check RxNorm
    rxnorm = normalized.get("therapy_rxnorm_ids", "")
    # Imatinib RxNorm is 282388
    if "282388" in rxnorm:
        print(f"✅ Therapy RxNorm Typo Handled: 'Imatnib' -> {rxnorm}")
    else:
        print(f"❌ Therapy RxNorm Typo FAILED: Got {rxnorm}")
        
    # Check NCIt
    ncit = normalized.get("therapy_ncit_ids", "")
    # Imatinib NCIt is C62035
    if "C62035" in ncit:
        print(f"✅ Therapy NCIt Typo Handled: 'Imatnib' -> {ncit}")
    else:
        print(f"❌ Therapy NCIt Typo FAILED: Got {ncit}")

    # 3. PMCID Check
    pmcid = normalized.get("source_pmcid")
    # Hodi 2013 has PMCID: PMC3805934 (Wait, does it? Let's check API response)
    if pmcid and pmcid.startswith("PMC"):
        print(f"✅ PMCID Lookup Success: {pmcid}")
    else:
        print(f"❌ PMCID Lookup FAILED: Got {pmcid}")

    # Check Errors
    errors = normalized.get("_normalization", {}).get("lookup_errors", [])
    if errors:
        print(f"⚠️ Lookup Errors: {json.dumps(errors, indent=2)}")
    else:
        print("✅ No Lookup Errors")

if __name__ == "__main__":
    asyncio.run(run_robustness_test())

