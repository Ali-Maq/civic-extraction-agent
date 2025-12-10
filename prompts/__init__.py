"""
Prompts Module
==============

Reusable prompt components for evidence extraction.
"""

from .system_prompt import SYSTEM_PROMPT_BASE, THINKING_INSTRUCTIONS
from .evidence_core import EVIDENCE_CORE_PROMPT, EVIDENCE_TYPES_GUIDE
from .molecular_profile import MOLECULAR_PROFILE_PROMPT, VARIANT_TYPES_GUIDE
from .clinical_context import CLINICAL_CONTEXT_PROMPT, DISEASE_THERAPY_GUIDE

__all__ = [
    "SYSTEM_PROMPT_BASE",
    "THINKING_INSTRUCTIONS",
    "EVIDENCE_CORE_PROMPT",
    "EVIDENCE_TYPES_GUIDE",
    "MOLECULAR_PROFILE_PROMPT",
    "VARIANT_TYPES_GUIDE",
    "CLINICAL_CONTEXT_PROMPT",
    "DISEASE_THERAPY_GUIDE",
]