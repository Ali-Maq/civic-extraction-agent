"""
Tool registry for CIViC extraction.

Centralizes MCP server construction so client/orchestrator wiring stays thin.
Currently uses existing tool implementations unchanged; future refactors can
swap in streamlined schemas without touching callers.
"""

from claude_agent_sdk import create_sdk_mcp_server

# Import tools directly from their source files
from tools.paper_tools import (
    get_paper_info,
    read_paper_page,
)
from tools.paper_content_tools import (
    save_paper_content,
    get_paper_content,
)
from tools.extraction_tools import (
    save_extraction_plan,
    get_extraction_plan,
    save_evidence_items,
    get_draft_extractions,
    save_critique,
    increment_iteration,
)
from tools.validation_tools import (
    check_actionability,
    validate_evidence_item,
)
from tools.normalization_tools import (
    finalize_extraction,
    get_tier2_coverage,
    lookup_rxnorm,
    lookup_efo,
    lookup_safety_profile,
    # New granular tools
    lookup_gene_entrez,
    lookup_variant_info_tool,
    lookup_therapy_ncit,
    lookup_disease_doid_tool,
    lookup_clinical_trial,
    lookup_hpo,
    lookup_pmcid,
)


def build_civic_mcp_server():
    """Create the civic MCP server with all registered tools."""
    return create_sdk_mcp_server(
        name="civic_tools",
        version="2.0.0",
        tools=[
            get_paper_info,
            read_paper_page,
            save_paper_content,
            get_paper_content,
            save_extraction_plan,
            get_extraction_plan,
            check_actionability,
            validate_evidence_item,
            save_evidence_items,
            get_draft_extractions,
            save_critique,
            increment_iteration,
            finalize_extraction,
            get_tier2_coverage,
            lookup_rxnorm,
            lookup_efo,
            lookup_safety_profile,
            # New granular tools
            lookup_gene_entrez,
            lookup_variant_info_tool,
            lookup_therapy_ncit,
            lookup_disease_doid_tool,
            lookup_clinical_trial,
            lookup_hpo,
            lookup_pmcid,
        ],
    )


# Allowed tool sets per phase for convenience (mirrors client defaults)
READER_TOOLS = [
    "mcp__civic_tools__get_paper_info",
    "mcp__civic_tools__read_paper_page",
    "mcp__civic_tools__save_paper_content",
]

ORCHESTRATOR_AND_SUBAGENT_TOOLS = [
    "Task",
    "mcp__civic_tools__get_paper_info",
    "mcp__civic_tools__get_paper_content",
    "mcp__civic_tools__save_extraction_plan",
    "mcp__civic_tools__get_extraction_plan",
    "mcp__civic_tools__check_actionability",
    "mcp__civic_tools__validate_evidence_item",
    "mcp__civic_tools__save_evidence_items",
    "mcp__civic_tools__get_draft_extractions",
    "mcp__civic_tools__save_critique",
    "mcp__civic_tools__increment_iteration",
    "mcp__civic_tools__finalize_extraction",
    "mcp__civic_tools__get_tier2_coverage",
    # Normalizer tools
    "mcp__civic_tools__lookup_rxnorm",
    "mcp__civic_tools__lookup_efo",
    "mcp__civic_tools__lookup_safety_profile",
    "mcp__civic_tools__lookup_gene_entrez",
    "mcp__civic_tools__lookup_variant_info_tool",
    "mcp__civic_tools__lookup_therapy_ncit",
    "mcp__civic_tools__lookup_disease_doid_tool",
    "mcp__civic_tools__lookup_clinical_trial",
    "mcp__civic_tools__lookup_hpo",
    "mcp__civic_tools__lookup_pmcid",
]
