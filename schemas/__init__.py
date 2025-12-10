"""
Schemas Module
==============

Field definitions, validation constants, and Pydantic models.
"""

from .field_definitions import (
    # Valid values
    VALID_EVIDENCE_TYPES,
    VALID_EVIDENCE_LEVELS,
    VALID_EVIDENCE_DIRECTIONS,
    VALID_VARIANT_ORIGINS,
    VALID_FEATURE_TYPES,
    VALID_THERAPY_INTERACTION_TYPES,
    EVIDENCE_SIGNIFICANCE_MAP,
    
    # Field lists
    CORE_EVIDENCE_FIELDS,
    VARIANT_FIELDS,
    FEATURE_FIELDS,
    DISEASE_FIELDS,
    THERAPY_FIELDS,
    SOURCE_FIELDS,
    CLINICAL_TRIAL_FIELDS,
    PHENOTYPE_FIELDS,
    TIER_1_FIELDS,
    TIER_2_FIELDS,
    REQUIRED_FIELDS,
)

from .evidence_item import EvidenceItem
from .extraction_result import ExtractionResult, ExtractionPlan, Critique, RejectedItem

__all__ = [
    # Valid values
    "VALID_EVIDENCE_TYPES",
    "VALID_EVIDENCE_LEVELS",
    "VALID_EVIDENCE_DIRECTIONS",
    "VALID_VARIANT_ORIGINS",
    "VALID_FEATURE_TYPES",
    "VALID_THERAPY_INTERACTION_TYPES",
    "EVIDENCE_SIGNIFICANCE_MAP",
    
    # Field lists
    "CORE_EVIDENCE_FIELDS",
    "VARIANT_FIELDS",
    "FEATURE_FIELDS",
    "DISEASE_FIELDS",
    "THERAPY_FIELDS",
    "SOURCE_FIELDS",
    "CLINICAL_TRIAL_FIELDS",
    "PHENOTYPE_FIELDS",
    "TIER_1_FIELDS",
    "TIER_2_FIELDS",
    "REQUIRED_FIELDS",
    
    # Pydantic models
    "EvidenceItem",
    "ExtractionResult",
    "ExtractionPlan",
    "Critique",
    "RejectedItem",
]