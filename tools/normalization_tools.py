"""
Normalization Tools
===================

Tools for normalizing evidence items by looking up database IDs.
Uses public APIs for Tier 2 field lookups:
- MyGene.info for gene Entrez IDs
- MyVariant.info for variant annotations
- OLS/DOID for disease DOIDs
- OLS/NCIt for therapy NCIt IDs
- PubMed E-utilities for PMIDs
- SO mappings for variant type IDs

Tier 2 Fields (20 fields requiring database lookups):
- disease_doid
- gene_entrez_ids
- therapy_ncit_ids
- factor_ncit_ids
- variant_type_soids
- variant_clinvar_ids
- variant_allele_registry_ids
- variant_mane_select_transcripts
- phenotype_ids
- phenotype_hpo_ids
- source_citation_id (PMID)
- source_pmcid
- chromosome
- start_position
- stop_position
- reference_build
- representative_transcript
- reference_bases
- variant_bases
- coordinate_type
"""

from typing import Dict, Any, List, Optional
import re
import json
import urllib.parse
import aiohttp
from datetime import datetime

# Import from existing normalization module
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from claude_agent_sdk import tool
from context import require_context
from config import OUTPUTS_DIR

# Lazy imports to avoid circular dependencies
_variant_annotator = None


def get_variant_annotator_async():
    """Lazy load the async variant annotator."""
    global _variant_annotator
    if _variant_annotator is None:
        try:
            from normalization.variant_annotator import annotate_variant_async
        except ImportError:
            from civic_extraction.normalization.variant_annotator import annotate_variant_async
        _variant_annotator = annotate_variant_async
    return _variant_annotator

def get_variant_annotator():
    """Lazy load the variant annotator."""
    global _variant_annotator
    if _variant_annotator is None:
        try:
            from normalization.variant_annotator import annotate_variant
        except ImportError:
            from civic_extraction.normalization.variant_annotator import annotate_variant
        _variant_annotator = annotate_variant
    return _variant_annotator


def _dump_checkpoint(filename: str, extra_data: dict = None):
    """Helper to save checkpoint to disk."""
    try:
        ctx = require_context()
        if not ctx.paper: return # Can't save if paper_id unknown
        
        paper_id = ctx.paper.paper_id
        checkpoint_dir = OUTPUTS_DIR / "checkpoints" / paper_id
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        checkpoint_path = checkpoint_dir / filename
        
        # Base data from context state
        data = {
            "paper_id": paper_id,
            "timestamp": datetime.now().isoformat(),
            # Include minimal context to allow resume
            "paper_content": ctx.paper_content,
        }
        
        # Merge extra data
        if extra_data:
            data.update(extra_data)
            
        with open(checkpoint_path, "w") as f:
            json.dump(data, f, indent=2, default=str)
            
    except Exception as e:
        print(f"Warning: Failed to save checkpoint {filename}: {e}")


# ============================================================================
# TIER 1 FIELDS (for coverage calculation)
# ============================================================================

TIER_1_FIELDS = [
    # Core fields (8 required)
    "feature_names",
    "variant_names",
    "disease_name",
    "evidence_type",
    "evidence_level",
    "evidence_direction",
    "evidence_significance",
    "evidence_description",
    # Variant fields
    "variant_origin",
    "variant_type_names",
    "variant_hgvs_descriptions",
    "molecular_profile_name",
    "fusion_five_prime_gene_names",
    "fusion_three_prime_gene_names",
    # Feature fields
    "feature_full_names",
    "feature_types",
    # Disease fields
    "disease_display_name",
    # Therapy fields
    "therapy_names",
    "therapy_interaction_type",
    # Source fields
    "source_title",
    "source_publication_year",
    "source_journal",
    # Clinical trial fields
    "clinical_trial_nct_ids",
    "clinical_trial_names",
    # Phenotype
    "phenotype_names",
]


# ============================================================================
# TIER 2 FIELDS - 20 fields requiring database lookups
# ============================================================================

TIER_2_FIELDS = [
    # Ontology IDs
    "disease_doid",
    "gene_entrez_ids",
    "therapy_ncit_ids",
    "factor_ncit_ids",
    "variant_type_soids",

    # Variant identifiers
    "variant_clinvar_ids",
    "variant_allele_registry_ids",
    "variant_mane_select_transcripts",

    # Phenotype IDs
    "phenotype_ids",
    "phenotype_hpo_ids",

    # Source IDs
    "source_citation_id",
    "source_pmcid",

    # Genomic coordinates
    "chromosome",
    "start_position",
    "stop_position",
    "reference_build",
    "representative_transcript",
    "reference_bases",
    "variant_bases",
    "coordinate_type",
]


# ============================================================================
# GENERIC VARIANT TERMS (Cannot be looked up in databases)
# ============================================================================

GENERIC_VARIANT_TERMS = {
    "mutation", "mutations", "mutant", "mutated",
    "wild type", "wild-type", "wildtype", "wt",
    "amplification", "amplified",
    "deletion", "deleted", "del",
    "expression", "overexpression", "underexpression",
    "loss", "loss of function", "lof",
    "gain", "gain of function", "gof",
    "alteration", "altered", "variant", "variants",
    "positive", "negative",
    "high", "low",
    "any", "any mutation", "any variant",
}


def is_specific_variant(variant_name: str) -> bool:
    """
    Check if a variant name is specific enough to look up.
    
    Specific variants: V600E, L858R, T790M, p.V600E, EXON 19 DELETION
    Generic terms: MUTATION, WILD TYPE, AMPLIFICATION (without position)
    
    Args:
        variant_name: Variant name to check (str or list)
        
    Returns:
        True if variant is specific, False if generic
    """
    if not variant_name:
        return False
        
    # Handle list input gracefully
    if isinstance(variant_name, list):
        if not variant_name:
            return False
        variant_name = str(variant_name[0])
    
    normalized = variant_name.lower().strip()
    
    # Check if it's a known generic term
    if normalized in GENERIC_VARIANT_TERMS:
        return False
    
    # Check for amino acid change patterns: V600E, L858R, p.Val600Glu
    aa_pattern = re.compile(r'^p?\.?[A-Z][a-z]{0,2}\d+[A-Z][a-z]{0,2}$', re.IGNORECASE)
    if aa_pattern.match(normalized.replace(" ", "")):
        return True
    
    # Check for exon patterns: EXON 19 DELETION, exon19del
    exon_pattern = re.compile(r'exon\s*\d+', re.IGNORECASE)
    if exon_pattern.search(normalized):
        return True
    
    # Check for fusion patterns: EML4-ALK, BCR::ABL1
    fusion_pattern = re.compile(r'^[A-Z0-9]+[-:][:|-][A-Z0-9]+$', re.IGNORECASE)
    if fusion_pattern.match(normalized.replace(" ", "")):
        return True
    
    # Check for HGVS patterns: c.1799T>A, g.55249071C>T
    hgvs_pattern = re.compile(r'[cgp]\.\d+', re.IGNORECASE)
    if hgvs_pattern.search(normalized):
        return True
    
    # Check for rsID: rs121434569
    if normalized.startswith("rs") and normalized[2:].isdigit():
        return True
    
    # If variant has numbers and letters mixed (likely specific)
    has_numbers = any(c.isdigit() for c in variant_name)
    has_letters = any(c.isalpha() for c in variant_name)
    if has_numbers and has_letters and len(variant_name) < 20:
        return True
    
    return False


def lookup_gene_entrez_id(gene_symbol: str) -> Dict[str, Any]:
    """
    Look up Entrez Gene ID for a gene symbol.
    
    Uses MyGene.info API.

    Args:
        gene_symbol: Gene symbol (e.g., "EGFR", "BRAF")

    Returns:
        Dict with gene_entrez_id if found
    """
    try:
        # Handle list input
        if isinstance(gene_symbol, list):
            gene_symbol = str(gene_symbol[0]) if gene_symbol else ""

        if not gene_symbol:
             return {"found": False, "error": "Empty gene symbol"}

        import requests

        # Query MyGene.info for gene info
        url = f"https://mygene.info/v3/query"
        params = {
            "q": f"symbol:{gene_symbol}",
            "species": "human",
            "fields": "entrezgene,symbol,name"
        }
        
        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            hits = data.get("hits", [])
            if hits:
                hit = hits[0]
                entrez_id = hit.get("entrezgene")
                if entrez_id:
                    return {
                        "found": True,
                        "gene_symbol": hit.get("symbol"),
                        "gene_entrez_id": str(entrez_id),
                        "gene_name": hit.get("name"),
                        "source": "MyGene.info"
                    }

        return {"found": False, "error": f"Gene {gene_symbol} not found"}

    except Exception as e:
        return {"found": False, "error": str(e)}


async def lookup_variant_info_async(gene_symbol: str, variant_name: str) -> Dict[str, Any]:
    """
    Look up variant information from MyVariant.info (Async).
    """
    if not is_specific_variant(variant_name):
        return {
            "found": False, 
            "error": f"'{variant_name}' is a generic term, not a specific variant. Cannot lookup.",
            "skipped": True
        }
    
    try:
        annotate = get_variant_annotator_async()
        result = await annotate(gene_symbol, variant_name)

        if result.get("found"):
            response = {
                "found": True,
                # Genomic coordinates
                "chromosome": result.get("chromosome"),
                "start_position": result.get("start_position"),
                "stop_position": result.get("stop_position"),
                "reference_build": result.get("reference_build", "GRCh37"),
                "reference_bases": result.get("reference_bases"),
                "variant_bases": result.get("variant_bases"),
                "representative_transcript": result.get("representative_transcript"),
                # Identifiers
                "variant_clinvar_ids": result.get("clinvar_id"),
                "variant_cosmic_ids": result.get("cosmic_id"),
                "variant_rsid": result.get("rsid"),
                # HGVS descriptions
                "variant_hgvs_coding": result.get("hgvs_c"),
                "variant_hgvs_c": result.get("hgvs_c"),
                "variant_hgvs_protein": result.get("hgvs_p"),
                "variant_hgvs_p": result.get("hgvs_p"),
                "variant_hgvs_genomic": result.get("hgvs_g"),
                # Gene info
                "gene": result.get("gene"),
                "variant": result.get("variant"),
                "gene_entrez_id": result.get("gene_entrez_id"),
                # Clinical annotations
                "clinical_significance": result.get("clinical_significance"),
                "review_status": result.get("review_status"),
                # Functional predictions
                "cadd_score": result.get("cadd_score"),
                "sift_prediction": result.get("sift_prediction"),
                "polyphen_prediction": result.get("polyphen_prediction"),
                "source": "MyVariant.info"
            }
            return response
        else:
            return {"found": False, "error": result.get("error", "Variant not found")}

    except Exception as e:
        return {"found": False, "error": str(e)}

def lookup_variant_info(gene_symbol: str, variant_name: str) -> Dict[str, Any]:
    """
    Look up variant information from MyVariant.info.

    Returns genomic coordinates, HGVS descriptions, ClinVar IDs, etc.
    
    NOTE: Only works for specific variants (V600E, L858R, etc.)
    Generic terms like "MUTATION" or "WILD TYPE" cannot be looked up.

    Args:
        gene_symbol: Gene symbol (e.g., "EGFR")
        variant_name: Variant name (e.g., "L858R", "T790M")

    Returns:
        Dict with variant annotation fields
    """
    # First check if this is a specific variant we can look up
    if not is_specific_variant(variant_name):
        return {
            "found": False, 
            "error": f"'{variant_name}' is a generic term, not a specific variant. Cannot lookup.",
            "skipped": True
        }
    
    try:
        annotate = get_variant_annotator()
        result = annotate(gene_symbol, variant_name)

        if result.get("found"):
            response = {
                "found": True,
                # Genomic coordinates
                "chromosome": result.get("chromosome"),
                "start_position": result.get("start_position"),
                "stop_position": result.get("stop_position"),
                "reference_build": result.get("reference_build", "GRCh37"),
                "reference_bases": result.get("reference_bases"),
                "variant_bases": result.get("variant_bases"),
                "representative_transcript": result.get("representative_transcript"),
                # Identifiers
                "variant_clinvar_ids": result.get("clinvar_id"),
                "variant_cosmic_ids": result.get("cosmic_id"),
                "variant_rsid": result.get("rsid"),
                # HGVS descriptions (include both legacy and standard keys)
                "variant_hgvs_coding": result.get("hgvs_c"),
                "variant_hgvs_c": result.get("hgvs_c"),
                "variant_hgvs_protein": result.get("hgvs_p"),
                "variant_hgvs_p": result.get("hgvs_p"),
                "variant_hgvs_genomic": result.get("hgvs_g"),
                # Gene info
                "gene": result.get("gene"),
                "variant": result.get("variant"),
                "gene_entrez_id": result.get("gene_entrez_id"),
                # Clinical annotations
                "clinical_significance": result.get("clinical_significance"),
                "review_status": result.get("review_status"),
                # Functional predictions
                "cadd_score": result.get("cadd_score"),
                "sift_prediction": result.get("sift_prediction"),
                "polyphen_prediction": result.get("polyphen_prediction"),
                "source": "MyVariant.info"
            }
            return response
        else:
            return {"found": False, "error": result.get("error", "Variant not found")}

    except Exception as e:
        return {"found": False, "error": str(e)}


def lookup_disease_doid(disease_name: str) -> Dict[str, Any]:
    """
    Look up Disease Ontology ID (DOID) for a disease name.

    Uses the OLS (Ontology Lookup Service) API.

    Args:
        disease_name: Disease name (e.g., "Non-Small Cell Lung Carcinoma", "Melanoma")

    Returns:
        Dict with disease_doid if found
    """
    try:
        # Handle list input
        if isinstance(disease_name, list):
            disease_name = str(disease_name[0]) if disease_name else ""

        if not disease_name:
             return {"found": False, "error": "Empty disease name"}

        import requests

        # Query OLS for disease
        url = "https://www.ebi.ac.uk/ols/api/search"
        params = {
            "q": disease_name,
            "ontology": "doid",
            "rows": 5
        }

        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            docs = data.get("response", {}).get("docs", [])

            if docs:
                best_match = docs[0]
                obo_id = best_match.get("obo_id", "")

                # Extract DOID number - keep full format for CIViC
                doid = None
                if obo_id.startswith("DOID:"):
                    doid = obo_id  # Keep "DOID:1909" format

                return {
                    "found": True,
                    "disease_doid": doid,
                    "disease_obo_id": obo_id,
                    "disease_label": best_match.get("label"),
                    "disease_description": best_match.get("description", [""])[0] if best_match.get("description") else None,
                    "source": "OLS/DOID"
                }

        return {"found": False, "error": f"Disease '{disease_name}' not found in DOID"}

    except Exception as e:
        return {"found": False, "error": str(e)}


async def lookup_therapy_ncit_id_async(therapy_name: str) -> Dict[str, Any]:
    """
    Look up NCI Thesaurus ID for a SINGLE therapy/drug name (Async).
    """
    if not therapy_name:
        return {"found": False, "error": "Empty therapy name"}

    # Handle list input
    if isinstance(therapy_name, list):
        therapy_name = str(therapy_name[0]) if therapy_name else ""
    
    if not therapy_name or not therapy_name.strip():
        return {"found": False, "error": "Empty therapy name"}
    
    # Clean the therapy name
    therapy_name = therapy_name.strip()
    
    try:
        # Query OLS for therapy in NCI Thesaurus
        url = "https://www.ebi.ac.uk/ols/api/search"
        # Increase rows and ensure fuzzy search
        # Using wildcards *term* helps with partial matches in OLS
        search_term = therapy_name
        if len(therapy_name) > 4: # Only use wildcard for longer terms
             search_term = f"*{therapy_name}*"
             
        params = f"q={urllib.parse.quote(search_term)}&ontology=ncit&rows=20&exact=false"
        full_url = f"{url}?{params}"

        async with aiohttp.ClientSession() as session:
            async with session.get(full_url) as response:
                if response.status != 200:
                    return {"found": False, "error": f"HTTP {response.status}"}
                
                data = await response.json()
                docs = data.get("response", {}).get("docs", [])

                # 1. Exact case-insensitive match on Label
                for doc in docs:
                    label = doc.get("label", "").lower()
                    if label == therapy_name.lower():
                        return _format_ncit_result(doc)

                # 2. Match on Synonyms
                # OLS returns 'synonyms' list
                for doc in docs:
                    synonyms = [s.lower() for s in doc.get("synonyms", [])]
                    if therapy_name.lower() in synonyms:
                         return _format_ncit_result(doc)

                # 3. Fuzzy/Partial Match (if no exact)
                # If we used wildcards, the first result might be good enough if score is high?
                # OLS sorts by relevance.
                if docs:
                    # Return first result but mark as fuzzy? 
                    # For now just return it as OLS ranking is usually okay.
                    return _format_ncit_result(docs[0])

        return {"found": False, "error": f"Therapy '{therapy_name}' not found in NCIt"}

    except Exception as e:
        return {"found": False, "error": str(e)}

def _format_ncit_result(doc):
    """Helper to format OLS NCIt result"""
    obo_id = doc.get("obo_id", "")
    ncit_id = None
    if obo_id.startswith("NCIT:"):
        ncit_id = obo_id
    elif "NCIT_" in obo_id:
        ncit_id = "NCIT:" + obo_id.split("NCIT_")[-1]
    
    if ncit_id:
        return {
            "found": True,
            "therapy_ncit_id": ncit_id,
            "therapy_label": doc.get("label"),
            "source": "OLS/NCIt"
        }
    return {"found": False, "error": "Invalid ID format"}

def lookup_therapy_ncit_id(therapy_name: str) -> Dict[str, Any]:
    """
    Look up NCI Thesaurus ID for a SINGLE therapy/drug name.

    Uses the OLS (Ontology Lookup Service) API.
    
    NOTE: This function expects a SINGLE drug name.
    For multiple drugs, call this function for each drug separately.

    Args:
        therapy_name: Single drug/therapy name (e.g., "Erlotinib", "Pembrolizumab")

    Returns:
        Dict with therapy_ncit_id if found
    """
    if not therapy_name:
        return {"found": False, "error": "Empty therapy name"}

    # Handle list input
    if isinstance(therapy_name, list):
        therapy_name = str(therapy_name[0]) if therapy_name else ""
    
    if not therapy_name or not therapy_name.strip():
        return {"found": False, "error": "Empty therapy name"}
    
    # Clean the therapy name
    therapy_name = therapy_name.strip()
    
    try:
        import requests

        # Query OLS for therapy in NCI Thesaurus
        url = "https://www.ebi.ac.uk/ols/api/search"
        params = {
            "q": therapy_name,
            "ontology": "ncit",
            "rows": 10,  # Get more results to find better match
            "exact": "false"
        }

        response = requests.get(url, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            docs = data.get("response", {}).get("docs", [])

            # Try to find exact match first
            for doc in docs:
                label = doc.get("label", "").lower()
                if label == therapy_name.lower():
                    obo_id = doc.get("obo_id", "")
                    ncit_id = None
                    if obo_id.startswith("NCIT:"):
                        ncit_id = obo_id  # Keep full format "NCIT:C1234"
                    elif "NCIT_" in obo_id:
                        ncit_id = "NCIT:" + obo_id.split("NCIT_")[-1]
                    
                    if ncit_id:
                        return {
                            "found": True,
                            "therapy_ncit_id": ncit_id,
                            "therapy_label": doc.get("label"),
                            "source": "OLS/NCIt"
                        }
            
            # If no exact match, use first result
            if docs:
                best_match = docs[0]
                obo_id = best_match.get("obo_id", "")

                ncit_id = None
                if obo_id.startswith("NCIT:"):
                    ncit_id = obo_id
                elif "NCIT_" in obo_id:
                    ncit_id = "NCIT:" + obo_id.split("NCIT_")[-1]

                if ncit_id:
                    return {
                        "found": True,
                        "therapy_ncit_id": ncit_id,
                        "therapy_label": best_match.get("label"),
                        "source": "OLS/NCIt"
                    }

        return {"found": False, "error": f"Therapy '{therapy_name}' not found in NCIt"}

    except Exception as e:
        return {"found": False, "error": str(e)}


def lookup_therapies(therapy_string: str) -> Dict[str, Any]:
    """
    Look up NCIt IDs for one or more therapies.
    
    Handles comma-separated therapy strings by splitting and looking up each.
    
    Args:
        therapy_string: One or more drug names, comma-separated (or list of strings)
                       e.g., "Pembrolizumab" or "Dabrafenib,Trametinib"
    
    Returns:
        Dict with combined results
    """
    if not therapy_string:
        return {"found": False, "error": "No therapy provided"}
    
    # Handle list input
    if isinstance(therapy_string, list):
        # Join list elements with comma
        therapy_string = ",".join([str(t) for t in therapy_string if t])

    # Split by comma and clean each drug name
    drugs = [d.strip() for d in therapy_string.split(",") if d.strip()]
    
    if not drugs:
        return {"found": False, "error": "No valid therapy names after parsing"}
    
    ncit_ids = []
    labels = []
    errors = []
    
    for drug in drugs:
        result = lookup_therapy_ncit_id(drug)
        if result.get("found"):
            ncit_ids.append(result["therapy_ncit_id"])
            labels.append(result.get("therapy_label", drug))
        else:
            errors.append(f"{drug}: {result.get('error', 'not found')}")
    
    if ncit_ids:
        return {
            "found": True,
            "therapy_ncit_ids": ";".join(ncit_ids),
            "therapy_labels": ";".join(labels),
            "drugs_found": len(ncit_ids),
            "drugs_total": len(drugs),
            "errors": errors if errors else None,
            "source": "OLS/NCIt"
        }
    else:
        return {
            "found": False,
            "error": f"No therapies found: {'; '.join(errors)}"
        }


def lookup_pmid_by_title(paper_title: str) -> Dict[str, Any]:
    """
    Look up PubMed ID (PMID) by paper title.

    Uses the NCBI E-utilities API.

    Args:
        paper_title: Paper title to search

    Returns:
        Dict with source_citation_id (PMID) if found
    """
    if not paper_title or len(paper_title) < 10:
        return {"found": False, "error": "Paper title too short or empty"}
    
    try:
        import requests

        # Use NCBI E-utilities
        search_url = "https://eutils.ncbi.nlm.nih.gov/entrez/eutils/esearch.fcgi"
        
        # First try exact title match
        params = {
            "db": "pubmed",
            "term": f'"{paper_title}"[Title]',
            "retmode": "json",
            "retmax": 5
        }

        response = requests.get(search_url, params=params, timeout=10)

        if response.status_code == 200:
            data = response.json()
            id_list = data.get("esearchresult", {}).get("idlist", [])

            if id_list:
                pmid = id_list[0]
                return {
                    "found": True,
                    "source_citation_id": pmid,
                    "source_pmid": pmid,
                    "source": "PubMed/NCBI"
                }
        
        # If exact match fails, try broader search
        # Take first 100 chars of title for fuzzy search
        short_title = paper_title[:100] if len(paper_title) > 100 else paper_title
        params["term"] = f'{short_title}[Title]'
        
        response = requests.get(search_url, params=params, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            id_list = data.get("esearchresult", {}).get("idlist", [])

            if id_list:
                pmid = id_list[0]
                return {
                    "found": True,
                    "source_citation_id": pmid,
                    "source_pmid": pmid,
                    "source": "PubMed/NCBI",
                    "match_type": "fuzzy"
                }

        return {"found": False, "error": f"Paper not found in PubMed"}

    except Exception as e:
        return {"found": False, "error": str(e)}


def lookup_variant_type_so_id(variant_type_name: str) -> Dict[str, Any]:
    """
    Look up Sequence Ontology ID for a variant type.
    
    Common mappings:
    - Missense Variant -> SO:0001583
    - Frameshift Truncation -> SO:0001589
    - In-frame Deletion -> SO:0001822
    - Amplification -> SO:0001742
    - Fusion -> SO:0001886
    - etc.

    Args:
        variant_type_name: Variant type (e.g., "Missense Variant", "Fusion")

    Returns:
        Dict with variant_type_soid if found
    """
    if not variant_type_name:
        return {"found": False, "error": "No variant type provided"}
    
    # Handle list input
    if isinstance(variant_type_name, list):
        variant_type_name = str(variant_type_name[0]) if variant_type_name else ""
    
    if not variant_type_name:
         return {"found": False, "error": "Empty variant type"}

    # Common SO term mappings (case-insensitive)
    SO_MAPPINGS = {
        # Point mutations
        "missense variant": "SO:0001583",
        "missense": "SO:0001583",
        "missense mutation": "SO:0001583",
        
        # Frameshift
        "frameshift truncation": "SO:0001589",
        "frameshift": "SO:0001589",
        "frameshift variant": "SO:0001589",
        "frameshift mutation": "SO:0001589",
        
        # Deletions
        "in-frame deletion": "SO:0001822",
        "inframe deletion": "SO:0001822",
        "deletion": "SO:0000159",
        "exon deletion": "SO:0001826",
        
        # Insertions
        "in-frame insertion": "SO:0001821",
        "inframe insertion": "SO:0001821",
        "insertion": "SO:0000667",
        "exon insertion": "SO:0001825",
        
        # Copy number
        "amplification": "SO:0001742",
        "copy number amplification": "SO:0001742",
        "loss": "SO:0001878",
        "copy number loss": "SO:0001878",
        "gain": "SO:0001879",
        "copy number gain": "SO:0001879",
        "duplication": "SO:1000035",
        "tandem duplication": "SO:1000173",
        
        # Fusions
        "fusion": "SO:0001886",
        "gene fusion": "SO:0001886",
        "transcript fusion": "SO:0001886",
        
        # Nonsense
        "nonsense": "SO:0001587",
        "stop gained": "SO:0001587",
        "stop gain": "SO:0001587",
        "truncating": "SO:0001587",
        
        # Splice
        "splice site variant": "SO:0001629",
        "splice site": "SO:0001629",
        "splice donor variant": "SO:0001575",
        "splice acceptor variant": "SO:0001574",
        "splicing": "SO:0001629",
        
        # Synonymous
        "synonymous variant": "SO:0001819",
        "synonymous": "SO:0001819",
        "silent": "SO:0001819",
        
        # Structural
        "translocation": "SO:0000199",
        "chromosomal translocation": "SO:0000199",
        "inversion": "SO:1000036",
        
        # SNV
        "mutation": "SO:0001059",
        "point mutation": "SO:1000008",
        "snv": "SO:0001483",
        "single nucleotide variant": "SO:0001483",
        "snp": "SO:0000694",
        
        # Expression
        "expression": "SO:0001026",
        "overexpression": "SO:0001026",
        "underexpression": "SO:0001026",
        
        # Wild type
        "wild type": "SO:0000817",
        "wildtype": "SO:0000817",
        "wild-type": "SO:0000817",
    }

    normalized = variant_type_name.lower().strip()

    if normalized in SO_MAPPINGS:
        return {
            "found": True,
            "variant_type_soid": SO_MAPPINGS[normalized],
            "variant_type_name": variant_type_name,
            "source": "SO (Sequence Ontology)"
        }

    # Try partial match
    for key, soid in SO_MAPPINGS.items():
        if key in normalized or normalized in key:
            return {
                "found": True,
                "variant_type_soid": soid,
                "variant_type_name": variant_type_name,
                "matched_term": key,
                "source": "SO (Sequence Ontology)"
            }

    return {"found": False, "error": f"Variant type '{variant_type_name}' not found in SO mappings"}


# =============================================================================
# NEW: TOOLUNIVERSE INSPIRED LOOKUPS (Direct API Implementation)
# =============================================================================

# Define INTERNAL helper functions first (not tools) for use in normalizer

async def _lookup_rxnorm_internal(drug_name: str) -> Dict[str, Any]:
    """Internal helper for RxNorm lookup."""
    if not drug_name:
        return {"found": False, "error": "Empty drug name"}

    # Handle list input just in case
    if isinstance(drug_name, list):
         drug_name = str(drug_name[0]) if drug_name else ""
         if not drug_name:
             return {"found": False, "error": "Empty drug name"}
        
    base_url = "https://rxnav.nlm.nih.gov/REST"
    url = f"{base_url}/approximateTerm.json?term={urllib.parse.quote(drug_name)}&maxEntries=1"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    return {"found": False, "error": f"HTTP {response.status}"}
                
                data = await response.json()
                if 'approximateGroup' in data and 'candidate' in data['approximateGroup']:
                    candidates = data['approximateGroup']['candidate']
                    if candidates:
                        best = candidates[0]
                        return {
                            "found": True,
                            "rxcui": best.get('rxcui'),
                            "score": best.get('score'),
                            "source": "RxNorm/NLM"
                        }
                return {"found": False, "error": "Not found in RxNorm"}
        except Exception as e:
            return {"found": False, "error": str(e)}

async def _lookup_efo_internal(disease_name: str) -> Dict[str, Any]:
    """Internal helper for EFO lookup."""
    if not disease_name:
        return {"found": False, "error": "Empty disease name"}

    # Handle list input just in case
    if isinstance(disease_name, list):
         disease_name = str(disease_name[0]) if disease_name else ""
         if not disease_name:
             return {"found": False, "error": "Empty disease name"}
    
    # Fuzzy Search Enhancement
    search_term = disease_name
    if len(disease_name) > 4:
         search_term = f"*{disease_name}*"

    base_url = "https://www.ebi.ac.uk/ols/api/search"
    url = f"{base_url}?q={urllib.parse.quote(search_term)}&ontology=efo&rows=5&exact=false"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    return {"found": False, "error": f"HTTP {response.status}"}
                
                data = await response.json()
                if 'response' in data and 'docs' in data['response']:
                    docs = data['response']['docs']
                    
                    if docs:
                        # Return best match (OLS ranks well usually)
                        best = docs[0]
                        return {
                            "found": True,
                            "efo_id": best.get('short_form'),
                            "label": best.get('label'),
                            "description": best.get('description', [])[0] if best.get('description') else None,
                            "source": "EFO/OLS"
                        }
                return {"found": False, "error": "Not found in EFO"}
        except Exception as e:
            return {"found": False, "error": str(e)}

async def _lookup_safety_profile_internal(drug_name: str) -> Dict[str, Any]:
    """Internal helper for Safety lookup."""
    if not drug_name:
        return {"found": False, "error": "Empty drug name"}

    # Handle list input just in case
    if isinstance(drug_name, list):
         drug_name = str(drug_name[0]) if drug_name else ""
         if not drug_name:
             return {"found": False, "error": "Empty drug name"}
        
    base_url = "https://api.fda.gov/drug/event.json"
    url = f"{base_url}?search=patient.drug.medicinalproduct:\"{urllib.parse.quote(drug_name)}\"&count=patient.reaction.reactionmeddrapt.exact&limit=5"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    return {"found": False, "error": f"HTTP {response.status}"}
                
                data = await response.json()
                if 'results' in data:
                    return {
                        "found": True,
                        "top_events": [
                            {"term": item['term'], "count": item['count']}
                            for item in data['results']
                        ],
                        "source": "FAERS/OpenFDA"
                    }
                return {"found": False, "error": "No safety data found"}
        except Exception as e:
            return {"found": False, "error": str(e)}

async def _lookup_clinical_trial_internal(nct_id: str) -> Dict[str, Any]:
    """Internal helper for ClinicalTrials.gov lookup."""
    if not nct_id:
        return {"found": False, "error": "Empty NCT ID"}
        
    # Clean ID
    nct_id = nct_id.strip()
    if not nct_id.startswith("NCT"):
        return {"found": False, "error": "Invalid format (must start with NCT)"}

    base_url = f"https://clinicaltrials.gov/api/v2/studies/{nct_id}"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(base_url) as response:
                if response.status != 200:
                    return {"found": False, "error": f"HTTP {response.status}"}
                
                data = await response.json()
                protocol = data.get("protocolSection", {})
                id_module = protocol.get("identificationModule", {})
                status_module = protocol.get("statusModule", {})
                
                return {
                    "found": True,
                    "nct_id": id_module.get("nctId"),
                    "title": id_module.get("briefTitle"),
                    "status": status_module.get("overallStatus"),
                    "phases": protocol.get("designModule", {}).get("phases", []),
                    "source": "ClinicalTrials.gov API v2"
                }
        except Exception as e:
            return {"found": False, "error": str(e)}

async def _lookup_hpo_internal(phenotype_name: str) -> Dict[str, Any]:
    """Internal helper for HPO lookup."""
    if not phenotype_name:
        return {"found": False, "error": "Empty phenotype"}
        
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
                        "source": "EBI OLS (HPO)"
                    }
                return {"found": False, "error": "Not found in HPO"}
        except Exception as e:
            return {"found": False, "error": str(e)}


async def _lookup_pmcid_internal(pmid: str) -> Dict[str, Any]:
    """Internal helper to convert PMID to PMCID."""
    if not pmid:
        return {"found": False, "error": "Empty PMID"}
    
    # Clean PMID
    pmid_clean = pmid.replace("PMID:", "").strip()
        
    # NEW URL (2025 update - verified via curl)
    base_url = "https://pmc.ncbi.nlm.nih.gov/tools/idconv/api/v1/articles/"
    url = f"{base_url}?tool=civic_agent&email=civic_agent@example.com&ids={pmid_clean}&format=json"
    
    async with aiohttp.ClientSession() as session:
        try:
            async with session.get(url) as response:
                if response.status != 200:
                    return {"found": False, "error": f"HTTP {response.status}"}
                
                data = await response.json()
                records = data.get("records", [])
                if records:
                    record = records[0]
                    pmcid = record.get("pmcid")
                    if pmcid:
                        return {"found": True, "pmcid": pmcid, "source": "NCBI ID Converter"}
                
                return {"found": False, "error": "No PMCID found"}
        except Exception as e:
            return {"found": False, "error": str(e)}


def get_tier2_field_coverage(evidence: Dict[str, Any]) -> Dict[str, Any]:
    """
    Calculate Tier 2 field coverage for an evidence item.

    Args:
        evidence: Evidence item dict

    Returns:
        Dict with coverage statistics
    """
    present = []
    missing = []

    for field in TIER_2_FIELDS:
        if evidence.get(field) is not None:
            present.append(field)
        else:
            missing.append(field)

    return {
        "tier2_fields_present": len(present),
        "tier2_fields_total": len(TIER_2_FIELDS),
        "tier2_coverage_percent": round(len(present) / len(TIER_2_FIELDS) * 100, 1),
        "present": present,
        "missing": missing
    }


# ============================================================================
# MCP TOOLS - Required by tools/__init__.py
# ============================================================================

@tool(
    "finalize_extraction",
    """Finalize the extraction after approval and normalization.
    
    This marks the extraction as complete and copies draft items to final.
    Call this as the LAST step after normalize_extractions.""",
    {}
)
async def finalize_extraction(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    MCP Tool: Finalize the extraction process.
    
    This should be called after:
    1. Critic approves (or max iterations reached)
    2. normalize_extractions has been called
    
    It copies draft_extractions to final_extractions and sets is_complete=True.
    """
    ctx = require_context()
    
    # Copy draft to final
    ctx.state.final_extractions = list(ctx.state.draft_extractions)
    ctx.state.is_complete = True
    
    # SAVE CHECKPOINT 04 (Normalization/Final)
    _dump_checkpoint("04_normalization_output.json", {
        "final_extractions": ctx.state.final_extractions,
        "is_complete": True
    })

    # Calculate coverage statistics
    items_count = len(ctx.state.final_extractions)
    
    # Calculate average Tier 1 and Tier 2 coverage
    tier1_coverages = []
    tier2_coverages = []
    
    for item in ctx.state.final_extractions:
        # Tier 1 coverage
        tier1_present = sum(1 for f in TIER_1_FIELDS if item.get(f) is not None)
        tier1_coverages.append(tier1_present / len(TIER_1_FIELDS) * 100)
        
        # Tier 2 coverage
        tier2_present = sum(1 for f in TIER_2_FIELDS if item.get(f) is not None)
        tier2_coverages.append(tier2_present / len(TIER_2_FIELDS) * 100)
    
    avg_tier1 = round(sum(tier1_coverages) / len(tier1_coverages), 1) if tier1_coverages else 0
    avg_tier2 = round(sum(tier2_coverages) / len(tier2_coverages), 1) if tier2_coverages else 0
    
    result = {
        "success": True,
        "items_extracted": items_count,
        "iterations_used": ctx.state.iteration_count,
        "max_iterations": ctx.state.max_iterations,
        "average_tier1_coverage": avg_tier1,
        "average_tier2_coverage": avg_tier2,
        "message": f"✅ Extraction finalized with {items_count} evidence items."
    }
    
    return {
        "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
    }


@tool(
    "get_tier2_coverage",
    """Get Tier 2 field coverage statistics for all draft extractions.
    
    Returns coverage percentage and lists of present/missing Tier 2 fields
    for each evidence item.""",
    {}
)
async def get_tier2_coverage(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    MCP Tool: Get Tier 2 coverage for all draft extractions.
    """
    ctx = require_context()
    
    if not ctx.state.draft_extractions:
        return {
            "content": [{
                "type": "text",
                "text": json.dumps({
                    "items": 0,
                    "average_coverage": 0,
                    "message": "No draft extractions available"
                }, indent=2)
            }]
        }
    
    item_coverages = []
    
    for i, item in enumerate(ctx.state.draft_extractions):
        coverage = get_tier2_field_coverage(item)
        coverage["item_index"] = i
        coverage["gene"] = item.get("feature_names", "?")
        coverage["variant"] = item.get("variant_names", "?")
        item_coverages.append(coverage)
    
    # Calculate average
    avg_coverage = round(
        sum(c["tier2_coverage_percent"] for c in item_coverages) / len(item_coverages), 
        1
    )
    
    result = {
        "items": len(item_coverages),
        "average_tier2_coverage": avg_coverage,
        "per_item_coverage": item_coverages,
        "tier2_fields_total": len(TIER_2_FIELDS),
    }
    
    return {
        "content": [{"type": "text", "text": json.dumps(result, indent=2)}]
    }


# =============================================================================
# NEW: TOOLUNIVERSE INSPIRED LOOKUPS (Direct API Implementation - MCP TOOLS)
# =============================================================================

@tool(
    "lookup_rxnorm",
    "Lookup a drug in RxNorm to get its RXCUI and canonical name.",
    {"drug_name": str}
)
async def lookup_rxnorm(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Lookup drug in RxNorm to get RXCUI and canonical name.
    """
    drug_name = args.get("drug_name")
    if not drug_name:
        return {"content": [{"type": "text", "text": "Error: Empty drug name"}]}
        
    # Use internal helper
    result = await _lookup_rxnorm_internal(drug_name)
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


@tool(
    "lookup_efo",
    "Lookup a disease in EFO via EBI OLS API.",
    {"disease_name": str}
)
async def lookup_efo(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Lookup disease in EFO via EBI OLS API.
    """
    disease_name = args.get("disease_name")
    if not disease_name:
        return {"content": [{"type": "text", "text": "Error: Empty disease name"}]}
        
    # Use internal helper
    result = await _lookup_efo_internal(disease_name)
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


@tool(
    "lookup_safety_profile",
    "Lookup top adverse events for a drug via OpenFDA (FAERS).",
    {"drug_name": str}
)
async def lookup_safety_profile(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Lookup top adverse events for a drug via OpenFDA (FAERS).
    """
    drug_name = args.get("drug_name")
    if not drug_name:
        return {"content": [{"type": "text", "text": "Error: Empty drug name"}]}
        
    # Use internal helper
    result = await _lookup_safety_profile_internal(drug_name)
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


@tool(
    "lookup_gene_entrez",
    "Lookup Entrez Gene ID for a gene symbol (e.g. BRAF).",
    {"gene_symbol": str}
)
async def lookup_gene_entrez(args: Dict[str, Any]) -> Dict[str, Any]:
    gene_symbol = args.get("gene_symbol")
    if not gene_symbol: return {"content": [{"type": "text", "text": "Error: Empty gene symbol"}]}
    result = lookup_gene_entrez_id(gene_symbol)
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


@tool(
    "lookup_disease_doid",
    "Lookup Disease Ontology ID (DOID) for a disease name via OLS.",
    {"disease_name": str}
)
async def lookup_disease_doid_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    disease_name = args.get("disease_name")
    if not disease_name: return {"content": [{"type": "text", "text": "Error: Empty disease name"}]}
    result = lookup_disease_doid(disease_name)
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


@tool(
    "lookup_therapy_ncit",
    "Lookup NCI Thesaurus ID for a therapy/drug name via OLS.",
    {"therapy_name": str}
)
async def lookup_therapy_ncit(args: Dict[str, Any]) -> Dict[str, Any]:
    therapy_name = args.get("therapy_name")
    if not therapy_name: return {"content": [{"type": "text", "text": "Error: Empty therapy name"}]}
    result = await lookup_therapy_ncit_id_async(therapy_name)
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


@tool(
    "lookup_variant_info",
    "Lookup variant information (coordinates, HGVS, ClinVar) from MyVariant.info.",
    {"gene_symbol": str, "variant_name": str}
)
async def lookup_variant_info_tool(args: Dict[str, Any]) -> Dict[str, Any]:
    gene_symbol = args.get("gene_symbol")
    variant_name = args.get("variant_name")
    if not gene_symbol or not variant_name: 
        return {"content": [{"type": "text", "text": "Error: Missing gene or variant"}]}
    result = await lookup_variant_info_async(gene_symbol, variant_name)
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


@tool(
    "lookup_clinical_trial",
    "Lookup Clinical Trial details (status, title, phases) by NCT ID.",
    {"nct_id": str}
)
async def lookup_clinical_trial(args: Dict[str, Any]) -> Dict[str, Any]:
    nct_id = args.get("nct_id")
    if not nct_id: return {"content": [{"type": "text", "text": "Error: Empty NCT ID"}]}
    result = await _lookup_clinical_trial_internal(nct_id)
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


@tool(
    "lookup_hpo",
    "Lookup Human Phenotype Ontology (HPO) ID for a phenotype name.",
    {"phenotype_name": str}
)
async def lookup_hpo(args: Dict[str, Any]) -> Dict[str, Any]:
    phenotype_name = args.get("phenotype_name")
    if not phenotype_name: return {"content": [{"type": "text", "text": "Error: Empty phenotype name"}]}
    result = await _lookup_hpo_internal(phenotype_name)
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}


@tool(
    "lookup_pmcid",
    "Lookup PMCID for a given PMID using NCBI ID Converter.",
    {"pmid": str}
)
async def lookup_pmcid(args: Dict[str, Any]) -> Dict[str, Any]:
    pmid = args.get("pmid")
    if not pmid: return {"content": [{"type": "text", "text": "Error: Empty PMID"}]}
    result = await _lookup_pmcid_internal(pmid)
    return {"content": [{"type": "text", "text": json.dumps(result, indent=2)}]}

