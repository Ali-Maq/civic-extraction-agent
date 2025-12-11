import asyncio
import json
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
# Add civic_extraction to path so 'import config' works (legacy support)
sys.path.insert(0, str(Path(__file__).parent.parent))

from context import set_current_context, CIViCContext
from client import CivicExtractionClient
from tool_registry import ORCHESTRATOR_AND_SUBAGENT_TOOLS
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, AssistantMessage, TextBlock, ToolUseBlock
from context.state import ExtractionPlan

async def run_extractor_test(paper_json_path):
    """Test the Extractor agent using saved reader output and plan."""
    print(f"=== TESTING EXTRACTOR AGENT ===")
    print(f"Loading paper content from: {paper_json_path}")
    
    # 1. Load saved state
    with open(paper_json_path, 'r') as f:
        saved_data = json.load(f)
    
    # 2. Setup Context
    context = CIViCContext()
    try:
        context.load_paper(saved_data['paper_id'])
    except Exception as e:
        print(f"⚠️ Could not load paper folder: {e}")
        from context.state import PaperInfo
        context.paper = PaperInfo(
            paper_id=saved_data['paper_id'], 
            author="Unknown",
            year="2025",
            num_pages=10,
            pdf_path="mock.pdf"
        )
        print("   Using Mock PaperInfo.")
    
    # Inject saved content
    context.paper_content = saved_data['paper_content']
    from tools.paper_content_tools import _generate_paper_context_text
    context.paper_content_text = _generate_paper_context_text(context.paper_content)
    
    # Inject saved Plan (if available) or create a dummy one
    if 'plan' in saved_data and saved_data['plan']:
        plan_data = saved_data['plan']
        
        # Sanitize list fields
        for field in ["key_variants", "key_therapies", "key_diseases", "focus_sections"]:
            val = plan_data.get(field)
            if isinstance(val, str):
                # Try to parse or split
                if val.startswith("[") and val.endswith("]"):
                    try:
                        plan_data[field] = json.loads(val)
                    except:
                        plan_data[field] = [s.strip() for s in val.strip("[]").split(',')]
                else:
                    plan_data[field] = [s.strip() for s in val.split(',')]
            elif not val:
                plan_data[field] = []
                
        context.state.extraction_plan = ExtractionPlan(
            paper_type=plan_data.get('paper_type', 'UNKNOWN'),
            expected_items=plan_data.get('expected_items', 0),
            key_variants=plan_data.get('key_variants', []),
            key_therapies=plan_data.get('key_therapies', []),
            key_diseases=plan_data.get('key_diseases', []),
            focus_sections=plan_data.get('focus_sections', []),
            extraction_notes=plan_data.get('extraction_notes', '')
        )
        print("Injected existing plan.")
    else:
        # Dummy plan for testing if none exists
        print("No plan found, injecting dummy plan.")
        context.state.extraction_plan = ExtractionPlan(
            paper_type="PRIMARY",
            expected_items=1,
            key_variants=[],
            key_therapies=[],
            key_diseases=[],
            focus_sections=["Results", "Discussion"],
            extraction_notes="Dummy plan for testing"
        )

    set_current_context(context)
    
    # 3. Setup Client options for Extractor
    from client import EXTRACTOR_AGENT
    from tool_registry import build_civic_mcp_server
    from config import DEFAULT_MODEL
    
    server = build_civic_mcp_server()
    
    options = ClaudeAgentOptions(
        system_prompt=EXTRACTOR_AGENT.prompt,
        mcp_servers={"civic_tools": server},
        allowed_tools=EXTRACTOR_AGENT.tools,
        max_turns=15,
    )
    
    # 4. Run Extractor
    prompt = "Extract evidence items based on the plan. Call 'get_paper_content' and 'get_extraction_plan' first."
    
    print("\n--- Starting Extractor ---")
    async with ClaudeSDKClient(options=options) as client:
        await client.query(prompt)
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(f"[Extractor] {block.text[:100]}...")
                    elif isinstance(block, ToolUseBlock):
                        print(f"[Extractor] Tool Use: {block.name}")
    
    print("\n--- Test Complete ---")
    
    # Check extractions
    if context.state.draft_extractions:
        print(f"✅ Extracted {len(context.state.draft_extractions)} items.")
        
        # Save Checkpoint
        from config import OUTPUTS_DIR
        paper_id = saved_data['paper_id']
        checkpoint_dir = OUTPUTS_DIR / "checkpoints" / paper_id
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        checkpoint_path = checkpoint_dir / "03_extractor_output.json"
        
        # Merge previous state with new extractions
        output_data = saved_data.copy()
        output_data['extraction'] = {
            "draft_extractions": context.state.draft_extractions
        }
        
        with open(checkpoint_path, "w") as f:
            json.dump(output_data, f, indent=2)
            
        print(f"💾 Checkpoint saved: {checkpoint_path}")
        print(f"➡️  Next step: Run Critic (test_critic.py - to be implemented)")
        
    else:
        print("❌ No items extracted.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_extractor.py <path_to_extraction.json>")
        # Default to the one we just ran
        default_path = "outputs/00018_Bradly_2012_extraction.json"
        if os.path.exists(default_path):
            asyncio.run(run_extractor_test(default_path))
        else:
            sys.exit(1)
    else:
        asyncio.run(run_extractor_test(sys.argv[1]))

