"""
Variant Annotator
=================

Specialized variant annotation using MyVariant.info.
"""

import re
import requests
import aiohttp
import asyncio
from dataclasses import dataclass, field
from typing import Any, Dict, Optional, Tuple, Union


@dataclass
class VariantAnnotation:
    """Annotation result for a variant."""
    found: bool = False
    gene: str = ""
    variant: str = ""
    
    # Identifiers
    hgvs_c: str = ""  # cDNA notation
    hgvs_p: str = ""  # Protein notation
    hgvs_g: str = ""  # Genomic notation
    rsid: str = ""
    clinvar_id: str = ""
    cosmic_id: str = ""
    
    # Coordinates
    chromosome: str = ""
    start_position: str = ""
    stop_position: str = ""
    reference_bases: str = ""
    variant_bases: str = ""
    reference_build: str = "GRCh38"
    
    # Clinical
    clinical_significance: str = ""
    review_status: str = ""
    
    # Functional predictions
    cadd_score: float | None = None
    sift_prediction: str = ""
    polyphen_prediction: str = ""
    
    # Errors
    error: str = ""


class VariantAnnotator:
    """
    Annotates variants using MyVariant.info API.
    
    Handles various input formats:
    - Protein changes: V600E, L858R, T790M
    - cDNA changes: c.1799T>A
    - HGVS: p.V600E, c.1799T>A
    - Exon mutations: EXON 11 MUTATION
    """
    
    def __init__(self):
        self.base_url = "https://myvariant.info/v1"
        self.timeout = 15
    
    def _parse_protein_change(self, variant: str) -> tuple[str, str, str] | None:
        """
        Parse protein change notation.
        
        Returns: (ref_aa, position, alt_aa) or None
        """
        # Patterns like V600E, L858R, p.V600E
        pattern = r"p?\.?([A-Z])(\d+)([A-Z*])"
        match = re.match(pattern, variant.upper())
        if match:
            return match.groups()
        return None
    
    async def _query_by_protein_change_async(self, session: aiohttp.ClientSession, gene: str, variant: str) -> dict | None:
        """Query MyVariant.info by protein change (Async)."""
        parsed = self._parse_protein_change(variant)
        if not parsed:
            return None
        
        ref_aa, pos, alt_aa = parsed
        query = f"dbnsfp.genename:{gene} AND dbnsfp.aaref:{ref_aa} AND dbnsfp.aapos:{pos} AND dbnsfp.aaalt:{alt_aa}"
        params = {
            "q": query,
            "fields": "clinvar,dbsnp,cadd,dbnsfp,cosmic",
            "size": 5
        }
        
        try:
            async with session.get(f"{self.base_url}/query", params=params, timeout=self.timeout) as response:
                if response.status == 200:
                    data = await response.json()
                    hits = data.get("hits", [])
                    if hits:
                        return hits[0]
        except Exception:
            pass
        return None

    def _query_by_protein_change(self, gene: str, variant: str) -> dict | None:
        """Query MyVariant.info by protein change."""
        parsed = self._parse_protein_change(variant)
        if not parsed:
            return None
        
        ref_aa, pos, alt_aa = parsed
        
        # Build query
        query = f"dbnsfp.genename:{gene} AND dbnsfp.aaref:{ref_aa} AND dbnsfp.aapos:{pos} AND dbnsfp.aaalt:{alt_aa}"
        
        params = {
            "q": query,
            "fields": "clinvar,dbsnp,cadd,dbnsfp,cosmic",
            "size": 5
        }
        
        response = requests.get(
            f"{self.base_url}/query",
            params=params,
            timeout=self.timeout
        )
        
        if response.status_code == 200:
            data = response.json()
            hits = data.get("hits", [])
            if hits:
                return hits[0]
        
        return None
    
    async def _query_by_hgvs_async(self, session: aiohttp.ClientSession, gene: str, hgvs: str) -> dict | None:
        """Query MyVariant.info by HGVS notation (Async)."""
        params = {
            "q": f"{gene}:{hgvs}",
            "fields": "clinvar,dbsnp,cadd,dbnsfp,cosmic",
            "size": 5
        }
        try:
            async with session.get(f"{self.base_url}/query", params=params, timeout=self.timeout) as response:
                if response.status == 200:
                    data = await response.json()
                    hits = data.get("hits", [])
                    if hits:
                        return hits[0]
        except Exception:
            pass
        return None

    def _query_by_hgvs(self, gene: str, hgvs: str) -> dict | None:
        """Query MyVariant.info by HGVS notation."""
        # Try direct HGVS query
        params = {
            "q": f"{gene}:{hgvs}",
            "fields": "clinvar,dbsnp,cadd,dbnsfp,cosmic",
            "size": 5
        }
        
        response = requests.get(
            f"{self.base_url}/query",
            params=params,
            timeout=self.timeout
        )
        
        if response.status_code == 200:
            data = response.json()
            hits = data.get("hits", [])
            if hits:
                return hits[0]
        
        return None
    
    def _extract_coordinates(self, hit: dict) -> dict:
        """Extract genomic coordinates from MyVariant.info hit."""
        coords = {}
        
        # Try to parse from variant ID (format: chrX:g.12345A>G)
        vid = hit.get("_id", "")
        if vid.startswith("chr"):
            # Parse chromosome
            parts = vid.split(":")
            if len(parts) >= 2:
                coords["chromosome"] = parts[0].replace("chr", "")
                
                # Parse position and bases
                pos_part = parts[1]
                if "g." in pos_part:
                    genomic = pos_part.split("g.")[1]
                    
                    # Handle different mutation types
                    if ">" in genomic:  # SNV: 12345A>G
                        match = re.match(r"(\d+)([ACGT])>([ACGT])", genomic)
                        if match:
                            coords["start_position"] = match.group(1)
                            coords["stop_position"] = match.group(1)
                            coords["reference_bases"] = match.group(2)
                            coords["variant_bases"] = match.group(3)
                    
                    elif "del" in genomic:  # Deletion
                        match = re.match(r"(\d+)(?:_(\d+))?del", genomic)
                        if match:
                            coords["start_position"] = match.group(1)
                            coords["stop_position"] = match.group(2) or match.group(1)
                    
                    elif "ins" in genomic:  # Insertion
                        match = re.match(r"(\d+)_(\d+)ins([ACGT]+)", genomic)
                        if match:
                            coords["start_position"] = match.group(1)
                            coords["stop_position"] = match.group(2)
                            coords["variant_bases"] = match.group(3)
        
        return coords
    
    def _extract_clinvar(self, hit: dict) -> dict:
        """Extract ClinVar information from hit."""
        info = {}
        clinvar = hit.get("clinvar", {})
        
        if clinvar:
            rcv = clinvar.get("rcv", {})
            
            if isinstance(rcv, dict):
                info["clinvar_id"] = rcv.get("accession")
                info["clinical_significance"] = rcv.get("clinical_significance")
                info["review_status"] = rcv.get("review_status")
            elif isinstance(rcv, list) and rcv:
                info["clinvar_id"] = rcv[0].get("accession")
                info["clinical_significance"] = rcv[0].get("clinical_significance")
                info["review_status"] = rcv[0].get("review_status")
            
            # HGVS notations
            hgvs = clinvar.get("hgvs", {})
            if hgvs:
                info["hgvs_c"] = hgvs.get("coding")
                info["hgvs_p"] = hgvs.get("protein")
                info["hgvs_g"] = hgvs.get("genomic")
        
        return info
    
    def _extract_predictions(self, hit: dict) -> dict:
        """Extract functional predictions from hit."""
        predictions = {}
        
        # CADD score
        cadd = hit.get("cadd", {})
        if cadd:
            predictions["cadd_score"] = cadd.get("phred")
        
        # dbNSFP predictions
        dbnsfp = hit.get("dbnsfp", {})
        if dbnsfp:
            sift = dbnsfp.get("sift", {})
            if isinstance(sift, dict):
                predictions["sift_prediction"] = sift.get("pred")
            
            polyphen = dbnsfp.get("polyphen2", {})
            if isinstance(polyphen, dict):
                hdiv = polyphen.get("hdiv", {})
                if isinstance(hdiv, dict):
                    predictions["polyphen_prediction"] = hdiv.get("pred")
        
        return predictions
    
    def _process_hit(self, hit: dict, annotation: VariantAnnotation) -> VariantAnnotation:
        """Process a MyVariant hit into an annotation object."""
        if hit:
            annotation.found = True
            
            # Extract coordinates
            coords = self._extract_coordinates(hit)
            annotation.chromosome = coords.get("chromosome", "")
            annotation.start_position = coords.get("start_position", "")
            annotation.stop_position = coords.get("stop_position", "")
            annotation.reference_bases = coords.get("reference_bases", "")
            annotation.variant_bases = coords.get("variant_bases", "")
            
            # Extract ClinVar info
            clinvar = self._extract_clinvar(hit)
            annotation.clinvar_id = clinvar.get("clinvar_id", "")
            annotation.clinical_significance = clinvar.get("clinical_significance", "")
            annotation.review_status = clinvar.get("review_status", "")
            annotation.hgvs_c = clinvar.get("hgvs_c", "")
            annotation.hgvs_p = clinvar.get("hgvs_p", "")
            annotation.hgvs_g = clinvar.get("hgvs_g", "")
            
            # Extract dbSNP
            dbsnp = hit.get("dbsnp", {})
            if dbsnp:
                annotation.rsid = dbsnp.get("rsid", "")
            
            # Extract predictions
            predictions = self._extract_predictions(hit)
            annotation.cadd_score = predictions.get("cadd_score")
            annotation.sift_prediction = predictions.get("sift_prediction", "")
            annotation.polyphen_prediction = predictions.get("polyphen_prediction", "")
            
            # Extract COSMIC
            cosmic = hit.get("cosmic", {})
            if cosmic:
                annotation.cosmic_id = cosmic.get("cosmic_id", "")
        
        return annotation

    async def annotate_async(self, gene: str, variant: str) -> VariantAnnotation:
        """Annotate a variant asynchronously."""
        annotation = VariantAnnotation(gene=gene, variant=variant)
        
        try:
            async with aiohttp.ClientSession() as session:
                hit = None
                
                # Strategy 1: Protein change
                hit = await self._query_by_protein_change_async(session, gene, variant)
                
                # Strategy 2: HGVS notation
                if not hit:
                    hit = await self._query_by_hgvs_async(session, gene, variant)
                
                # Strategy 3: Direct search
                if not hit:
                    params = {
                        "q": f"{gene} {variant}",
                        "fields": "clinvar,dbsnp,cadd,dbnsfp,cosmic",
                        "size": 5
                    }
                    try:
                        async with session.get(f"{self.base_url}/query", params=params, timeout=self.timeout) as response:
                            if response.status == 200:
                                data = await response.json()
                                hits = data.get("hits", [])
                                if hits:
                                    hit = hits[0]
                    except Exception:
                        pass
                
                if hit:
                    annotation = self._process_hit(hit, annotation)
                else:
                    annotation.error = f"Variant {gene}:{variant} not found in databases"
                    
        except Exception as e:
            annotation.error = str(e)
            
        return annotation

    def annotate(self, gene: str, variant: str) -> VariantAnnotation:
        """
        Annotate a variant (Synchronous).
        
        Args:
            gene: Gene symbol (e.g., "EGFR", "BRAF")
            variant: Variant name (e.g., "V600E", "L858R", "c.1799T>A")
            
        Returns:
            VariantAnnotation with all available information
        """
        annotation = VariantAnnotation(gene=gene, variant=variant)
        
        try:
            # Try different query strategies
            hit = None
            
            # Strategy 1: Protein change
            hit = self._query_by_protein_change(gene, variant)
            
            # Strategy 2: HGVS notation
            if not hit:
                hit = self._query_by_hgvs(gene, variant)
            
            # Strategy 3: Direct search
            if not hit:
                params = {
                    "q": f"{gene} {variant}",
                    "fields": "clinvar,dbsnp,cadd,dbnsfp,cosmic",
                    "size": 5
                }
                response = requests.get(
                    f"{self.base_url}/query",
                    params=params,
                    timeout=self.timeout
                )
                if response.status_code == 200:
                    data = response.json()
                    hits = data.get("hits", [])
                    if hits:
                        hit = hits[0]
            
            if hit:
                annotation = self._process_hit(hit, annotation)
            else:
                annotation.error = f"Variant {gene}:{variant} not found in databases"
        
        except Exception as e:
            annotation.error = str(e)
        
        return annotation


async def annotate_variant_async(gene: str, variant: str) -> dict:
    """Async convenience function."""
    annotator = VariantAnnotator()
    result = await annotator.annotate_async(gene, variant)
    return _annotation_to_dict(result)

def annotate_variant(gene: str, variant: str) -> dict:
    """
    Convenience function to annotate a variant.
    
    Returns dict suitable for adding to evidence item.
    """
    annotator = VariantAnnotator()
    result = annotator.annotate(gene, variant)
    return _annotation_to_dict(result)

def _annotation_to_dict(result: VariantAnnotation) -> dict:
    return {
        "found": result.found,
        "clinvar_id": result.clinvar_id,
        "chromosome": result.chromosome,
        "start_position": result.start_position,
        "stop_position": result.stop_position,
        "reference_bases": result.reference_bases,
        "variant_bases": result.variant_bases,
        "reference_build": result.reference_build,
        "hgvs_c": result.hgvs_c,
        "hgvs_p": result.hgvs_p,
        "rsid": result.rsid,
        "cadd_score": result.cadd_score,
        "error": result.error
    }