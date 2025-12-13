"""
CIViC Context
=============

Main context object managing paper data.

NOTE: Ground truth is NOT available in this context.
Ground truth is only used in the separate evaluation script.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional

from .state import PaperInfo, ExtractionState
from config import PAPERS_DIR


@dataclass
class CIViCContext:
    """
    Central context for CIViC evidence extraction.
    
    Manages:
    - Current paper being processed (PDF)
    - Extraction state
    - Session statistics
    
    NOTE: NO ground truth access - extraction must be independent.
    """
    
    # Current paper
    paper: Optional[PaperInfo] = None
    
    # Papers directory
    papers_dir: Path = field(default_factory=lambda: PAPERS_DIR)
    
    # Extraction state
    state: ExtractionState = field(default_factory=ExtractionState)

    # Reader-extracted content (set at runtime by tools)
    paper_content: Optional[dict] = None
    paper_content_text: str = ""
    
    # Session stats
    papers_processed: int = 0
    total_items_extracted: int = 0
    
    def load_paper(self, paper_id: str) -> None:
        """
        Load a paper by its folder name.
        
        Looks for:
        1. PDF file: {paper_id}.pdf
        2. Fallback: visualizations/page*_annotated.jpg or page*.jpg
        """
        paper_folder = self.papers_dir / paper_id
        
        if not paper_folder.exists():
            raise ValueError(f"Paper folder not found: {paper_folder}")
        
        # Look for PDF first (preferred)
        pdf_file = paper_folder / f"{paper_id}.pdf"
        if not pdf_file.exists():
            # Try any PDF in folder
            pdf_files = list(paper_folder.glob("*.pdf"))
            pdf_file = pdf_files[0] if pdf_files else None
        
        # Fallback to page images if no PDF
        page_images = []
        if pdf_file is None or not pdf_file.exists():
            viz_folder = paper_folder / "visualizations"
            if viz_folder.exists():
                # Try annotated images first
                page_images = sorted(viz_folder.glob("page*_annotated.jpg"))
                if not page_images:
                    # Try regular page images
                    page_images = sorted(viz_folder.glob("page*.jpg"))
            
            if not page_images:
                # Try root folder
                page_images = sorted(paper_folder.glob("page*.jpg"))
            
            if not page_images and pdf_file is None:
                raise ValueError(f"No PDF or page images found in {paper_folder}")
        
        # Parse paper ID for metadata
        parts = paper_id.split("_")
        author = parts[1] if len(parts) > 1 else "Unknown"
        year = parts[2] if len(parts) > 2 else "Unknown"
        
        # Determine number of pages
        if pdf_file and pdf_file.exists():
            try:
                import fitz  # PyMuPDF
                doc = fitz.open(pdf_file)
                num_pages = len(doc)
                doc.close()
            except ImportError:
                # If PyMuPDF not available, estimate from images
                num_pages = len(page_images) if page_images else 10
        else:
            num_pages = len(page_images)
        
        self.paper = PaperInfo(
            paper_id=paper_id,
            paper_folder=paper_folder,
            author=author,
            year=year,
            num_pages=num_pages,
            page_images=page_images,
            pdf_path=pdf_file if pdf_file and pdf_file.exists() else None
        )

        # Reset state for new paper
        self.state.reset()
        # Keep state paper_info in sync with the loaded paper metadata
        self.state.paper_info = self.paper
    
    def get_page_image_path(self, page_num: int) -> Optional[Path]:
        """Get the path to a specific page image."""
        if not self.paper:
            return None
        
        if self.paper.page_images and page_num <= len(self.paper.page_images):
            return self.paper.page_images[page_num - 1]
        
        return None


# Global context management
_current_context: Optional[CIViCContext] = None


def set_current_context(ctx: CIViCContext) -> None:
    """Set the current context for tool access."""
    global _current_context
    _current_context = ctx


def require_context() -> CIViCContext:
    """Get current context, raising if not set."""
    if _current_context is None:
        raise RuntimeError("No CIViC context set. Call set_current_context first.")
    return _current_context


def get_current_context() -> Optional[CIViCContext]:
    """Get current context, or None if not set."""
    return _current_context

