"""
Paper Content Tools
===================

Tools for the Reader-first architecture.

These tools allow the Reader agent to save extracted paper content,
and other agents to retrieve it.
"""

from typing import Any, Dict
import json
from claude_agent_sdk import tool

from context import get_current_context
from hooks.logging_hooks import logger


@tool(
    "save_paper_content",
    "Save complete extracted paper content. Called by Reader agent after reading all pages.",
    {
        "title": str,
        "authors": list,
        "journal": str,
        "year": int,
        "paper_type": str,
        "abstract": str,
        "sections": list,
        "tables": list,
        "figures": list,
        "statistics": list,
        "genes": list,
        "variants": list,
        "diseases": list,
        "therapies": list,
        "clinical_trials": list,
    }
)
async def save_paper_content(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Save the complete extracted paper content.
    
    Called by the Reader agent after reading all pages.
    This becomes the SINGLE SOURCE OF TRUTH for all downstream agents.
    """
    # Extract arguments
    title = args.get("title", "")
    authors = args.get("authors", [])
    journal = args.get("journal", "")
    year = args.get("year", 0)
    paper_type = args.get("paper_type", "")
    abstract = args.get("abstract", "")
    sections = args.get("sections", [])
    tables = args.get("tables", [])
    figures = args.get("figures", [])
    statistics = args.get("statistics", [])
    genes = args.get("genes", [])
    variants = args.get("variants", [])
    diseases = args.get("diseases", [])
    therapies = args.get("therapies", [])
    clinical_trials = args.get("clinical_trials", [])

    context = get_current_context()
    
    # Store in context
    context.paper_content = {
        "title": title,
        "authors": authors,
        "journal": journal,
        "year": year,
        "paper_type": paper_type,
        "abstract": abstract,
        "sections": sections,
        "tables": tables,
        "figures": figures,
        "statistics": statistics,
        "genes": genes,
        "variants": variants,
        "diseases": diseases,
        "therapies": therapies,
        "clinical_trials": clinical_trials,
    }
    
    # Generate text context for other agents
    context.paper_content_text = _generate_paper_context_text(context.paper_content)
    
    # Log
    logger.info(f"[READER] Paper content saved: {title}")
    logger.info(f"[READER]   Type: {paper_type}")
    
    # Ensure we log item counts, not character counts of strings
    t_count = len(tables) if isinstance(tables, list) else 0
    f_count = len(figures) if isinstance(figures, list) else 0
    s_count = len(statistics) if isinstance(statistics, list) else 0
    
    logger.info(f"[READER]   Tables: {t_count}")
    logger.info(f"[READER]   Figures: {f_count}")
    logger.info(f"[READER]   Statistics: {s_count}")
    logger.info(f"[READER]   Genes: {genes}")
    logger.info(f"[READER]   Variants: {variants}")
    
    result = {
        "status": "saved",
        "title": title,
        "paper_type": paper_type,
        "tables_count": len(tables),
        "figures_count": len(figures),
        "statistics_count": len(statistics),
        "genes": genes,
        "variants": variants,
        "diseases": diseases,
        "therapies": therapies,
    }

    return {
        "content": [{
            "type": "text",
            "text": json.dumps(result, indent=2)
        }]
    }


@tool(
    "get_paper_content",
    "Get the extracted paper content. Returns structured content and formatted text for agent use.",
    {}
)
async def get_paper_content(args: Dict[str, Any]) -> Dict[str, Any]:
    """
    Get the extracted paper content.
    
    Used by Planner, Extractor, and Critic agents to access
    the paper content extracted by the Reader.
    """
    context = get_current_context()
    
    if not hasattr(context, 'paper_content') or not context.paper_content:
        return {
            "content": [{
                "type": "text",
                "text": json.dumps({
                    "error": "Paper content not yet extracted. Reader agent must run first.",
                    "hint": "Delegate to 'reader' agent first to extract paper content."
                })
            }],
            "is_error": True
        }
    
    # Return ONLY the text representation to save context window
    # The full JSON structure is available if needed, but text is better for LLM reasoning
    return {
        "content": [{
            "type": "text",
            "text": context.paper_content_text
        }]
    }


def _generate_paper_context_text(content: dict) -> str:
    """
    Generate formatted text context from paper content.
    
    This text is passed to Planner/Extractor/Critic agents
    so they can work from the extracted content without reading images.
    """
    if not isinstance(content, dict):
        return f"Error: Paper content is not a dictionary. Got {type(content)}: {content}"

    lines = [
        "=" * 80,
        "PAPER CONTENT (Extracted by Reader Agent)",
        "=" * 80,
        "",
        f"TITLE: {content.get('title', 'Unknown')}",
        f"AUTHORS: {', '.join(content.get('authors', []) if isinstance(content.get('authors'), list) else [])}",
        f"JOURNAL: {content.get('journal', 'Unknown')} ({content.get('year', '?')})",
        f"PAPER TYPE: {content.get('paper_type', 'Unknown')}",
    ]
    
    # Key entities section
    if any([content.get('genes'), content.get('variants'), content.get('diseases'), content.get('therapies')]):
        lines.extend([
            "",
            "-" * 40,
            "KEY ENTITIES IDENTIFIED",
            "-" * 40,
        ])
        if content.get('genes'):
            genes = content['genes'] if isinstance(content['genes'], list) else [str(content['genes'])]
            lines.append(f"GENES: {', '.join(str(g) for g in genes)}")
        if content.get('variants'):
            variants = content['variants'] if isinstance(content['variants'], list) else [str(content['variants'])]
            lines.append(f"VARIANTS: {', '.join(str(v) for v in variants)}")
        if content.get('diseases'):
            diseases = content['diseases'] if isinstance(content['diseases'], list) else [str(content['diseases'])]
            lines.append(f"DISEASES: {', '.join(str(d) for d in diseases)}")
        if content.get('therapies'):
            therapies = content['therapies'] if isinstance(content['therapies'], list) else [str(content['therapies'])]
            lines.append(f"THERAPIES: {', '.join(str(t) for t in therapies)}")
    
    # Clinical trials
    if content.get('clinical_trials'):
        lines.extend([
            "",
            "-" * 40,
            "CLINICAL TRIALS",
            "-" * 40,
        ])
        trials = content['clinical_trials'] if isinstance(content['clinical_trials'], list) else []
        for trial in trials:
            if isinstance(trial, dict):
                trial_str = f"  - {trial.get('name', 'Unknown')}"
                if trial.get('nct_id'):
                    trial_str += f" ({trial['nct_id']})"
                if trial.get('phase'):
                    trial_str += f" Phase {trial['phase']}"
                lines.append(trial_str)
            else:
                lines.append(f"  - {str(trial)}")
    
    # Abstract
    lines.extend([
        "",
        "-" * 40,
        "ABSTRACT",
        "-" * 40,
        content.get('abstract', ''),
    ])
    
    # Tables (CRITICAL - contain most important data)
    if content.get('tables'):
        lines.extend([
            "",
            "=" * 40,
            "TABLES (Key Data Source)",
            "=" * 40,
        ])
        tables = content['tables'] if isinstance(content['tables'], list) else []
        for table in tables:
            if not isinstance(table, dict):
                lines.append(f"\n[Malformed Table Data]: {str(table)}")
                continue
                
            lines.append(f"\n### {table.get('table_id', 'Table')} (Page {table.get('page_number', '?')})")
            lines.append(f"Caption: {table.get('caption', '')}")
            
            # Format as markdown table
            if table.get('headers'):
                headers = table['headers'] if isinstance(table['headers'], list) else []
                lines.append("")
                lines.append("| " + " | ".join(str(h) for h in headers) + " |")
                lines.append("|" + "|".join(["---"] * len(headers)) + "|")
            
            rows = table.get('rows', [])
            if isinstance(rows, list):
                for row in rows:
                    if isinstance(row, list):
                        lines.append("| " + " | ".join(str(cell) for cell in row) + " |")
                    else:
                        lines.append(f"| {str(row)} |")
            
            if table.get('footnotes'):
                lines.append(f"\nFootnotes: {table['footnotes']}")
    
    # Figures
    if content.get('figures'):
        lines.extend([
            "",
            "=" * 40,
            "FIGURES",
            "=" * 40,
        ])
        figures = content['figures'] if isinstance(content['figures'], list) else []
        for fig in figures:
            if not isinstance(fig, dict):
                lines.append(f"\n[Malformed Figure Data]: {str(fig)}")
                continue
                
            lines.append(f"\n### {fig.get('figure_id', 'Figure')} (Page {fig.get('page_number', '?')})")
            lines.append(f"Type: {fig.get('figure_type', 'Unknown')}")
            lines.append(f"Caption: {fig.get('caption', '')}")
            lines.append(f"Description: {fig.get('description', '')}")
            if fig.get('statistics'):
                stats = fig['statistics'] if isinstance(fig['statistics'], list) else [str(fig['statistics'])]
                lines.append(f"Statistics visible: {', '.join(str(s) for s in stats)}")
    
    # Key Statistics (extracted for quick reference)
    if content.get('statistics'):
        lines.extend([
            "",
            "=" * 40,
            "KEY STATISTICS EXTRACTED",
            "=" * 40,
            "(Use these for evidence extraction)",
        ])
        statistics = content['statistics'] if isinstance(content['statistics'], list) else []
        for stat in statistics:
            if not isinstance(stat, dict):
                lines.append(f"• {str(stat)}")
                continue
                
            stat_parts = [f"• {stat.get('value', '')}"]
            if stat.get('confidence_interval'):
                stat_parts.append(f"({stat['confidence_interval']})")
            if stat.get('p_value'):
                stat_parts.append(stat['p_value'])
            if stat.get('sample_size'):
                stat_parts.append(stat['sample_size'])
            
            stat_str = " ".join(stat_parts)
            stat_str += f" — {stat.get('context', '')}"
            stat_str += f" [Page {stat.get('page_number', '?')}, {stat.get('source_location', '')}]"
            lines.append(stat_str)
    
    # Sections (full text)
    if content.get('sections'):
        lines.extend([
            "",
            "=" * 40,
            "FULL SECTION CONTENT",
            "=" * 40,
        ])
        sections = content['sections'] if isinstance(content['sections'], list) else []
        for section in sections:
            if not isinstance(section, dict):
                lines.append(f"\n[Malformed Section]: {str(section)}")
                continue
                
            page_nums = section.get('page_numbers', [])
            page_str = ", ".join(str(p) for p in page_nums) if isinstance(page_nums, list) else str(page_nums)
            lines.extend([
                "",
                f"### {section.get('name', 'Section')} (Pages: {page_str})",
                "-" * 30,
                section.get('content', ''),
            ])
    
    return "\n".join(lines)


# =============================================================================
# TOOL SCHEMAS (for MCP registration)
# =============================================================================

SAVE_PAPER_CONTENT_SCHEMA = {
    "name": "save_paper_content",
    "description": "Save complete extracted paper content. Called by Reader agent after reading all pages.",
    "input_schema": {
        "type": "object",
        "properties": {
            "title": {
                "type": "string",
                "description": "Exact paper title"
            },
            "authors": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of author names"
            },
            "journal": {
                "type": "string",
                "description": "Journal name"
            },
            "year": {
                "type": "integer",
                "description": "Publication year"
            },
            "paper_type": {
                "type": "string",
                "enum": ["PRIMARY", "REVIEW", "META_ANALYSIS", "CASE_REPORT"],
                "description": "Paper classification"
            },
            "abstract": {
                "type": "string",
                "description": "Full abstract text"
            },
            "sections": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "page_numbers": {"type": "array", "items": {"type": "integer"}},
                        "content": {"type": "string"}
                    }
                },
                "description": "Paper sections with content"
            },
            "tables": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "table_id": {"type": "string"},
                        "page_number": {"type": "integer"},
                        "caption": {"type": "string"},
                        "headers": {"type": "array", "items": {"type": "string"}},
                        "rows": {"type": "array", "items": {"type": "array", "items": {"type": "string"}}},
                        "footnotes": {"type": "string"}
                    },
                    "required": ["table_id", "caption", "headers", "rows"]
                },
                "description": "All tables extracted from paper"
            },
            "figures": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "figure_id": {"type": "string"},
                        "page_number": {"type": "integer"},
                        "caption": {"type": "string"},
                        "figure_type": {"type": "string"},
                        "description": {"type": "string"},
                        "statistics": {"type": "array", "items": {"type": "string"}}
                    },
                    "required": ["figure_id", "caption", "description"]
                },
                "description": "All figures extracted from paper"
            },
            "statistics": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "value": {"type": "string"},
                        "context": {"type": "string"},
                        "confidence_interval": {"type": "string"},
                        "p_value": {"type": "string"},
                        "sample_size": {"type": "string"},
                        "page_number": {"type": "integer"},
                        "source_location": {"type": "string"}
                    },
                    "required": ["value", "context"]
                },
                "description": "All statistics extracted from paper"
            },
            "genes": {
                "type": "array",
                "items": {"type": "string"},
                "description": "All genes mentioned in paper"
            },
            "variants": {
                "type": "array",
                "items": {"type": "string"},
                "description": "All variants mentioned in paper"
            },
            "diseases": {
                "type": "array",
                "items": {"type": "string"},
                "description": "All diseases mentioned in paper"
            },
            "therapies": {
                "type": "array",
                "items": {"type": "string"},
                "description": "All therapies mentioned in paper"
            },
            "clinical_trials": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string"},
                        "nct_id": {"type": "string"},
                        "phase": {"type": "string"}
                    }
                },
                "description": "Clinical trial information"
            }
        },
        "required": ["title", "authors", "journal", "year", "paper_type", "abstract"]
    }
}


GET_PAPER_CONTENT_SCHEMA = {
    "name": "get_paper_content",
    "description": "Get the extracted paper content. Returns structured content and formatted text for agent use.",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": []
    }
}