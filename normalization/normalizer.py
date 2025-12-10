"""
Evidence Normalizer
===================

Main normalizer class for adding Tier 2 fields via external APIs.
"""

import asyncio
import requests
from dataclasses import dataclass, field
from typing import Any


@dataclass
class NormalizationResult:
    """Result of normalizing an evidence item."""
    success: bool
    fields_added: list[str] = field(default_factory=list)
    errors: list[str] = field(default_factory=list)
    normalized_item: dict = field(default_factory=dict)


class EvidenceNormalizer:
    """
    Normalizes evidence items by looking up Tier 2 fields from external databases.
    
    Uses:
    - MyGene.info for gene Entrez IDs
    - MyVariant.info for variant coordinates and ClinVar IDs
    - OLS (Ontology Lookup Service) for DOID and NCIt IDs
    """
    
    def __init__(self):
        self.mygene_url = "https://mygene.info/v3"
        self.myvariant_url = "https://myvariant.info/v1"
        self.ols_url = "https://www.ebi.ac.uk/ols/api"
        self.timeout = 15
    
    def lookup_gene(self, gene_symbol: str) -> dict:
        """Look up gene information from MyGene.info."""
        try:
            url = f"{self.mygene_url}/query"
            params = {
                "q": f"symbol:{gene_symbol}",
                "species": "human",
                "fields": "entrezgene,symbol,name,alias,ensembl.gene"
            }
            response = requests.get(url, params=params, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                hits = data.get("hits", [])
                if hits:
                    hit = hits[0]
                    return {
                        "found": True,
                        "entrez_id": hit.get("entrezgene"),
                        "symbol": hit.get("symbol"),
                        "name": hit.get("name"),
                        "ensembl_id": hit.get("ensembl", {}).get("gene") if isinstance(hit.get("ensembl"), dict) else None
                    }
            
            return {"found": False, "error": f"Gene '{gene_symbol}' not found"}
        
        except Exception as e:
            return {"found": False, "error": str(e)}
    
    def lookup_disease(self, disease_name: str) -> dict:
        """Look up disease from Disease Ontology via OLS."""
        try:
            url = f"{self.ols_url}/search"
            params = {
                "q": disease_name,
                "ontology": "doid",
                "rows": 10,
                "exact": "false"
            }
            response = requests.get(url, params=params, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                docs = data.get("response", {}).get("docs", [])
                
                # Try to find best match
                for doc in docs:
                    label = doc.get("label", "").lower()
                    if disease_name.lower() in label or label in disease_name.lower():
                        return {
                            "found": True,
                            "doid": doc.get("obo_id"),
                            "name": doc.get("label"),
                            "description": doc.get("description", [""])[0] if doc.get("description") else ""
                        }
                
                # Return first result if no exact match
                if docs:
                    doc = docs[0]
                    return {
                        "found": True,
                        "doid": doc.get("obo_id"),
                        "name": doc.get("label"),
                        "note": "Approximate match"
                    }
            
            return {"found": False, "error": f"Disease '{disease_name}' not found in DOID"}
        
        except Exception as e:
            return {"found": False, "error": str(e)}
    
    def lookup_therapy(self, therapy_name: str) -> dict:
        """Look up therapy from NCI Thesaurus via OLS."""
        try:
            url = f"{self.ols_url}/search"
            params = {
                "q": therapy_name,
                "ontology": "ncit",
                "rows": 10
            }
            response = requests.get(url, params=params, timeout=self.timeout)
            
            if response.status_code == 200:
                data = response.json()
                docs = data.get("response", {}).get("docs", [])
                
                # Look for drug-related terms
                for doc in docs:
                    label = doc.get("label", "")
                    if therapy_name.lower() in label.lower():
                        return {
                            "found": True,
                            "ncit_id": doc.get("obo_id"),
                            "name": doc.get("label")
                        }
                
                if docs:
                    doc = docs[0]
                    return {
                        "found": True,
                        "ncit_id": doc.get("obo_id"),
                        "name": doc.get("label"),
                        "note": "Approximate match"
                    }
            
            return {"found": False, "error": f"Therapy '{therapy_name}' not found in NCIt"}
        
        except Exception as e:
            return {"found": False, "error": str(e)}
    
    def lookup_variant(self, gene: str, variant: str) -> dict:
        """Look up variant from MyVariant.info."""
        try:
            # Try different query formats
            queries = [
                f"{gene}:{variant}",
                f"{gene} {variant}",
                variant
            ]
            
            for query in queries:
                url = f"{self.myvariant_url}/query"
                params = {
                    "q": query,
                    "fields": "clinvar,dbsnp,cadd,dbnsfp,gnomad_genome",
                    "size": 5
                }
                response = requests.get(url, params=params, timeout=self.timeout)
                
                if response.status_code == 200:
                    data = response.json()
                    hits = data.get("hits", [])
                    
                    if hits:
                        hit = hits[0]
                        result = {
                            "found": True,
                            "variant_id": hit.get("_id")
                        }
                        
                        # Parse variant ID for coordinates (format: chrX:g.12345A>G)
                        vid = hit.get("_id", "")
                        if vid.startswith("chr"):
                            parts = vid.split(":")
                            if len(parts) >= 2:
                                result["chromosome"] = parts[0].replace("chr", "")
                                # Extract position
                                pos_part = parts[1]
                                if "g." in pos_part:
                                    pos = pos_part.split("g.")[1]
                                    # Extract just the number
                                    pos_num = ""
                                    for c in pos:
                                        if c.isdigit():
                                            pos_num += c
                                        else:
                                            break
                                    if pos_num:
                                        result["start_position"] = pos_num
                        
                        # ClinVar data
                        clinvar = hit.get("clinvar", {})
                        if clinvar:
                            rcv = clinvar.get("rcv", {})
                            if isinstance(rcv, dict):
                                result["clinvar_id"] = rcv.get("accession")
                                result["clinical_significance"] = rcv.get("clinical_significance")
                            elif isinstance(rcv, list) and rcv:
                                result["clinvar_id"] = rcv[0].get("accession")
                                result["clinical_significance"] = rcv[0].get("clinical_significance")
                        
                        # dbSNP
                        dbsnp = hit.get("dbsnp", {})
                        if dbsnp:
                            result["rsid"] = dbsnp.get("rsid")
                        
                        return result
            
            return {"found": False, "error": f"Variant '{gene}:{variant}' not found"}
        
        except Exception as e:
            return {"found": False, "error": str(e)}
    
    def normalize_item(self, item: dict) -> NormalizationResult:
        """
        Normalize a single evidence item by adding Tier 2 fields.
        
        Args:
            item: Evidence item with Tier 1 fields
            
        Returns:
            NormalizationResult with normalized item
        """
        normalized = item.copy()
        fields_added = []
        errors = []
        
        # Gene lookup
        gene = item.get("feature_names")
        if gene:
            gene_result = self.lookup_gene(gene)
            if gene_result.get("found"):
                normalized["gene_entrez_ids"] = gene_result.get("entrez_id")
                if gene_result.get("entrez_id"):
                    fields_added.append("gene_entrez_ids")
            else:
                errors.append(f"Gene: {gene_result.get('error')}")
        
        # Disease lookup
        disease = item.get("disease_name")
        if disease:
            disease_result = self.lookup_disease(disease)
            if disease_result.get("found"):
                normalized["disease_doid"] = disease_result.get("doid")
                if disease_result.get("doid"):
                    fields_added.append("disease_doid")
            else:
                errors.append(f"Disease: {disease_result.get('error')}")
        
        # Therapy lookup
        therapy = item.get("therapy_names")
        if therapy:
            therapy_result = self.lookup_therapy(therapy)
            if therapy_result.get("found"):
                normalized["therapy_ncit_ids"] = therapy_result.get("ncit_id")
                if therapy_result.get("ncit_id"):
                    fields_added.append("therapy_ncit_ids")
            else:
                errors.append(f"Therapy: {therapy_result.get('error')}")
        
        # Variant lookup
        variant = item.get("variant_names")
        if gene and variant:
            variant_result = self.lookup_variant(gene, variant)
            if variant_result.get("found"):
                if variant_result.get("clinvar_id"):
                    normalized["variant_clinvar_ids"] = variant_result["clinvar_id"]
                    fields_added.append("variant_clinvar_ids")
                if variant_result.get("chromosome"):
                    normalized["chromosome"] = variant_result["chromosome"]
                    fields_added.append("chromosome")
                if variant_result.get("start_position"):
                    normalized["start_position"] = variant_result["start_position"]
                    fields_added.append("start_position")
            else:
                errors.append(f"Variant: {variant_result.get('error')}")
        
        # Add normalization metadata
        normalized["_normalization"] = {
            "normalized": True,
            "fields_added": fields_added,
            "errors": errors
        }
        
        return NormalizationResult(
            success=len(errors) == 0,
            fields_added=fields_added,
            errors=errors,
            normalized_item=normalized
        )
    
    def normalize_items(self, items: list[dict]) -> list[dict]:
        """
        Normalize a list of evidence items.
        
        Args:
            items: List of evidence items
            
        Returns:
            List of normalized items
        """
        normalized = []
        for item in items:
            result = self.normalize_item(item)
            normalized.append(result.normalized_item)
        return normalized