"""
Extraction State
================

Manages the shared state across all agents in the extraction pipeline.

NEW ARCHITECTURE (Reader-First):
    Reader → Planner → Extractor → Critic → Normalization
    
The Reader extracts paper content ONCE, then all downstream agents
use the same text-based context (no more redundant image reading).
"""

from dataclasses import dataclass, field
from typing import Optional, Any
from datetime import datetime
import json


@dataclass
class PaperInfo:
    """Basic paper metadata (from folder structure)."""
    paper_id: str
    author: str
    year: str
    num_pages: int
    paper_type: str = ""
    pdf_path: Optional[str] = None
    paper_folder: Optional[str] = None
    page_images: list[str] = field(default_factory=list)
    expected_item_count: int = 0


@dataclass
class ExtractionPlan:
    """Plan created by the Planner agent."""
    paper_type: str
    expected_items: int
    key_variants: list[str]
    key_therapies: list[str]
    key_diseases: list[str]
    focus_sections: list[str]
    extraction_notes: str


@dataclass
class CritiqueResult:
    """Feedback from the Critic agent."""
    overall_assessment: str  # "APPROVE", "NEEDS_REVISION", "REJECT"
    item_feedback: list[dict]
    missing_items: str
    extra_items: str
    summary: str
    iteration: int


@dataclass
class ExtractionState:
    """
    Central state object shared across all agents.
    
    NEW: Now includes paper_content from the Reader agent.
    This eliminates redundant page reading by downstream agents.
    """
    # Paper info
    paper_info: Optional[PaperInfo] = None
    
    # NEW: Paper content extracted by Reader agent (SINGLE SOURCE OF TRUTH)
    paper_content: Optional[Any] = None  # PaperContent object
    paper_context_text: str = ""  # Text version for agent prompts
    
    # Extraction plan from Planner
    extraction_plan: Optional[ExtractionPlan] = None
    
    # Current evidence items (Draft)
    draft_extractions: list[dict] = field(default_factory=list)
    
    # Final evidence items (Post-normalization)
    final_extractions: list[dict] = field(default_factory=list)
    
    # Latest critique
    critique: Optional[dict] = None
    
    # Iteration tracking
    iteration_count: int = 0
    max_iterations: int = 3
    
    # Status
    is_complete: bool = False
    final_status: str = ""  # "APPROVED", "MAX_ITERATIONS", "ERROR"
    
    # Timing
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    
    def reset(self) -> None:
        """Reset state for a new paper."""
        # Note: paper_info is not reset here as it is set by CIViCContext.load_paper
        self.paper_content = None
        self.paper_context_text = ""
        self.extraction_plan = None
        self.draft_extractions = []
        self.final_extractions = []
        self.critique = None
        self.iteration_count = 0
        self.is_complete = False
        self.final_status = ""
        self.start_time = None
        self.end_time = None

    def set_paper_content(self, paper_content) -> None:
        """
        Set the paper content from the Reader agent.
        This generates the text context used by all downstream agents.
        """
        self.paper_content = paper_content
        # Handle dict vs object
        if isinstance(paper_content, dict):
            # We need a helper to generate text from dict if it's not the object
            # But paper_content_tools saves it as dict.
            # And paper_content_tools already sets ctx.paper_content_text!
            # So this method might be redundant if tools do it directly.
            pass
        else:
            self.paper_context_text = paper_content.to_context_document()

        # Also update paper_info with extracted metadata
        if self.paper_info and hasattr(paper_content, "paper_type"):
            self.paper_info.paper_type = paper_content.paper_type

    def get_context_for_agents(self) -> str:
        """
        Get the text context to pass to Planner/Extractor/Critic.
        
        This replaces image-based page reading with text-based context.
        All agents work from the SAME extracted content.
        """
        if not self.paper_context_text:
            raise ValueError("Paper content not yet extracted. Run Reader agent first.")
        return self.paper_context_text
    
    def get_latest_critique(self) -> Optional[dict]:
        """Get the most recent critique, if any."""
        return self.critique
    
    def increment_iteration(self) -> int:
        """Increment iteration counter and return new value."""
        self.iteration_count += 1
        return self.iteration_count
    
    def should_continue(self) -> bool:
        """Check if we should continue iterating."""
        if self.is_complete:
            return False
        if self.iteration_count >= self.max_iterations:
            return False
        latest = self.critique
        if latest and latest.get("overall_assessment") == "APPROVE":
            return False
        return True
    
    def to_summary(self) -> dict:
        """Generate summary for logging/output."""
        info = self.paper_info

        def _get_info(field: str, default: Any):
            if isinstance(info, dict):
                return info.get(field, default)
            if info is not None:
                return getattr(info, field, default)
            return default

        return {
            "paper_id": _get_info("paper_id", "Unknown"),
            "paper_info": {
                "author": _get_info("author", "Unknown"),
                "year": _get_info("year", "Unknown"),
                "num_pages": _get_info("num_pages", 0),
                "paper_type": _get_info("paper_type", ""),
            },
            "extraction": {
                "items": len(self.final_extractions) if self.is_complete else len(self.draft_extractions),
                "iterations": self.iteration_count,
                "complete": self.is_complete,
                "evidence_items": self.final_extractions if self.is_complete else self.draft_extractions
            },
            "plan": {
                "paper_type": self.extraction_plan.paper_type if self.extraction_plan else "",
                "expected_items": self.extraction_plan.expected_items if self.extraction_plan else 0,
                "key_variants": self.extraction_plan.key_variants if self.extraction_plan else [],
                "key_therapies": self.extraction_plan.key_therapies if self.extraction_plan else [],
                "key_diseases": self.extraction_plan.key_diseases if self.extraction_plan else [],
                "focus_sections": self.extraction_plan.focus_sections if self.extraction_plan else [],
                "extraction_notes": self.extraction_plan.extraction_notes if self.extraction_plan else ""
            },
            "final_critique": self.critique,
            "timing": {
                "start": self.start_time.isoformat() if self.start_time else None,
                "end": self.end_time.isoformat() if self.end_time else None,
                "seconds": (self.end_time - self.start_time).total_seconds() if self.start_time and self.end_time else 0
            }
        }
