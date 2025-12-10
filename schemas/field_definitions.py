"""
Field Definitions
=================

Canonical field names and validation constants.
This is the SINGLE SOURCE OF TRUTH for all field definitions.

Total fields: 45
- Tier 1 (LLM-extractable): 25 fields
- Tier 2 (database lookups): 20 fields
- Required (minimum): 8 fields
"""

# =============================================================================
# VALID VALUES (Controlled Vocabularies)
# =============================================================================

VALID_EVIDENCE_TYPES = [
    "PREDICTIVE",
    "DIAGNOSTIC",
    "PROGNOSTIC",
    "PREDISPOSING",
    "ONCOGENIC",
    "FUNCTIONAL",
]

VALID_EVIDENCE_LEVELS = ["A", "B", "C", "D", "E"]

VALID_EVIDENCE_DIRECTIONS = ["SUPPORTS", "DOES_NOT_SUPPORT"]

VALID_VARIANT_ORIGINS = [
    "SOMATIC",
    "GERMLINE",
    "RARE_GERMLINE",
    "NA",
    "COMBINED",
]

VALID_FEATURE_TYPES = ["GENE", "FACTOR"]

VALID_THERAPY_INTERACTION_TYPES = [
    "COMBINATION",
    "SEQUENTIAL",
    "SUBSTITUTES",
    None,  # Single therapy (no interaction)
]

# Evidence significance must match evidence type
EVIDENCE_SIGNIFICANCE_MAP = {
    "PREDICTIVE": [
        "SENSITIVITY",
        "RESISTANCE",
        "ADVERSE_RESPONSE",
        "REDUCED_SENSITIVITY",
        "NA",
    ],
    "DIAGNOSTIC": [
        "POSITIVE",
        "NEGATIVE",
        "NA",
    ],
    "PROGNOSTIC": [
        "BETTER_OUTCOME",
        "POOR_OUTCOME",
        "NA",
    ],
    "PREDISPOSING": [
        "PREDISPOSITION",
        "PROTECTIVENESS",
        "NA",
    ],
    "ONCOGENIC": [
        "ONCOGENICITY",
        "NA",
    ],
    "FUNCTIONAL": [
        "GAIN_OF_FUNCTION",
        "LOSS_OF_FUNCTION",
        "UNALTERED_FUNCTION",
        "NEOMORPHIC",
        "DOMINANT_NEGATIVE",
        "NA",
    ],
}

# =============================================================================
# TIER 1 FIELDS (25 fields)
# LLM-extractable from paper text/images
# =============================================================================

CORE_EVIDENCE_FIELDS = [
    "evidence_description",  # 1-3 sentence summary of finding
    "evidence_level",        # A, B, C, D, E
    "evidence_type",         # PREDICTIVE, DIAGNOSTIC, etc.
    "evidence_direction",    # SUPPORTS, DOES_NOT_SUPPORT
    "evidence_significance", # Type-specific significance
]

VARIANT_FIELDS = [
    "variant_names",                 # Specific variant (V600E, L858R)
    "variant_origin",                # SOMATIC, GERMLINE, etc.
    "variant_type_names",            # Missense, Fusion, etc.
    "variant_hgvs_descriptions",     # p.V600E, c.1799T>A
    "molecular_profile_name",        # "[GENE] [VARIANT]"
    "fusion_five_prime_gene_names",  # 5' fusion partner
    "fusion_three_prime_gene_names", # 3' fusion partner
]

FEATURE_FIELDS = [
    "feature_names",      # Gene symbol (EGFR, BRAF)
    "feature_full_names", # Full gene name
    "feature_types",      # GENE or FACTOR
]

DISEASE_FIELDS = [
    "disease_name",         # Disease name
    "disease_display_name", # Display version
]

THERAPY_FIELDS = [
    "therapy_names",           # Drug name(s)
    "therapy_interaction_type", # COMBINATION, SEQUENTIAL, etc.
]

SOURCE_FIELDS = [
    "source_title",            # Paper title
    "source_publication_year", # Year
    "source_journal",          # Journal name
]

CLINICAL_TRIAL_FIELDS = [
    "clinical_trial_nct_ids", # NCT numbers
    "clinical_trial_names",   # Trial names/acronyms
]

PHENOTYPE_FIELDS = [
    "phenotype_names",  # Phenotype descriptions
]

# Combined Tier 1 (25 fields)
TIER_1_FIELDS = (
    CORE_EVIDENCE_FIELDS +      # 5
    VARIANT_FIELDS +            # 7
    FEATURE_FIELDS +            # 3
    DISEASE_FIELDS +            # 2
    THERAPY_FIELDS +            # 2
    SOURCE_FIELDS +             # 3
    CLINICAL_TRIAL_FIELDS +     # 2
    PHENOTYPE_FIELDS            # 1
)

# =============================================================================
# TIER 2 FIELDS (20 fields)
# Require database lookups (normalization)
# =============================================================================

TIER_2_FIELDS = [
    # Ontology IDs
    "disease_doid",              # Disease Ontology ID
    "gene_entrez_ids",           # NCBI Gene ID
    "therapy_ncit_ids",          # NCI Thesaurus ID
    "factor_ncit_ids",           # NCIt ID for factors
    "variant_type_soids",        # Sequence Ontology ID
    
    # Variant identifiers
    "variant_clinvar_ids",       # ClinVar accession
    "variant_allele_registry_ids", # ClinGen Allele Registry
    "variant_mane_select_transcripts", # MANE Select transcript
    
    # Phenotype IDs
    "phenotype_ids",             # General phenotype ID
    "phenotype_hpo_ids",         # HPO ID
    
    # Source IDs
    "source_citation_id",        # PMID
    "source_pmcid",              # PMC ID
    
    # Genomic coordinates
    "chromosome",                # Chromosome number
    "start_position",            # Start coordinate
    "stop_position",             # End coordinate
    "reference_build",           # GRCh37, GRCh38
    "representative_transcript", # RefSeq transcript
    "reference_bases",           # Reference allele
    "variant_bases",             # Alternate allele
    "coordinate_type",           # genomic, cDNA, etc.
]

# =============================================================================
# REQUIRED FIELDS (8 fields)
# Minimum for a valid evidence item
# =============================================================================

REQUIRED_FIELDS = [
    "feature_names",        # Must have a gene
    "variant_names",        # Must have a variant
    "disease_name",         # Must have a disease
    "evidence_type",        # Must specify type
    "evidence_level",       # Must specify level
    "evidence_direction",   # Must specify direction
    "evidence_significance", # Must specify significance
    "evidence_description", # Must have description
]

# =============================================================================
# FIELD ALIASES (for backwards compatibility)
# Map old field names to new canonical names
# =============================================================================

FIELD_ALIASES = {
    # Old name -> New name
    "gene_name": "feature_names",
    "gene": "feature_names",
    "variant_name": "variant_names",
    "variant": "variant_names",
    "clinical_significance": "evidence_significance",
    "evidence_statement": "evidence_description",
    "description": "evidence_description",
    "drug": "therapy_names",
    "drug_name": "therapy_names",
    "drugs": "therapy_names",
    "therapy": "therapy_names",
    "disease": "disease_name",
}


def normalize_field_name(field_name: str) -> str:
    """
    Normalize a field name to its canonical form.
    
    Args:
        field_name: Field name (possibly an alias)
        
    Returns:
        Canonical field name
    """
    return FIELD_ALIASES.get(field_name, field_name)


def normalize_item_fields(item: dict) -> dict:
    """
    Normalize all field names in an evidence item.
    
    Args:
        item: Evidence item with possibly aliased field names
        
    Returns:
        Item with canonical field names
    """
    normalized = {}
    for key, value in item.items():
        canonical_key = normalize_field_name(key)
        normalized[canonical_key] = value
    return normalized

