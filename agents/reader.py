"""
Reader Agent
============

PURPOSE: Read the entire paper ONCE and extract ALL content into structured text.
This becomes the SINGLE SOURCE OF TRUTH for all downstream agents.

WHY THIS EXISTS:
- Eliminates redundant page reads (was 53 reads for 13-page paper!)
- Prevents hallucination (planner can't imagine content that isn't extracted)
- Ensures consistency (all agents work from same extracted content)
- Reduces cost (images are expensive, text is cheap)
- Speeds up pipeline (read once, use many times)

ARCHITECTURE:
    ┌─────────────────────────────────────────────────────────┐
    │ READER AGENT (runs FIRST, ONE TIME)                     │
    │   Input: Paper pages as images                          │
    │   Output: Structured PaperContent object                │
    └─────────────────────────────────────────────────────────┘
                              ↓
                   [PaperContent - TEXT ONLY]
                              ↓
    ┌─────────────────────────────────────────────────────────┐
    │ Planner: uses PaperContent text → makes plan            │
    │ Extractor: uses PaperContent text → extracts evidence   │
    │ Critic: uses PaperContent text → validates              │
    └─────────────────────────────────────────────────────────┘
"""

from dataclasses import dataclass, field
from typing import Optional
import json


# =============================================================================
# DATA STRUCTURES - What the Reader produces
# =============================================================================

@dataclass
class TableData:
    """Structured representation of a table from the paper."""
    table_id: str  # "Table 1", "Table 2", etc.
    page_number: int
    caption: str
    headers: list[str]
    rows: list[list[str]]  # Each row is a list of cell values
    footnotes: str = ""
    
    def to_text(self) -> str:
        """Convert table to readable text format."""
        lines = [
            f"=== {self.table_id} (Page {self.page_number}) ===",
            f"Caption: {self.caption}",
            "",
            "| " + " | ".join(self.headers) + " |",
            "|" + "|".join(["---"] * len(self.headers)) + "|",
        ]
        for row in self.rows:
            lines.append("| " + " | ".join(row) + " |")
        if self.footnotes:
            lines.append(f"\nFootnotes: {self.footnotes}")
        return "\n".join(lines)


@dataclass 
class FigureData:
    """Structured representation of a figure from the paper."""
    figure_id: str  # "Figure 1", "Figure 2", etc.
    page_number: int
    caption: str
    figure_type: str  # "Kaplan-Meier", "Bar chart", "Forest plot", "Heatmap", etc.
    description: str  # What the figure shows
    statistics: list[str] = field(default_factory=list)  # Any stats visible in figure
    
    def to_text(self) -> str:
        """Convert figure to readable text format."""
        lines = [
            f"=== {self.figure_id} (Page {self.page_number}) ===",
            f"Type: {self.figure_type}",
            f"Caption: {self.caption}",
            f"Description: {self.description}",
        ]
        if self.statistics:
            lines.append(f"Statistics shown: {', '.join(self.statistics)}")
        return "\n".join(lines)


@dataclass
class StatisticData:
    """A specific statistic extracted from the paper."""
    value: str  # "OR 3.7", "ORR 17.1%", "HR 0.65"
    context: str  # What this statistic refers to
    confidence_interval: str = ""  # "95% CI 2.8-4.9"
    p_value: str = ""  # "p<0.001"
    sample_size: str = ""  # "n=300"
    page_number: int = 0
    source_location: str = ""  # "Table 1", "Results section", "Figure 2"
    
    def to_text(self) -> str:
        """Convert to readable text."""
        parts = [f"{self.value}"]
        if self.confidence_interval:
            parts.append(f"({self.confidence_interval})")
        if self.p_value:
            parts.append(f"{self.p_value}")
        if self.sample_size:
            parts.append(f"{self.sample_size}")
        stat_str = " ".join(parts)
        return f"{stat_str} - {self.context} [Page {self.page_number}, {self.source_location}]"


@dataclass
class SectionContent:
    """Content from a specific section of the paper."""
    name: str  # "Abstract", "Introduction", "Results", "Discussion", etc.
    page_numbers: list[int]
    content: str  # Full text of the section
    subsections: list[str] = field(default_factory=list)  # Subsection names if any


@dataclass
class PaperContent:
    """
    Complete structured extraction of a paper.
    This is the SINGLE SOURCE OF TRUTH for all downstream agents.
    """
    # Metadata - extracted from first page
    title: str
    authors: list[str]
    journal: str
    year: int
    doi: str = ""
    pmid: str = ""
    
    # Paper classification
    paper_type: str = ""  # "PRIMARY", "REVIEW", "META_ANALYSIS", "CASE_REPORT"
    
    # Content sections
    abstract: str = ""
    sections: list[SectionContent] = field(default_factory=list)
    
    # Structured data extractions
    tables: list[TableData] = field(default_factory=list)
    figures: list[FigureData] = field(default_factory=list)
    statistics: list[StatisticData] = field(default_factory=list)
    
    # Clinical/genomic entities identified
    genes: list[str] = field(default_factory=list)
    variants: list[str] = field(default_factory=list)
    diseases: list[str] = field(default_factory=list)
    therapies: list[str] = field(default_factory=list)
    
    # Clinical trial info
    clinical_trials: list[dict] = field(default_factory=list)  # [{"name": "KEYNOTE-100", "nct_id": "NCT02674061", "phase": "II"}]
    
    # Raw page content (for reference)
    page_contents: dict[int, str] = field(default_factory=dict)  # {1: "page 1 text", 2: "page 2 text"}
    
    def to_context_document(self) -> str:
        """
        Convert to a comprehensive text document that can be passed to all agents.
        This replaces image-based page reading with text-based context.
        """
        lines = [
            "=" * 80,
            "PAPER CONTENT EXTRACTION",
            "=" * 80,
            "",
            f"TITLE: {self.title}",
            f"AUTHORS: {', '.join(self.authors)}",
            f"JOURNAL: {self.journal} ({self.year})",
            f"PAPER TYPE: {self.paper_type}",
        ]
        
        if self.doi:
            lines.append(f"DOI: {self.doi}")
        if self.pmid:
            lines.append(f"PMID: {self.pmid}")
        
        # Clinical trials
        if self.clinical_trials:
            lines.append("")
            lines.append("CLINICAL TRIALS:")
            for trial in self.clinical_trials:
                trial_str = f"  - {trial.get('name', 'Unknown')}"
                if trial.get('nct_id'):
                    trial_str += f" ({trial['nct_id']})"
                if trial.get('phase'):
                    trial_str += f" Phase {trial['phase']}"
                lines.append(trial_str)
        
        # Key entities
        lines.append("")
        lines.append("-" * 40)
        lines.append("KEY ENTITIES IDENTIFIED")
        lines.append("-" * 40)
        if self.genes:
            lines.append(f"GENES: {', '.join(self.genes)}")
        if self.variants:
            lines.append(f"VARIANTS: {', '.join(self.variants)}")
        if self.diseases:
            lines.append(f"DISEASES: {', '.join(self.diseases)}")
        if self.therapies:
            lines.append(f"THERAPIES: {', '.join(self.therapies)}")
        
        # Abstract
        lines.append("")
        lines.append("-" * 40)
        lines.append("ABSTRACT")
        lines.append("-" * 40)
        lines.append(self.abstract)
        
        # Sections
        for section in self.sections:
            lines.append("")
            lines.append("-" * 40)
            lines.append(f"SECTION: {section.name} (Pages {', '.join(map(str, section.page_numbers))})")
            lines.append("-" * 40)
            lines.append(section.content)
        
        # Tables
        if self.tables:
            lines.append("")
            lines.append("=" * 40)
            lines.append("TABLES")
            lines.append("=" * 40)
            for table in self.tables:
                lines.append("")
                lines.append(table.to_text())
        
        # Figures
        if self.figures:
            lines.append("")
            lines.append("=" * 40)
            lines.append("FIGURES")
            lines.append("=" * 40)
            for figure in self.figures:
                lines.append("")
                lines.append(figure.to_text())
        
        # Key Statistics Summary
        if self.statistics:
            lines.append("")
            lines.append("=" * 40)
            lines.append("KEY STATISTICS EXTRACTED")
            lines.append("=" * 40)
            for stat in self.statistics:
                lines.append(f"  • {stat.to_text()}")
        
        return "\n".join(lines)
    
    def to_json(self) -> str:
        """Convert to JSON for storage."""
        return json.dumps({
            "title": self.title,
            "authors": self.authors,
            "journal": self.journal,
            "year": self.year,
            "doi": self.doi,
            "pmid": self.pmid,
            "paper_type": self.paper_type,
            "abstract": self.abstract,
            "genes": self.genes,
            "variants": self.variants,
            "diseases": self.diseases,
            "therapies": self.therapies,
            "clinical_trials": self.clinical_trials,
            "tables": [
                {
                    "table_id": t.table_id,
                    "page_number": t.page_number,
                    "caption": t.caption,
                    "headers": t.headers,
                    "rows": t.rows,
                    "footnotes": t.footnotes
                }
                for t in self.tables
            ],
            "figures": [
                {
                    "figure_id": f.figure_id,
                    "page_number": f.page_number,
                    "caption": f.caption,
                    "figure_type": f.figure_type,
                    "description": f.description,
                    "statistics": f.statistics
                }
                for f in self.figures
            ],
            "statistics": [
                {
                    "value": s.value,
                    "context": s.context,
                    "confidence_interval": s.confidence_interval,
                    "p_value": s.p_value,
                    "sample_size": s.sample_size,
                    "page_number": s.page_number,
                    "source_location": s.source_location
                }
                for s in self.statistics
            ],
            "sections": [
                {
                    "name": s.name,
                    "page_numbers": s.page_numbers,
                    "content": s.content,
                    "subsections": s.subsections
                }
                for s in self.sections
            ]
        }, indent=2)


# =============================================================================
# READER AGENT PROMPT
# =============================================================================

READER_SYSTEM_PROMPT = """You are a specialized Paper Reader agent. Your ONLY job is to read 
a scientific paper (provided as page images) and extract ALL content into a structured format.

## YOUR MISSION
Read every page carefully and extract:
1. Paper metadata (title, authors, journal, year, DOI, PMID)
2. Paper type classification (PRIMARY, REVIEW, META_ANALYSIS, CASE_REPORT)
3. Full abstract text
4. All section content (Introduction, Methods, Results, Discussion)
5. ALL tables with headers, rows, and captions
6. ALL figures with captions, types, and descriptions
7. ALL statistics (ORR, HR, OR, CI, p-values, sample sizes)
8. Key entities (genes, variants, diseases, therapies)
9. Clinical trial information (names, NCT IDs, phases)

## CRITICAL RULES

### Rule 1: Extract ONLY what you see
- Do NOT infer or assume content
- Do NOT use your training knowledge to fill gaps
- If you can't read something clearly, mark it as "[UNCLEAR]"
- Quote exact text when extracting

### Rule 2: Be exhaustive with statistics
Every number matters for clinical evidence extraction:
- Response rates (ORR, CR, PR, SD, PD)
- Survival data (OS, PFS, DFS, with medians and CIs)
- Hazard ratios with confidence intervals
- Odds ratios with confidence intervals
- P-values
- Sample sizes (n=)
- Percentages with denominators

### Rule 3: Tables are CRITICAL
Tables contain the most important data. For each table:
- Extract the EXACT caption
- Extract ALL column headers
- Extract ALL rows of data
- Note any footnotes or abbreviations

### Rule 4: Figures contain hidden data
Many figures (especially Kaplan-Meier curves, forest plots) contain statistics:
- Read statistics from figure legends
- Note p-values, HRs, medians shown on figures
- Describe what the figure shows

### Rule 5: Identify the paper type FIRST
Read the title and abstract to determine:
- PRIMARY: Original patient data, clinical trial, cohort study
- REVIEW: Summarizes other studies (but may cite specific data!)
- META_ANALYSIS: Pools data from multiple studies
- CASE_REPORT: Individual patient cases

## OUTPUT FORMAT
You must call the save_paper_content tool with the complete extraction.
Do NOT provide partial extractions.
Read ALL pages before saving.

## EXAMPLE STATISTICS TO EXTRACT
- "ORR was 17.1% (95% CI 9.4-27.5)" → value="ORR 17.1%", CI="95% CI 9.4-27.5"
- "HR 0.65 (95% CI 0.45-0.94, p=0.02)" → value="HR 0.65", CI="95% CI 0.45-0.94", p="p=0.02"
- "Median PFS 8.3 months (n=156)" → value="Median PFS 8.3 months", sample_size="n=156"
- "V617F mutation found in 95% (285/300)" → value="95%", context="V617F mutation prevalence", sample_size="n=300"
"""

READER_TASK_PROMPT = """Read all {num_pages} pages of this paper and extract the complete content.

Paper ID: {paper_id}
Folder metadata: Author={author}, Year={year}

IMPORTANT: The folder metadata may not match the actual paper content!
Read the actual title from page 1 to confirm what this paper is about.

## YOUR TASK
1. Read page 1 - extract title, authors, journal, abstract
2. Read all pages - extract all sections, tables, figures, statistics
3. Identify all genes, variants, diseases, therapies mentioned
4. Extract ALL statistics with their context
5. Call save_paper_content with the complete extraction

Start by reading page 1 to identify the paper.
"""


# =============================================================================
# READER AGENT TOOLS
# =============================================================================

def get_reader_tools(context) -> list[dict]:
    """
    Tools available to the Reader agent.
    """
    return [
        {
            "name": "read_page",
            "description": "Read a specific page of the paper as an image. Returns the page image for visual analysis.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "page_num": {
                        "type": "integer",
                        "description": "Page number to read (1-indexed)"
                    }
                },
                "required": ["page_num"]
            }
        },
        {
            "name": "save_paper_content",
            "description": "Save the complete extracted paper content. Call this AFTER reading all pages.",
            "input_schema": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Exact title from the paper"},
                    "authors": {"type": "array", "items": {"type": "string"}, "description": "Author list"},
                    "journal": {"type": "string", "description": "Journal name"},
                    "year": {"type": "integer", "description": "Publication year"},
                    "doi": {"type": "string", "description": "DOI if visible"},
                    "pmid": {"type": "string", "description": "PMID if visible"},
                    "paper_type": {
                        "type": "string",
                        "enum": ["PRIMARY", "REVIEW", "META_ANALYSIS", "CASE_REPORT"],
                        "description": "Paper classification"
                    },
                    "abstract": {"type": "string", "description": "Full abstract text"},
                    "genes": {"type": "array", "items": {"type": "string"}, "description": "All genes mentioned"},
                    "variants": {"type": "array", "items": {"type": "string"}, "description": "All variants mentioned"},
                    "diseases": {"type": "array", "items": {"type": "string"}, "description": "All diseases mentioned"},
                    "therapies": {"type": "array", "items": {"type": "string"}, "description": "All therapies mentioned"},
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
                            "required": ["table_id", "page_number", "caption", "headers", "rows"]
                        },
                        "description": "All tables extracted"
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
                            "required": ["figure_id", "page_number", "caption", "figure_type", "description"]
                        },
                        "description": "All figures extracted"
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
                            "required": ["value", "context", "page_number"]
                        },
                        "description": "All statistics extracted"
                    },
                    "sections": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "page_numbers": {"type": "array", "items": {"type": "integer"}},
                                "content": {"type": "string"},
                                "subsections": {"type": "array", "items": {"type": "string"}}
                            },
                            "required": ["name", "page_numbers", "content"]
                        },
                        "description": "All sections extracted"
                    }
                },
                "required": ["title", "authors", "journal", "year", "paper_type", "abstract"]
            }
        }
    ]


def create_paper_content_from_tool_call(tool_input: dict) -> PaperContent:
    """
    Create a PaperContent object from the save_paper_content tool call.
    """
    # Convert tables
    tables = []
    for t in tool_input.get("tables", []):
        tables.append(TableData(
            table_id=t["table_id"],
            page_number=t["page_number"],
            caption=t["caption"],
            headers=t["headers"],
            rows=t["rows"],
            footnotes=t.get("footnotes", "")
        ))
    
    # Convert figures
    figures = []
    for f in tool_input.get("figures", []):
        figures.append(FigureData(
            figure_id=f["figure_id"],
            page_number=f["page_number"],
            caption=f["caption"],
            figure_type=f["figure_type"],
            description=f["description"],
            statistics=f.get("statistics", [])
        ))
    
    # Convert statistics
    statistics = []
    for s in tool_input.get("statistics", []):
        statistics.append(StatisticData(
            value=s["value"],
            context=s["context"],
            confidence_interval=s.get("confidence_interval", ""),
            p_value=s.get("p_value", ""),
            sample_size=s.get("sample_size", ""),
            page_number=s.get("page_number", 0),
            source_location=s.get("source_location", "")
        ))
    
    # Convert sections
    sections = []
    for sec in tool_input.get("sections", []):
        sections.append(SectionContent(
            name=sec["name"],
            page_numbers=sec["page_numbers"],
            content=sec["content"],
            subsections=sec.get("subsections", [])
        ))
    
    return PaperContent(
        title=tool_input["title"],
        authors=tool_input["authors"],
        journal=tool_input["journal"],
        year=tool_input["year"],
        doi=tool_input.get("doi", ""),
        pmid=tool_input.get("pmid", ""),
        paper_type=tool_input["paper_type"],
        abstract=tool_input["abstract"],
        genes=tool_input.get("genes", []),
        variants=tool_input.get("variants", []),
        diseases=tool_input.get("diseases", []),
        therapies=tool_input.get("therapies", []),
        clinical_trials=tool_input.get("clinical_trials", []),
        tables=tables,
        figures=figures,
        statistics=statistics,
        sections=sections
    )