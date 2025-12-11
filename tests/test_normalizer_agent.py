
import asyncio
import json
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
# Add civic_extraction to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from context import CIViCContext, set_current_context
from client import CivicExtractionClient
from config import OUTPUTS_DIR
from schemas.extraction_result import ExtractionPlan

from civic_extraction.tools.paper_content_tools import _generate_paper_context_text

async def run_normalizer_agent_test(extractor_output_path: str):
    print(f"=== TESTING NORMALIZER AGENT ===")
    print(f"Loading extractor output from: {extractor_output_path}")

    # Load checkpoint data
    with open(extractor_output_path, "r") as f:
        checkpoint_data = json.load(f)

    paper_id = checkpoint_data["paper_id"]
    
    # Reconstruct context state
    context = CIViCContext()
    context.paper_content = checkpoint_data.get("paper_content")
    
    # Robustly get paper_content_text
    if checkpoint_data.get("paper_content_text"):
        context.paper_content_text = checkpoint_data["paper_content_text"]
    elif context.paper_content:
        print("Regenerating paper_content_text from paper_content...")
        context.paper_content_text = _generate_paper_context_text(context.paper_content)
    else:
        context.paper_content_text = ""

    context.state.paper_info = checkpoint_data.get("paper_info")
    
    # Map 'plan' (from JSON) to 'extraction_plan' (dataclass)
    # The extraction_plan dataclass expects 'paper_type' and 'expected_items'
    plan_data = checkpoint_data.get("plan") or checkpoint_data.get("extraction_plan") or {}
    
    # Ensure required fields for ExtractionPlan
    if "paper_type" not in plan_data:
        plan_data["paper_type"] = "PRIMARY" # Default
    if "expected_items" not in plan_data:
        plan_data["expected_items"] = 0
    
    # Sanitize list fields that might be strings
    for field in ["key_variants", "key_therapies", "key_diseases", "focus_sections"]:
        val = plan_data.get(field)
        if isinstance(val, str):
            plan_data[field] = [s.strip() for s in val.split(',')]
        elif not val:
            plan_data[field] = []
        
    context.state.extraction_plan = ExtractionPlan(**plan_data)
    
    # Correctly load draft_extractions from nested 'extraction' key if present
    drafts = checkpoint_data.get("draft_extractions")
    if not drafts:
        drafts = checkpoint_data.get("extraction", {}).get("draft_extractions", [])
        
    context.state.draft_extractions = drafts
    
    # Ensure no previous final extractions interfere
    context.state.final_extractions = []
    
    set_current_context(context)

    print(f"Loaded {len(context.state.draft_extractions)} draft items.")
    
    # Print a sample draft item for reference
    if context.state.draft_extractions:
        print(f"Sample Draft Item [0]: {context.state.draft_extractions[0].get('variant_names')} / {context.state.draft_extractions[0].get('therapy_names')}")

    # Initialize Client
    client = CivicExtractionClient(verbose=True)

    # --- Starting Normalizer ---
    print("\n--- Starting Normalizer Agent ---")
    # We instruct the Orchestrator to delegate immediately to the Normalizer
    # Note: In the real flow, this happens after Critic approval.
    prompt = "Skip other steps. Delegate to 'normalizer' immediately to standardize the current draft extractions."
    
    # We use the orchestrator phase options, which includes the normalizer sub-agent
    options = client._create_options("orchestrator")
    
    # Custom run loop to target just the normalizer logic
    from claude_agent_sdk import ClaudeSDKClient
    async with ClaudeSDKClient(options=options) as agent_client:
        print(f"[Test] Sending prompt: {prompt}")
        await agent_client.query(prompt)
        async for message in agent_client.receive_response():
            await client._process_message(message, "Orchestrator/Normalizer")

    # Verify Results
    print("\n--- Verification ---")
    
    # Check if final_extractions are populated (Normalizer calls finalize_extraction which does this)
    if context.state.final_extractions:
        print(f"✅ Final Extractions: {len(context.state.final_extractions)}")
        
        # Check for normalized fields in the first item
        item = context.state.final_extractions[0]
        print("\n--- Normalized Item [0] Fields ---")
        tier2_fields = [
            "gene_entrez_ids", "disease_efo_id", "therapy_ncit_ids", 
            "therapy_rxnorm_ids", "source_pmcid", "drug_safety_profile"
        ]
        found_fields = []
        for field in tier2_fields:
            val = item.get(field)
            if val:
                print(f"  - {field}: {val}")
                found_fields.append(field)
            else:
                print(f"  - {field}: [MISSING]")
        
        if len(found_fields) >= 3:
             print("✅ Normalizer successfully enriched items!")
        else:
             print("⚠️ Normalizer ran but might have missed some lookups.")
             
        # Save output
        output_path = OUTPUTS_DIR / f"{paper_id}_agentic_normalized.json"
        with open(output_path, "w") as f:
            json.dump({
                "paper_id": paper_id,
                "evidence_items": context.state.final_extractions
            }, f, indent=2, default=str)
        print(f"Saved to: {output_path}")
        
    else:
        print("❌ Normalizer FAILED to finalize extractions (no final items found).")
        # Check draft extractions to see if they were modified at least
        if context.state.draft_extractions:
             item = context.state.draft_extractions[0]
             if item.get("gene_entrez_ids"):
                 print("⚠️ Draft items WERE modified but finalize_extraction wasn't called.")
             else:
                 print("❌ Draft items were NOT modified.")

    sys.exit(0)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_normalizer_agent.py <path_to_extractor_output_json>")
        sys.exit(1)
    asyncio.run(run_normalizer_agent_test(sys.argv[1]))

