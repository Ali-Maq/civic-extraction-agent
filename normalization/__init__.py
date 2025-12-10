"""
Normalization Module
====================

External API clients for Tier 2 field lookups.
"""

from .normalizer import EvidenceNormalizer
from .variant_annotator import VariantAnnotator, annotate_variant

__all__ = [
    "EvidenceNormalizer",
    "VariantAnnotator",
    "annotate_variant",
]