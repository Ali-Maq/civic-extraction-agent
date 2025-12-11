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

# Mock Logger
class MockLogger:
    def info(self, msg): print(f"[INFO] {msg}")
    def error(self, msg): print(f"[ERROR] {msg}")
    def debug(self, msg): print(f"[DEBUG] {msg}")

async def run_planner_test(paper_json_path):
    """Test the Planner agent using saved reader output."""
    print(f"=== TESTING PLANNER AGENT ===")
    print(f"Loading paper content from: {paper_json_path}")
    
    # 1. Load saved state
    with open(paper_json_path, 'r') as f:
        saved_data = json.load(f)
    
    # 2. Setup Context
    context = CIViCContext()
    
    # Mock the paper info minimally (avoid load_paper which needs images)
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
    # Re-generate text context (using the tool's helper would be better, but we can rely on the tool to do it or manually set it)
    from tools.paper_content_tools import _generate_paper_context_text
    context.paper_content_text = _generate_paper_context_text(context.paper_content)
    
    set_current_context(context)
    
    # 3. Setup Client options for Planner
    # We want to run JUST the planner. 
    # The Orchestrator usually delegates to it. 
    # We can invoke the Planner Agent directly if we construct the options right.
    
    # Import PLANNER_AGENT definition
    from client import PLANNER_AGENT
    from tool_registry import build_civic_mcp_server
    from config import PLANNER_MODEL
    
    server = build_civic_mcp_server()
    
    options = ClaudeAgentOptions(
        system_prompt=PLANNER_AGENT.prompt,
        mcp_servers={"civic_tools": server},
        allowed_tools=PLANNER_AGENT.tools,
        max_turns=5,
    )
    
    # 4. Run Planner
    # We send a user message stimulating the task
    prompt = "Analyze the paper content and create an extraction plan. Call 'get_paper_content' first."
    
    print("\n--- Starting Planner ---")
    async with ClaudeSDKClient(options=options) as client:
        # Wrap prompt in message structure if needed, or string is fine for simple query
        await client.query(prompt)
        async for message in client.receive_response():
            if isinstance(message, AssistantMessage):
                for block in message.content:
                    if isinstance(block, TextBlock):
                        print(f"[Planner] {block.text[:100]}...")
                    elif isinstance(block, ToolUseBlock):
                        print(f"[Planner] Tool Use: {block.name}")
    
    print("\n--- Test Complete ---")
    
    # Check if plan was saved
    if context.state.extraction_plan:
        print("✅ Plan saved successfully.")
        
        # Save Checkpoint
        from config import OUTPUTS_DIR
        paper_id = saved_data['paper_id']
        checkpoint_dir = OUTPUTS_DIR / "checkpoints" / paper_id
        checkpoint_dir.mkdir(parents=True, exist_ok=True)
        
        checkpoint_path = checkpoint_dir / "02_planner_output.json"
        
        # Merge previous state with new plan
        output_data = saved_data.copy()
        
        # Convert Pydantic model or dict
        if isinstance(context.state.extraction_plan, dict):
            plan_dict = context.state.extraction_plan
        elif hasattr(context.state.extraction_plan, "model_dump"):
            plan_dict = context.state.extraction_plan.model_dump()
        else:
            plan_dict = context.state.extraction_plan.__dict__
            
        output_data['plan'] = plan_dict
        
        with open(checkpoint_path, "w") as f:
            json.dump(output_data, f, indent=2, default=str)
            
        print(f"💾 Checkpoint saved: {checkpoint_path}")
        print(f"➡️  Next step: python civic_extraction/tests/test_extractor.py {checkpoint_path}")
        
    else:
        print("❌ No plan saved.")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_planner.py <path_to_extraction.json>")
        # Default to the one we just ran
        default_path = "outputs/00018_Bradly_2012_extraction.json"
        if os.path.exists(default_path):
            asyncio.run(run_planner_test(default_path))
        else:
            sys.exit(1)
    else:
        asyncio.run(run_planner_test(sys.argv[1]))

