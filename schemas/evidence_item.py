"""
Evidence Item Schema
====================

Pydantic model for CIViC evidence items with comprehensive field definitions.

This schema defines:
- 25 Tier 1 fields (extracted from paper text)
- 8 Reasoning fields (capture WHY decisions were made)

Field descriptions guide Claude's extraction by explaining:
- What the field means in CIViC context
- Where to find it in the paper
- Valid values and formats
- Common mistakes to avoid
"""

from pydantic import BaseModel, Field, field_validator, model_validator
from typing import Literal, Any, Optional, Dict


class FieldReasoning(BaseModel):
    """Reasoning for a specific field decision."""
    value: Any = Field(..., description="The extracted value")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Confidence in this value (0.0-1.0)")
    source_page: Optional[int] = Field(None, description="Page number where found")
    source_location: Optional[str] = Field(None, description="Location in paper (Table 2, Results paragraph 1)")
    verbatim_quote: Optional[str] = Field(None, description="Exact text from paper supporting this value")
    reasoning: str = Field(..., description="Why this value was chosen")


class ExtractionMetadata(BaseModel):
    """Overall metadata about the extraction decision."""
    overall_confidence: float = Field(..., ge=0.0, le=1.0, description="Overall confidence in this evidence item")
    primary_source_pages: str = Field(..., description="Main pages where evidence was found")
    extraction_reasoning: str = Field(..., description="Why this item was extracted")
    alternative_interpretations: Optional[str] = Field(None, description="Other ways this data could be interpreted")
    actionability_justification: str = Field(..., description="Why this is clinically actionable")


class EvidenceItem(BaseModel):
    """
    A single CIViC evidence item with all 25 Tier 1 fields + reasoning traces.
    
    CIViC evidence items capture clinically actionable findings that link:
    - A molecular alteration (gene + variant)
    - To a clinical outcome (treatment response, prognosis, diagnosis)
    - In a specific disease context
    - With supporting data from the literature
    """
    
    # =========================================================================
    # CORE EVIDENCE FIELDS (5 required)
    # =========================================================================
    
    evidence_description: str = Field(
        ...,
        min_length=50,
        description="""
        A 1-3 sentence summary of the clinical finding. MUST include:
        - The variant-disease-outcome relationship being claimed
        - Key statistics (HR, OR, p-value, response rate, median survival)
        - Patient numbers/cohort size when available
        """
    )
    
    evidence_level: Literal["A", "B", "C", "D", "E"] = Field(
        ...,
        description="""
        Strength of evidence based on STUDY DESIGN:
        A = Meta-analyses, FDA approvals, NCCN guidelines
        B = Clinical trials, large cohorts (>50 pts)
        C = Case reports, small series (<20 pts)
        D = Preclinical: cell lines, mouse models
        E = Computational predictions
        """
    )
    
    evidence_type: Literal[
        "PREDICTIVE", "DIAGNOSTIC", "PROGNOSTIC", 
        "PREDISPOSING", "ONCOGENIC", "FUNCTIONAL"
    ] = Field(
        ...,
        description="""
        The clinical question addressed:
        PREDICTIVE = Drug response (requires therapy_names)
        DIAGNOSTIC = Helps diagnose/classify cancer
        PROGNOSTIC = Predicts outcome independent of therapy
        PREDISPOSING = Germline variant increases cancer risk
        ONCOGENIC = Variant is a cancer driver
        FUNCTIONAL = Biochemical effect of variant
        """
    )
    
    evidence_direction: Literal["SUPPORTS", "DOES_NOT_SUPPORT"] = Field(
        ...,
        description="Does the study support or refute the clinical significance?"
    )
    
    evidence_significance: Literal[
        # PREDICTIVE
        "SENSITIVITY", "RESISTANCE", "ADVERSE_RESPONSE", "REDUCED_SENSITIVITY", 
        # PROGNOSTIC  
        "BETTER_OUTCOME", "POOR_OUTCOME",
        # DIAGNOSTIC
        "POSITIVE", "NEGATIVE",
        # PREDISPOSING
        "PREDISPOSITION", "PROTECTIVENESS",
        # ONCOGENIC
        "ONCOGENICITY",
        # FUNCTIONAL
        "GAIN_OF_FUNCTION", "LOSS_OF_FUNCTION", "UNALTERED_FUNCTION",
        "NEOMORPHIC", "DOMINANT_NEGATIVE",
        # Universal
        "NA"
    ] = Field(
        ...,
        description="Specific significance. Must match evidence_type."
    )
    
    # =========================================================================
    # VARIANT FIELDS (3 required + 4 optional)
    # =========================================================================
    
    feature_names: str = Field(
        ...,
        description="Gene symbol (HGNC). Examples: EGFR, BRAF, KRAS, TP53"
    )
    
    variant_names: str = Field(
        ...,
        description="Specific variant. Examples: V600E, L858R, EXON 19 DELETION, T790M"
    )
    
    variant_origin: Optional[Literal["SOMATIC", "GERMLINE", "RARE_GERMLINE", "NA", "COMBINED"]] = Field(
        None,
        description="SOMATIC (tumor), GERMLINE (inherited), or NA"
    )
    
    variant_type_names: Optional[str] = Field(
        None,
        description="Variant type: Missense Variant, Frameshift Truncation, Amplification, Fusion, etc."
    )
    
    variant_hgvs_descriptions: Optional[str] = Field(
        None,
        description="HGVS notation if provided: p.V600E, c.1799T>A"
    )
    variant_hgvs_c: Optional[str] = Field(
        None,
        description="Explicit HGVS c. notation (e.g., c.80G>C)"
    )
    variant_hgvs_p: Optional[str] = Field(
        None,
        description="Explicit HGVS p. notation (e.g., p.Arg27Pro)"
    )
    variant_coordinates: Optional[str] = Field(
        None,
        description="Genomic interval if stated (e.g., chr16:11965404 or chr12:13002001-13358000)"
    )
    
    molecular_profile_name: Optional[str] = Field(
        None,
        description="Format: '[GENE] [VARIANT]' e.g., 'BRAF V600E'"
    )
    
    fusion_five_prime_gene_names: Optional[str] = Field(
        None,
        description="5' partner gene in fusions (e.g., BCR in BCR-ABL1)"
    )
    
    fusion_three_prime_gene_names: Optional[str] = Field(
        None,
        description="3' partner gene in fusions (e.g., ABL1 in BCR-ABL1)"
    )
    
    # =========================================================================
    # FEATURE FIELDS (gene details)
    # =========================================================================
    
    feature_full_names: Optional[str] = Field(
        None,
        description="Full gene name if mentioned in paper"
    )
    
    feature_types: Optional[Literal["GENE", "FACTOR"]] = Field(
        "GENE",
        description="Almost always GENE. FACTOR for MSI-H, TMB, PD-L1 expression."
    )
    
    # =========================================================================
    # DISEASE FIELDS
    # =========================================================================
    
    disease_name: str = Field(
        ...,
        description="Full CIViC disease name: 'Non-Small Cell Lung Carcinoma', 'Melanoma'"
    )
    
    disease_display_name: Optional[str] = Field(
        None,
        description="Short form: 'NSCLC', 'CRC', 'AML'"
    )
    
    # =========================================================================
    # THERAPY FIELDS
    # =========================================================================
    
    therapy_names: Optional[str] = Field(
        None,
        description="""
        REQUIRED for PREDICTIVE evidence.
        Specific drug names only: 'Erlotinib', 'Dabrafenib,Trametinib'
        NEVER use: TKI, EGFR inhibitor, chemotherapy, targeted therapy
        """
    )
    
    therapy_interaction_type: Optional[Literal["COMBINATION", "SEQUENTIAL", "SUBSTITUTES"]] = Field(
        None,
        description="For multiple drugs: COMBINATION, SEQUENTIAL, or SUBSTITUTES"
    )
    
    # =========================================================================
    # SOURCE FIELDS
    # =========================================================================
    
    source_title: Optional[str] = Field(
        None,
        description="Full paper title from first page"
    )
    
    source_publication_year: Optional[str] = Field(
        None,
        description="4-digit year: '2015', '2023'"
    )
    
    source_journal: Optional[str] = Field(
        None,
        description="Full journal name: 'Journal of Clinical Oncology'"
    )
    
    # =========================================================================
    # CLINICAL TRIAL FIELDS
    # =========================================================================
    
    clinical_trial_nct_ids: Optional[str] = Field(
        None,
        description="NCT number: 'NCT01234567'"
    )
    
    clinical_trial_names: Optional[str] = Field(
        None,
        description="Trial acronym: 'BRIM-3', 'KEYNOTE-024'"
    )

    # =========================================================================
    # STUDY/COHORT FIELDS
    # =========================================================================

    cohort_size: Optional[int] = Field(
        None,
        description="Number of patients in the cohort relevant to the evidence item"
    )

    cancer_cell_fraction: Optional[float] = Field(
        None,
        description="Cancer cell fraction (0-1) if reported (e.g., 0.35)"
    )
    
    # =========================================================================
    # PHENOTYPE FIELD
    # =========================================================================
    
    phenotype_names: Optional[str] = Field(
        None,
        description="Relevant phenotypes: 'High tumor mutation burden', 'Prior platinum exposure'"
    )
    
    # =========================================================================
    # REASONING FIELDS (NEW - for traceability)
    # =========================================================================
    
    source_page_numbers: Optional[str] = Field(
        None,
        description="Pages where evidence was found. Format: '2, 3' or '3-5'"
    )
    
    source_section: Optional[str] = Field(
        None,
        description="Section of paper: 'Abstract', 'Results', 'Table 2', 'Figure 3'"
    )
    
    verbatim_quote: Optional[str] = Field(
        None,
        description="EXACT text from paper supporting this evidence item. Copy-paste the sentence(s)."
    )
    
    verbatim_statistics: Optional[str] = Field(
        None,
        description="Exact statistical values from paper: 'ORR 61%, HR 0.34 (95% CI 0.24-0.49), p<0.001'"
    )
    
    extraction_confidence: Optional[float] = Field(
        None,
        ge=0.0,
        le=1.0,
        description="Confidence score 0.0-1.0. Higher = more certain."
    )
    
    extraction_reasoning: Optional[str] = Field(
        None,
        description="Why this item was extracted. Justify actionability and evidence type choice."
    )
    
    field_reasoning: Optional[Dict[str, FieldReasoning]] = Field(
        None,
        description="Per-field reasoning for key decisions (evidence_type, evidence_significance, etc.)"
    )
    
    extraction_metadata: Optional[ExtractionMetadata] = Field(
        None,
        description="Overall extraction metadata and justification"
    )

    # =========================================================================
    # TIER 2 FIELDS (NORMALIZATION - Optional, populated by Normalizer)
    # =========================================================================
    
    # Identifiers (Support both singular/plural/alias conventions)
    gene_entrez_ids: Optional[Any] = Field(None, description="NCBI Entrez Gene ID (Legacy)")
    gene_entrez_id: Optional[Any] = Field(None, description="NCBI Entrez Gene ID")
    
    disease_doid: Optional[str] = Field(None, description="Disease Ontology ID")
    disease_efo_id: Optional[str] = Field(None, description="EFO ID")
    
    therapy_ncit_ids: Optional[str] = Field(None, description="NCI Thesaurus ID (Legacy)")
    therapy_ncit_id: Optional[str] = Field(None, description="NCI Thesaurus ID")
    
    therapy_rxnorm_ids: Optional[str] = Field(None, description="RxNorm CUI (Legacy)")
    therapy_rxcui: Optional[str] = Field(None, description="RxNorm CUI")
    
    factor_ncit_ids: Optional[str] = Field(None, description="NCIt ID for factors")
    factor_ncit_id: Optional[str] = Field(None, description="NCIt ID for factors")
    
    variant_type_soids: Optional[str] = Field(None, description="Sequence Ontology ID")
    variant_type_soid: Optional[str] = Field(None, description="Sequence Ontology ID")
    
    # Variant External IDs
    variant_clinvar_ids: Optional[Any] = Field(None, description="ClinVar ID")
    variant_clinvar_id: Optional[Any] = Field(None, description="ClinVar ID")
    
    variant_allele_registry_ids: Optional[Any] = Field(None, description="ClinGen Allele Registry ID")
    variant_allele_registry_id: Optional[Any] = Field(None, description="ClinGen Allele Registry ID")
    
    variant_mane_select_transcripts: Optional[Any] = Field(None, description="MANE Transcript")
    
    # Phenotypes
    phenotype_ids: Optional[Any] = Field(None, description="Phenotype ID")
    phenotype_hpo_ids: Optional[Any] = Field(None, description="HPO ID")
    hpo_id: Optional[Any] = Field(None, description="HPO ID")
    
    # Source
    source_citation_id: Optional[str] = Field(None, description="PMID")
    source_pmid: Optional[str] = Field(None, description="PMID")
    source_pmcid: Optional[str] = Field(None, description="PMCID")
    
    # Genomic Coordinates
    chromosome: Optional[str] = Field(None, description="Chromosome (e.g. '7', 'X')")
    start_position: Optional[Any] = Field(None, description="Start position")
    stop_position: Optional[Any] = Field(None, description="Stop position")
    reference_build: Optional[str] = Field(None, description="Genome build (GRCh37/38)")
    representative_transcript: Optional[str] = Field(None, description="Transcript ID")
    reference_bases: Optional[str] = Field(None, description="Ref bases")
    variant_bases: Optional[str] = Field(None, description="Alt bases")
    coordinate_type: Optional[str] = Field(None, description="Coordinate type")
    
    # Safety
    drug_safety_profile: Optional[Any] = Field(None, description="FAERS Safety Data")
    therapy_safety_profile: Optional[Any] = Field(None, description="FAERS Safety Data")

    # =========================================================================
    # VALIDATORS
    # =========================================================================
    
    @model_validator(mode='after')
    def validate_predictive_has_therapy(self) -> 'EvidenceItem':
        """PREDICTIVE evidence MUST have therapy_names."""
        if self.evidence_type == "PREDICTIVE" and not self.therapy_names:
            raise ValueError("PREDICTIVE evidence requires therapy_names field")
        return self
    
    @model_validator(mode='after')
    def validate_significance_matches_type(self) -> 'EvidenceItem':
        """Validate evidence_significance is valid for evidence_type."""
        valid_combinations = {
            "PREDICTIVE": {"SENSITIVITY", "RESISTANCE", "ADVERSE_RESPONSE", "REDUCED_SENSITIVITY", "NA"},
            "PROGNOSTIC": {"BETTER_OUTCOME", "POOR_OUTCOME", "NA"},
            "DIAGNOSTIC": {"POSITIVE", "NEGATIVE", "NA"},
            "PREDISPOSING": {"PREDISPOSITION", "PROTECTIVENESS", "NA"},
            "ONCOGENIC": {"ONCOGENICITY", "NA"},
            "FUNCTIONAL": {"GAIN_OF_FUNCTION", "LOSS_OF_FUNCTION", "UNALTERED_FUNCTION", 
                          "NEOMORPHIC", "DOMINANT_NEGATIVE", "NA"}
        }
        
        valid_sigs = valid_combinations.get(self.evidence_type, set())
        if self.evidence_significance not in valid_sigs:
            raise ValueError(
                f"evidence_significance '{self.evidence_significance}' not valid for "
                f"evidence_type '{self.evidence_type}'. Valid options: {valid_sigs}"
            )
        return self
    
    # =========================================================================
    # HELPER METHODS
    # =========================================================================
    
    def get_reasoning_coverage(self) -> float:
        """Calculate what percentage of reasoning fields are populated."""
        reasoning_fields = [
            self.source_page_numbers,
            self.source_section,
            self.verbatim_quote,
            self.extraction_confidence,
            self.extraction_reasoning
        ]
        populated = sum(1 for f in reasoning_fields if f is not None)
        return populated / len(reasoning_fields)
    
    def has_full_reasoning(self) -> bool:
        """Check if item has complete reasoning traces."""
        return (
            self.source_page_numbers is not None and
            self.verbatim_quote is not None and
            self.extraction_confidence is not None and
            self.extraction_reasoning is not None
        )
    
    def to_dict(self) -> dict:
        """Convert to dictionary, excluding None values."""
        return {k: v for k, v in self.model_dump().items() if v is not None}