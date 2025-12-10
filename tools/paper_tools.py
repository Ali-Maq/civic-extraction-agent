"""
Paper Reading Tools
===================

Tools for reading paper pages - supports both PDF and image files.
"""

import base64
import json
import io
from claude_agent_sdk import tool
from typing import Any

from context import require_context


def render_pdf_page_to_image(pdf_path, page_num: int, dpi: int = 150) -> bytes:
    """
    Render a PDF page to a JPEG image.
    
    Args:
        pdf_path: Path to PDF file
        page_num: 1-indexed page number
        dpi: Resolution for rendering (default 150 for good quality/size balance)
    
    Returns:
        JPEG image bytes
    """
    try:
        import fitz  # PyMuPDF
        
        doc = fitz.open(pdf_path)
        if page_num < 1 or page_num > len(doc):
            doc.close()
            raise ValueError(f"Page {page_num} out of range (1-{len(doc)})")
        
        page = doc[page_num - 1]  # 0-indexed in PyMuPDF
        
        # Render at specified DPI
        zoom = dpi / 72  # 72 is default PDF DPI
        mat = fitz.Matrix(zoom, zoom)
        pix = page.get_pixmap(matrix=mat)
        
        # Convert to JPEG
        img_bytes = pix.tobytes("jpeg")
        
        doc.close()
        return img_bytes
        
    except ImportError:
        raise ImportError(
            "PyMuPDF (fitz) is required for PDF reading. "
            "Install with: pip install PyMuPDF"
        )


@tool(
    "read_paper_page",
    "Read a specific page from the paper. Returns page image for visual analysis.",
    {"page_num": int, "include_image": bool}
)
async def read_paper_page(args: dict[str, Any]) -> dict[str, Any]:
    """
    Read a page from the current paper.
    
    Supports:
    - PDF files (preferred, renders page to image)
    - Pre-rendered page images (fallback)
    """
    ctx = require_context()
    
    if ctx.paper is None:
        return {
            "content": [{"type": "text", "text": "Error: No paper loaded"}],
            "is_error": True
        }
    
    page_num = args["page_num"]
    include_image = args.get("include_image", True)
    
    if page_num < 1 or page_num > ctx.paper.num_pages:
        return {
            "content": [{"type": "text", "text": f"Error: Invalid page {page_num}. Paper has {ctx.paper.num_pages} pages."}],
            "is_error": True
        }
    
    content = []
    
    # Add text info
    content.append({
        "type": "text",
        "text": f"Page {page_num} of {ctx.paper.num_pages} | Paper: {ctx.paper.paper_id}"
    })
    
    # Get image if requested
    if include_image:
        image_bytes = None
        
        # Try PDF first (preferred)
        if ctx.paper.pdf_path and ctx.paper.pdf_path.exists():
            try:
                image_bytes = render_pdf_page_to_image(ctx.paper.pdf_path, page_num)
            except Exception as e:
                content.append({
                    "type": "text",
                    "text": f"Warning: Could not render PDF page: {e}. Trying fallback..."
                })
        
        # Fallback to pre-rendered images
        if image_bytes is None and ctx.paper.page_images:
            if page_num <= len(ctx.paper.page_images):
                page_image = ctx.paper.page_images[page_num - 1]
                if page_image.exists():
                    with open(page_image, "rb") as f:
                        image_bytes = f.read()
        
        # Add image to content
        if image_bytes:
            b64_image = base64.b64encode(image_bytes).decode("utf-8")
            content.append({
                "type": "image",
                "source": {
                    "type": "base64",
                    "media_type": "image/jpeg",
                    "data": b64_image
                }
            })
        else:
            content.append({
                "type": "text",
                "text": f"Warning: Could not load image for page {page_num}"
            })
    
    return {"content": content}


@tool(
    "get_paper_info",
    "Get metadata about the current paper being processed.",
    {}
)
async def get_paper_info(args: dict[str, Any]) -> dict[str, Any]:
    """Get paper metadata."""
    ctx = require_context()
    
    if ctx.paper is None:
        return {
            "content": [{"type": "text", "text": "Error: No paper loaded"}],
            "is_error": True
        }
    
    info = {
        "paper_id": ctx.paper.paper_id,
        "author": ctx.paper.author,
        "year": ctx.paper.year,
        "num_pages": ctx.paper.num_pages,
        "paper_type": ctx.paper.paper_type or "Not yet determined",
        "expected_items": ctx.paper.expected_item_count,
        "current_iteration": ctx.state.iteration_count,
        "max_iterations": ctx.state.max_iterations,
        "source": "PDF" if ctx.paper.pdf_path else "Images",
    }
    
    return {
        "content": [{"type": "text", "text": json.dumps(info, indent=2)}]
    }