"""
Extraction Result Schema
========================

Pydantic model for complete extraction results.
"""

from pydantic import BaseModel, Field
from typing import Literal
from .evidence_item import EvidenceItem


class RejectedItem(BaseModel):
    """An evidence item that was considered but rejected."""
    
    reason: str = Field(..., description="Why this item was rejected")
    description: str = Field(..., description="Brief description of what was rejected")
    source_quote: str | None = Field(None, description="Quote from paper if available")


class ExtractionPlan(BaseModel):
    """The extraction plan created by the Planner agent."""
    
    paper_type: Literal["REVIEW", "PRIMARY", "CASE_REPORT", "GUIDELINE"]
    expected_items: int
    key_variants: list[str] = Field(default_factory=list)
    key_therapies: list[str] = Field(default_factory=list)
    key_diseases: list[str] = Field(default_factory=list)
    focus_sections: list[str] = Field(default_factory=list)
    extraction_notes: str = ""


class Critique(BaseModel):
    """Critique from the Critic agent."""
    
    overall_assessment: Literal["APPROVE", "NEEDS_REVISION", "REJECT"]
    item_feedback: list[dict] = Field(default_factory=list)
    missing_items: list[str] = Field(default_factory=list)
    extra_items: list[int] = Field(default_factory=list)
    summary: str = ""
    iteration: int = 0


class ExtractionResult(BaseModel):
    """Complete result of evidence extraction from a paper."""
    
    # Paper info
    paper_id: str
    paper_author: str
    paper_year: str
    paper_type: str | None = None
    num_pages: int
    
    # Extraction plan
    extraction_plan: ExtractionPlan | None = None
    
    # Results
    evidence_items: list[EvidenceItem] = Field(default_factory=list)
    rejected_items: list[RejectedItem] = Field(default_factory=list)
    
    # Process info
    iterations_used: int = 0
    final_critique: Critique | None = None
    
    # Confidence
    extraction_confidence: Literal["HIGH", "MEDIUM", "LOW"] = "MEDIUM"
    
    # Timing
    duration_seconds: float = 0.0
    
    def to_civic_format(self) -> list[dict]:
        """Convert to CIViC database format."""
        return [item.model_dump(exclude_none=True) for item in self.evidence_items]