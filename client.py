"""
CIViC Extraction Client
=======================

Encapsulates the Claude Agent SDK client for the CIViC extraction pipeline.
Implements the Reader-First architecture with "All At Once" image strategy.
"""

import base64
from typing import Dict, Any, List

from claude_agent_sdk import (
    ClaudeSDKClient,
    ClaudeAgentOptions,
    AgentDefinition,
    AssistantMessage,
    TextBlock,
    ThinkingBlock,
    ToolUseBlock,
    ResultMessage,
    HookMatcher,
)

from context import get_current_context
from hooks import logging_hooks
from hooks.logging_hooks import logger
from config import MAX_TURNS, MAX_ITERATIONS
from tool_registry import (
    build_civic_mcp_server,
    READER_TOOLS,
    ORCHESTRATOR_AND_SUBAGENT_TOOLS,
)

# =============================================================================
# AGENT DEFINITIONS
# =============================================================================

# Reader System Prompt (Phase 1)
READER_SYSTEM_PROMPT = """You are a specialized Paper Reader agent. Your ONLY job is to read 
a scientific paper (provided as images in the context) and extract ALL content into a structured format.

## YOUR MISSION
Read every page carefully and extract:
1. Paper metadata (title, authors, journal, year)
2. Paper type (PRIMARY, REVIEW, META_ANALYSIS, CASE_REPORT)
3. Full abstract text
4. All section content
5. ALL tables with headers, rows, and captions
6. ALL figures with captions and descriptions  
7. ALL statistics (ORR, HR, OR, CI, p-values, sample sizes)
8. Key entities (genes, variants, diseases, therapies)
9. Clinical trial information

## CRITICAL RULES
1. Extract ONLY what you see - no inference
2. Be exhaustive with statistics - every number matters
3. Tables are CRITICAL - extract all data
4. Note figure content and any visible statistics

## WORKFLOW
1. Analyze all the page images provided in the user message.
2. Call save_paper_content with complete extraction.

Do NOT ask for pages to be read - they are already provided.
"""

# Orchestrator System Prompt (Phase 2)
ORCHESTRATOR_SYSTEM_PROMPT = f"""You are the Orchestrator coordinating evidence extraction.

## WORKFLOW (Phase 2 - Text Based)
The Reader has already extracted the paper content. You will now coordinate the Planner, Extractor, and Critic.

### Step 1: PLANNER  
Delegate to "planner":
- Planner calls get_paper_content
- Planner creates extraction strategy

### Step 2: EXTRACTOR
Delegate to "extractor":
- Extractor calls get_paper_content
- Extractor produces evidence items

### Step 3: CRITIC
Delegate to "critic":
- Critic calls get_paper_content
- Critic validates items

### Iteration
If NEEDS_REVISION: increment_iteration → Extractor → Critic
Maximum {MAX_ITERATIONS} iterations.

    ### Finalization
    After APPROVED:
    1. Delegate to "normalizer" to standardize IDs
    2. finalize_extraction
    
    ## CRITICAL RULES
    - Use Task tool to delegate to agents
    - All agents must use get_paper_content (TEXT only)
"""

# Normalizer Agent - Works from TEXT & TOOLS
NORMALIZER_AGENT = AgentDefinition(
    description="Standardizes entities to ontologies (RxNorm, EFO, etc.)",
    prompt="""You are an expert Clinical Data Normalizer.
Your goal is to standardize extracted evidence items to standard ontologies.

## YOUR PROCESS
1. **Review**: Call `get_draft_extractions`.
2. **Normalize**: For each item, lookup missing IDs using your tools.
   **MANDATORY**: You MUST attempt to find ALL applicable IDs for each entity type. Do not stop at the first match.
   
   - Gene -> `lookup_gene_entrez`
   - Variant -> `lookup_variant_info`
   - Drug -> `lookup_rxnorm` AND `lookup_therapy_ncit` AND `lookup_safety_profile`
   - Disease -> `lookup_efo` AND `lookup_disease_doid`
   - Trial -> `lookup_clinical_trial`
   - Phenotype -> `lookup_hpo`
   - PMID -> `lookup_pmcid`

3. **INTELLIGENT ERROR HANDLING**:
   - If a tool returns "Not found" or error:
     - **Analyze**: Check for typos (e.g. "Mellanoma"), extra words, or synonyms.
     - **RETRY**: Call the tool again with the corrected term.
     - Only give up after retrying.

4. **Save**: Call `save_evidence_items` with the updated list.
5. **Finish**: Call `finalize_extraction`.
""",
    tools=[
        "mcp__civic_tools__get_draft_extractions",
        "mcp__civic_tools__save_evidence_items",
        "mcp__civic_tools__finalize_extraction",
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
)

# Planner Agent - Works from TEXT
PLANNER_AGENT = AgentDefinition(
    description="Creates extraction plan from paper content",
    prompt="""You are a Planner agent for CIViC evidence extraction.

## YOUR ROLE
Analyze the paper content (provided as TEXT) and create an extraction strategy.

## WORKFLOW
1. Call get_paper_content to get the Reader's extraction
2. Analyze the content to identify extractable evidence
3. Call save_extraction_plan with your analysis

## CRITICAL
- Work ONLY from the text content returned by get_paper_content
- Do NOT use training knowledge to fill gaps
""",
    tools=[
        "mcp__civic_tools__get_paper_info",
        "mcp__civic_tools__get_paper_content",
        "mcp__civic_tools__save_extraction_plan",
    ]
)

# Extractor Agent - Works from TEXT
EXTRACTOR_AGENT = AgentDefinition(
    description="Extracts evidence items from paper content",
    prompt="""You are an Extractor agent for CIViC evidence extraction.

## YOUR ROLE
Extract actionable clinical evidence from paper content (TEXT).

## REQUIRED FIELDS (ALL 8 MANDATORY)
1. feature_names: Gene name
2. variant_names: Specific variant
3. disease_name: Disease type
4. evidence_type: PREDICTIVE/PROGNOSTIC/DIAGNOSTIC/PREDISPOSING
5. evidence_level: A/B/C/D/E
6. evidence_direction: SUPPORTS/DOES_NOT_SUPPORT
7. evidence_significance: Based on type
8. evidence_description: With statistics

## REASONING FIELDS (MANDATORY)
- source_page_numbers: e.g. "Page 3, Table 1"
- verbatim_quote: The exact sentence supporting the claim
- extraction_confidence: 0.0 to 1.0
- extraction_reasoning: Explain WHY this evidence is actionable

## WORKFLOW
1. Call get_paper_content to get the text
2. Call get_extraction_plan to see what to extract
3. For each evidence item, call check_actionability
4. Call validate_evidence_item before adding
5. Call save_evidence_items with all items

## CRITICAL
- Work from get_paper_content text only
- Include verbatim quotes from the text
""",
    tools=[
        "mcp__civic_tools__get_paper_info",
        "mcp__civic_tools__get_paper_content",
        "mcp__civic_tools__get_extraction_plan",
        "mcp__civic_tools__get_draft_extractions",
        "mcp__civic_tools__check_actionability",
        "mcp__civic_tools__validate_evidence_item",
        "mcp__civic_tools__save_evidence_items",
    ]
)

# Critic Agent - Works from TEXT
CRITIC_AGENT = AgentDefinition(
    description="Validates evidence items against paper content",
    prompt="""You are a Critic agent for CIViC evidence validation.

## YOUR ROLE
Validate extracted evidence items against paper content (TEXT).

## VALIDATION CHECKLIST
1. All 8 required fields present
2. Type-specific rules (PREDICTIVE needs therapy_names)
3. Statistics match the paper content
4. Verbatim quotes appear in content

## WORKFLOW
1. Call get_paper_content to get the text
2. Call get_extraction_plan for context
3. Call get_draft_extractions to see items
4. Validate each item against the content
5. Call save_critique with assessment

## OUTPUT
- APPROVE: All items valid
- NEEDS_REVISION: Some fixes needed
- REJECT: Fundamental issues

## CRITICAL
- Work from get_paper_content text only
""",
    tools=[
        "mcp__civic_tools__get_paper_info",
        "mcp__civic_tools__get_paper_content",
        "mcp__civic_tools__get_extraction_plan",
        "mcp__civic_tools__get_draft_extractions",
        "mcp__civic_tools__check_actionability",
        "mcp__civic_tools__validate_evidence_item",
        "mcp__civic_tools__save_critique",
    ]
)


class CivicExtractionClient:
    """Wrapper for ClaudeSDKClient specific to CIViC extraction."""

    def __init__(self, verbose: bool = True):
        self.verbose = verbose
        # Create MCP server with all tools once
        self.civic_server = build_civic_mcp_server()

    def _create_options(self, phase: str) -> ClaudeAgentOptions:
        """Create ClaudeAgentOptions based on the phase."""

        hook_config = {
            "PreToolUse": [HookMatcher(hooks=[logging_hooks.log_tool_usage])],
            "PostToolUse": [HookMatcher(hooks=[logging_hooks.log_tool_result])],
            "SubagentStop": [HookMatcher(hooks=[logging_hooks.log_subagent_stop])],
        }
        
        if phase == "reader":
            # Phase 1: Reader (Root Agent)
            return ClaudeAgentOptions(
                system_prompt=READER_SYSTEM_PROMPT,
                mcp_servers={"civic_tools": self.civic_server},
                allowed_tools=READER_TOOLS,
                permission_mode="acceptEdits",
                max_turns=10, # Reader shouldn't take too long
                can_use_tool=self._permission_handler,
                setting_sources=["project"],
                hooks=hook_config,
            )
        else:
            # Phase 2: Orchestrator (Root Agent) with Subagents
            return ClaudeAgentOptions(
                system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
                mcp_servers={"civic_tools": self.civic_server},
                agents={
                    "planner": PLANNER_AGENT,
                    "extractor": EXTRACTOR_AGENT,
                    "critic": CRITIC_AGENT,
                    "normalizer": NORMALIZER_AGENT,
                },
                allowed_tools=ORCHESTRATOR_AND_SUBAGENT_TOOLS,
                permission_mode="acceptEdits",
                max_turns=MAX_TURNS,
                can_use_tool=self._permission_handler,
                setting_sources=["project"],
                hooks=hook_config,
            )

    async def _permission_handler(self, tool_name: str, input_data: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Log tool calls."""
        summary = {}
        if isinstance(input_data, dict):
            if "title" in input_data:
                summary["title"] = input_data["title"][:40]
            if "items" in input_data and isinstance(input_data["items"], list):
                summary["items"] = len(input_data["items"])
            if "overall_assessment" in input_data:
                summary["assessment"] = input_data["overall_assessment"]
        
        logger.info(f"[TOOL] {tool_name} | {summary}")
        return {"behavior": "allow", "updatedInput": input_data}

    def _load_images_from_pdf(self, pdf_path: str) -> List[Dict[str, Any]]:
        """
        Render PDF pages to images for direct injection.
        """
        import fitz  # PyMuPDF
        
        images_content = []
        try:
            doc = fitz.open(pdf_path)
            # Limit to first 20 pages to avoid context overflow if paper is huge
            # Most relevant info is in first 10-15 pages
            max_pages = min(len(doc), 20)
            
            logger.info(f"Rendering {max_pages} pages from PDF for Reader context...")
            
            for i in range(max_pages):
                page = doc[i]
                # Reduce DPI to avoid pipe errors (1.5 = ~108dpi)
                pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5)) 
                # Use higher compression for JPEG to keep size down
                data = base64.b64encode(pix.tobytes("jpeg", jpg_quality=85)).decode("utf-8")
                
                images_content.append({
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": "image/jpeg",
                        "data": data
                    }
                })
            doc.close()
        except Exception as e:
            logger.error(f"Failed to render PDF images: {e}")
            
        return images_content

    async def run_reader_phase(self):
        """
        Phase 1: Run Reader Agent with ALL images.
        Uses chunked injection to avoid pipe size limits.
        """
        logger.info("=== PHASE 1: READER (Chunked Injection) ===")
        options = self._create_options("reader")
        context = get_current_context()
        
        # Load all images first
        images = []
        if context.paper.pdf_path:
            images = self._load_images_from_pdf(context.paper.pdf_path)
        elif context.paper.page_images:
            for img_path in context.paper.page_images[:20]:
                with open(img_path, "rb") as f:
                    data = base64.b64encode(f.read()).decode("utf-8")
                    images.append({
                        "type": "image",
                        "source": {
                            "type": "base64",
                            "media_type": "image/jpeg",
                            "data": data
                        }
                    })
        
        logger.info(f"Injecting {len(images)} page images into Reader context.")

        # Chunk images to avoid Pipe errors (max 2 per turn)
        CHUNK_SIZE = 2
        
        async with ClaudeSDKClient(options=options) as client:
            
            # Send images in chunks
            for i in range(0, len(images), CHUNK_SIZE):
                chunk = images[i:i+CHUNK_SIZE]
                is_last_chunk = (i + CHUNK_SIZE) >= len(images)
                
                # Construct message for this chunk
                chunk_content = []
                
                if i == 0:
                    # First chunk instructions
                    chunk_content.append({
                        "type": "text", 
                        "text": f"I am uploading the paper in parts. Part {i//CHUNK_SIZE + 1}. Read these pages but DO NOT extract yet. Just acknowledge with 'Received Part {i//CHUNK_SIZE + 1}'."
                    })
                elif not is_last_chunk:
                    # Middle chunk instructions
                    chunk_content.append({
                        "type": "text", 
                        "text": f"Part {i//CHUNK_SIZE + 1}. Read these pages but DO NOT extract yet. Just acknowledge with 'Received Part {i//CHUNK_SIZE + 1}'."
                    })
                else:
                    # Last chunk instructions
                    chunk_content.append({
                        "type": "text", 
                        "text": (
                            f"Part {i//CHUNK_SIZE + 1} (Final). "
                            "Now you have all pages. Extract ALL scientific data (metadata, sections, tables, figures, stats) "
                            "and call 'save_paper_content' IMMEDIATELY. "
                            "Do not use 'read_paper_page'."
                        )
                    })
                
                # Add images
                chunk_content.extend(chunk)
                
                # Send chunk
                logger.info(f"Sending chunk {i//CHUNK_SIZE + 1} ({len(chunk)} images)...")
                
                # Create the User Message wrapped in 'message' field as expected by CLI
                user_message = {
                    "type": "user",
                    "message": {
                        "role": "user",
                        "content": chunk_content
                    }
                }

                # Generator yielding the Message object
                async def message_generator():
                    yield user_message

                await client.query(message_generator())
                
                # Process response (drain it)
                async for message in client.receive_response():
                    await self._process_message(message, "Reader")

    async def run_orchestrator_phase(self):
        """Phase 2: Run Orchestrator with text context."""
        logger.info("=== PHASE 2: ORCHESTRATOR ===")
        options = self._create_options("orchestrator")
        
        # SMART RESUME PROMPT
        prompt = (
            "Begin the extraction workflow. "
            "Check your context first: "
            "1. If 'extraction_plan' exists, SKIP Planner and go straight to Extractor. "
            "2. If 'draft_extractions' exist, check if they need validation (Critic) or Normalization. "
            "Otherwise, start by delegating to the Planner."
        )
        
        async with ClaudeSDKClient(options=options) as client:
            await client.query(prompt)
            async for message in client.receive_response():
                await self._process_message(message, "Orchestrator")

    async def _process_message(self, message, phase):
        """Process and log messages."""
        if isinstance(message, AssistantMessage):
            for block in message.content:
                if isinstance(block, TextBlock):
                    if self.verbose:
                        text = block.text[:150] + "..." if len(block.text) > 150 else block.text
                        print(f"[{phase}] {text}")
                    logger.debug(f"[{phase}] {block.text[:500]}")
                
                elif isinstance(block, ThinkingBlock):
                    if block.thinking:
                        logger.info(f"[{phase}] [THINKING] {block.thinking[:300]}...")
                
                elif isinstance(block, ToolUseBlock):
                    log_msg = f"[{phase}] [TOOL] {block.name}"
                    if isinstance(block.input, dict):
                        if 'subagent_type' in block.input:
                            log_msg += f" → {block.input['subagent_type']}"
                    logger.info(log_msg)
                    if self.verbose:
                        print(log_msg)
        
        if isinstance(message, ResultMessage):
            if message.subtype == 'success':
                logger.info(f"[{phase}] Completed successfully")
