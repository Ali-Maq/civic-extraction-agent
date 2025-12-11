
import asyncio
import aiohttp
import json
import urllib.parse
from typing import Dict, Any

async def lookup_clinical_trial(nct_id: str) -> Dict[str, Any]:
    """
    Lookup Clinical Trial details from ClinicalTrials.gov API v2.
    """
    print(f"\n--- Looking up Clinical Trial: {nct_id} ---")
    base_url = f"https://clinicaltrials.gov/api/v2/studies/{nct_id}"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(base_url) as response:
                if response.status != 200:
                    return {"found": False, "error": f"HTTP {response.status}"}
                
                data = await response.json()
                protocol_section = data.get("protocolSection", {})
                id_module = protocol_section.get("identificationModule", {})
                status_module = protocol_section.get("statusModule", {})
                
                return {
                    "found": True,
                    "nct_id": id_module.get("nctId"),
                    "title": id_module.get("briefTitle"),
                    "status": status_module.get("overallStatus"),
                    "phases": protocol_section.get("designModule", {}).get("phases", []),
                    "source": "ClinicalTrials.gov API v2"
                }
        except Exception as e:
            return {"found": False, "error": str(e)}

async def lookup_hpo_phenotype(phenotype_name: str) -> Dict[str, Any]:
    """
    Lookup Phenotype HPO ID via EBI OLS (Ontology Lookup Service).
    """
    print(f"\n--- Looking up Phenotype (HPO): {phenotype_name} ---")
    base_url = "https://www.ebi.ac.uk/ols/api/search"
    query = urllib.parse.quote(phenotype_name)
    url = f"{base_url}?q={query}&ontology=hp&rows=1&exact=false"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    return {"found": False, "error": f"HTTP {response.status}"}
                
                data = await response.json()
                docs = data.get("response", {}).get("docs", [])
                
                if docs:
                    best = docs[0]
                    return {
                        "found": True,
                        "hpo_id": best.get("obo_id"),
                        "label": best.get("label"),
                        "description": best.get("description", [""])[0],
                        "source": "EBI OLS (HPO)"
                    }
                return {"found": False, "error": "Not found in HPO"}
        except Exception as e:
            return {"found": False, "error": str(e)}

async def test_extra_variant_fields(gene: str, variant: str):
    """
    Check MyVariant.info for MANE and Allele Registry IDs.
    """
    print(f"\n--- Checking MyVariant for Advanced Fields: {gene} {variant} ---")
    base_url = "https://myvariant.info/v1/query"
    
    # Try generic query first
    query = f"q={gene} {variant}&fields=clingen,clinvar,mane"
    url = f"{base_url}?{query}"
    print(f"Querying: {url}")
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                data = await response.json()
                hits = data.get("hits", [])
                if hits:
                    hit = hits[0]
                    print(f"Found Hit: {hit.get('_id')}")
                    
                    # Check for MANE
                    mane = hit.get("mane")
                    if mane:
                        print(f"✅ MANE FOUND: {type(mane)}")
                    else:
                        print("❌ MANE Missing")
                        
                    # Check for ClinGen
                    clingen = hit.get("clingen")
                    if clingen:
                         print(f"✅ ClinGen FOUND: {clingen.get('allele_registry_id', 'No Registry ID')}")
                    else:
                         print("❌ ClinGen Missing")

                else:
                    print("No hits found. Trying HGVS...")
                    # Fallback to HGVS if known, or just debug
        except Exception as e:
            print(f"Error: {e}")

async def run_sandbox():
    # 1. Clinical Trials
    # Using a real trial ID found in CIViC papers often (e.g., Imatinib melanoma)
    # Check Hodi 2013 text for a trial ID if possible, or use a known one. 
    # Hodi 2013 mentions: NCT00424515 (from paper check) or generic.
    # Let's try a known one: NCT00470470
    ct_res = await lookup_clinical_trial("NCT00470470")
    print(json.dumps(ct_res, indent=2))
    
    # 2. HPO Phenotype
    # "Melanoma" is a disease, but "Sunburn" or "Pruritus" is a phenotype.
    # Let's try "Pruritus" (Itching), often a side effect.
    hpo_res = await lookup_hpo_phenotype("Pruritus")
    print(json.dumps(hpo_res, indent=2))
    
    # 3. Advanced Variant Fields
    await test_extra_variant_fields("BRAF", "V600E")

if __name__ == "__main__":
    asyncio.run(run_sandbox())

