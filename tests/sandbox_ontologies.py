"""
Sandbox for Clinical Ontology Lookups
=====================================

Prototyping "ToolUniverse" style lookups for:
1. RxNorm (Drugs) via NLM RxNav API
2. EFO (Diseases) via EBI OLS API
3. MedDRA/Adverse Events via FDA FAERS API

Goal: Verify API behavior and response formats before integrating into main codebase.
"""

import asyncio
import aiohttp
import json
import urllib.parse

# =============================================================================
# 1. RxNorm (Drugs) - NLM API
# =============================================================================
async def lookup_rxnorm(drug_name: str) -> dict:
    """
    Lookup drug in RxNorm to get RXCUI and canonical name.
    Matches ToolUniverse `RxNorm_get_drug_names`.
    """
    base_url = "https://rxnav.nlm.nih.gov/REST"
    
    # Endpoint: /approximateTerm maps strings (brand/generic) to RXCUIs
    url = f"{base_url}/approximateTerm.json?term={urllib.parse.quote(drug_name)}&maxEntries=1"
    
    print(f"\n[RxNorm] Searching for: '{drug_name}'...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    return {"error": f"HTTP {response.status}"}
                
                data = await response.json()
                
                # Parse NLM's unique structure
                # response -> approximateGroup -> candidate -> [ {rxcui, score} ]
                if 'approximateGroup' in data and 'candidate' in data['approximateGroup']:
                    candidates = data['approximateGroup']['candidate']
                    if candidates:
                        best = candidates[0]
                        rxcui = best.get('rxcui')
                        
                        # Now get properties (canonical name)
                        prop_url = f"{base_url}/rxcui/{rxcui}/properties.json"
                        async with session.get(prop_url) as prop_response:
                            if prop_response.status == 200:
                                prop_data = await prop_response.json()
                                properties = prop_data.get('properties', {})
                                return {
                                    "status": "found",
                                    "query": drug_name,
                                    "rxcui": rxcui,
                                    "name": properties.get('name', ''),
                                    "synonym": properties.get('synonym', ''),
                                    "tty": properties.get('tty', '') # Term Type (IN=Ingredient, BN=Brand Name)
                                }
                
                return {"status": "not_found", "query": drug_name}
                
        except Exception as e:
            return {"error": str(e)}

# =============================================================================
# 2. EFO (Diseases) - EBI OLS API
# =============================================================================
async def lookup_efo(disease_name: str) -> dict:
    """
    Lookup disease in EFO via EBI OLS.
    Matches ToolUniverse `OSL_get_efo_id_by_disease_name`.
    """
    base_url = "https://www.ebi.ac.uk/ols/api/search"
    # Filter to EFO ontology to match ToolUniverse strategy
    url = f"{base_url}?q={urllib.parse.quote(disease_name)}&ontology=efo&rows=1&exact=false"
    
    print(f"\n[EFO/OLS] Searching for: '{disease_name}'...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    return {"error": f"HTTP {response.status}"}
                
                data = await response.json()
                
                if 'response' in data and 'docs' in data['response']:
                    docs = data['response']['docs']
                    if docs:
                        best = docs[0]
                        return {
                            "status": "found",
                            "query": disease_name,
                            "id": best.get('short_form'), # E.g., EFO_0000311
                            "iri": best.get('iri'),
                            "label": best.get('label'),
                            "ontology_name": best.get('ontology_name'),
                            "description": best.get('description', [])[:1] # First line only
                        }
                
                return {"status": "not_found", "query": disease_name}
                
        except Exception as e:
            return {"error": str(e)}

# =============================================================================
# 3. MedDRA/AEs - OpenFDA FAERS API
# =============================================================================
async def lookup_adverse_events(drug_name: str) -> dict:
    """
    Lookup top adverse events for a drug via OpenFDA (FAERS).
    Approximate ToolUniverse `FAERS_count_reactions_by_drug_event`.
    """
    base_url = "https://api.fda.gov/drug/event.json"
    
    # Count reactions for this medicinal product
    # search=patient.drug.medicinalproduct:"Imatinib"&count=patient.reaction.reactionmeddrapt.exact
    url = f"{base_url}?search=patient.drug.medicinalproduct:\"{urllib.parse.quote(drug_name)}\"&count=patient.reaction.reactionmeddrapt.exact&limit=5"
    
    print(f"\n[FDA/MedDRA] Searching events for: '{drug_name}'...")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    return {"error": f"HTTP {response.status} (Drug might not be in FAERS or name mismatch)"}
                
                data = await response.json()
                
                if 'results' in data:
                    # Returns list of {term: "NAUSEA", count: 1234}
                    top_events = [
                        {"term": item['term'], "count": item['count']}
                        for item in data['results']
                    ]
                    return {
                        "status": "found",
                        "drug": drug_name,
                        "top_meddra_events": top_events
                    }
                
                return {"status": "not_found", "drug": drug_name}
                
        except Exception as e:
            return {"error": str(e)}

# =============================================================================
# Main Test Loop
# =============================================================================
async def main():
    print("=== SANDBOX: CLINICAL ONTOLOGY LOOKUPS ===")
    
    # Test Cases
    drugs = ["Imatinib", "Gleevec", "Vemurafenib", "UnknownDrug123"]
    diseases = ["Melanoma", "Lung Cancer", "Gastrointestinal Stromal Tumor"]
    
    # 1. Run RxNorm Tests
    print("\n--- Testing RxNorm (Drugs) ---")
    for drug in drugs:
        result = await lookup_rxnorm(drug)
        print(json.dumps(result, indent=2))
        
    # 2. Run EFO Tests
    print("\n--- Testing EFO (Diseases) ---")
    for disease in diseases:
        result = await lookup_efo(disease)
        print(json.dumps(result, indent=2))
        
    # 3. Run FAERS Tests (MedDRA)
    print("\n--- Testing FAERS (Adverse Events) ---")
    for drug in ["Imatinib", "Pembrolizumab"]: # Use known drugs
        result = await lookup_adverse_events(drug)
        print(json.dumps(result, indent=2))

if __name__ == "__main__":
    asyncio.run(main())

