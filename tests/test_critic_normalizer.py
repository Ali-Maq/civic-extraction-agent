
import asyncio
import json
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
# Add civic_extraction to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from context import set_current_context, CIViCContext
from client import CivicExtractionClient, CRITIC_AGENT
from tool_registry import build_civic_mcp_server
from config import CRITIC_MODEL
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, AssistantMessage, TextBlock, ToolUseBlock
from tools.normalization_tools import normalize_extractions, finalize_extraction

async def run_critic_normalizer_test(extractor_json_path):
    """Test Critic agent and Normalization."""
    print(f"=== TESTING CRITIC & NORMALIZER ===")
    print(f"Loading extractor output from: {extractor_json_path}")
    
    # 1. Load saved state
    with open(extractor_json_path, 'r') as f:
        saved_data = json.load(f)
    
    # 2. Setup Context
    context = CIViCContext()
    context.load_paper(saved_data['paper_id'])
    context.paper_content = saved_data['paper_content']
    from tools.paper_content_tools import _generate_paper_context_text
    context.paper_content_text = _generate_paper_context_text(context.paper_content)
    
    # Restore extraction state
    from context.state import ExtractionPlan
    if 'plan' in saved_data and saved_data['plan']:
        plan_data = saved_data['plan']
        # Convert dict back to ExtractionPlan object if needed, or just use dict if tool supports it
        # The tools expect it in context.state.extraction_plan
        context.state.extraction_plan = plan_data 
        
    if 'extraction' in saved_data:
        context.state.draft_extractions = saved_data['extraction'].get('draft_extractions', [])
    
    set_current_context(context)
    
    print(f"Loaded {len(context.state.draft_extractions)} draft items.")
    
    # 3. Setup Critic Client
    server = build_civic_mcp_server()
    options = ClaudeAgentOptions(
        model=CRITIC_MODEL,
        system_prompt=CRITIC_AGENT.prompt,
        mcp_servers={"civic_tools": server},
        allowed_tools=CRITIC_AGENT.tools,
        max_turns=10,
    )
    
    prompt = "Validate the draft extractions. Call 'get_draft_extractions' and 'get_paper_content' first. If good, call 'save_critique' with APPROVE."
    
    print("\n--- Starting Critic ---")
    async with ClaudeSDKClient(options=options) as client:
        await client.query(prompt)
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(f"[Critic] {block.text[:100]}...")
                    elif isinstance(block, ToolUseBlock):
                        print(f"[Critic] Tool Use: {block.name}")
    
    # 4. Run Normalization (The Fix Verification)
    print("\n--- Starting Normalization ---")
    # Using the tool handler directly as we aliased it in tools_impl.py or calling the decorated tool object
    # normalize_extractions is imported from tools.normalization_tools, which is an SdkMcpTool
    
    result = await normalize_extractions.handler({})
    print(f"Normalization Result: {result}")
    
    # Check for fields
    passed_norm = False
    for item in context.state.draft_extractions:
        if "therapy_rxnorm_ids" in item or "disease_efo_id" in item:
            passed_norm = True
            break
            
    if passed_norm:
        print("✅ Normalization SUCCESS: New fields found in draft items.")
    else:
        print("❌ Normalization WARNING: No new fields found (check API connectivity or matching).")

    # 5. Finalize
    print("\n--- Finalizing ---")
    await finalize_extraction.handler({})
    
    # 6. Save Final Result
    from config import OUTPUTS_DIR
    output_path = OUTPUTS_DIR / f"{saved_data['paper_id']}_final_verified.json"
    
    final_data = {
        "paper_id": saved_data['paper_id'],
        "extraction": {
            "evidence_items": context.state.final_extractions
        }
    }
    
    with open(output_path, "w") as f:
        json.dump(final_data, f, indent=2)
        
    print(f"🎉 FINAL OUTPUT SAVED: {output_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_critic_normalizer.py <path_to_extractor_output.json>")
        sys.exit(1)
    
    asyncio.run(run_critic_normalizer_test(sys.argv[1]))

