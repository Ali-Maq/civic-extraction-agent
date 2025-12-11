
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
from tools.paper_content_tools import _generate_paper_context_text

async def run_full_orchestration_test(reader_checkpoint_path: str):
    print(f"=== TESTING FULL ORCHESTRATION (Phase 2) ===")
    print(f"Loading Reader checkpoint from: {reader_checkpoint_path}")

    # Load checkpoint data
    with open(reader_checkpoint_path, "r") as f:
        checkpoint_data = json.load(f)

    paper_id = checkpoint_data["paper_id"]
    
    # Reconstruct context state
    context = CIViCContext()
    context.paper_content = checkpoint_data["paper_content"]
    
    # Robustly get paper_content_text
    if checkpoint_data.get("paper_content_text"):
        context.paper_content_text = checkpoint_data["paper_content_text"]
    elif context.paper_content:
        print("Regenerating paper_content_text from paper_content...")
        context.paper_content_text = _generate_paper_context_text(context.paper_content)
    else:
        context.paper_content_text = ""
        
    context.state.paper_info = checkpoint_data.get("paper_info")
    
    set_current_context(context)
    
    print(f"Paper Context Loaded. Title: {context.paper_content.get('title')[:50]}...")

    # Initialize Client
    client = CivicExtractionClient(verbose=True)

    # --- Run Orchestrator Phase ---
    print("\n--- Starting Phase 2: Orchestrator ---")
    # This will trigger Planner -> Extractor -> Critic -> Normalizer
    await client.run_orchestrator_phase()

    # Verify Results
    print("\n--- Verification ---")
    
    if context.state.final_extractions:
        print(f"✅ Final Extractions: {len(context.state.final_extractions)}")
        
        # Check for normalized fields in the first item
        item = context.state.final_extractions[0]
        print("\n--- Normalized Item [0] Fields ---")
        # Define field aliases to check
        field_checks = {
            "gene_entrez_ids": ["gene_entrez_ids", "gene_entrez_id"],
            "disease_efo_id": ["disease_efo_id"],
            "therapy_ncit_ids": ["therapy_ncit_ids", "therapy_ncit_id"],
            "therapy_rxnorm_ids": ["therapy_rxnorm_ids", "therapy_rxcui"],
            "source_pmcid": ["source_pmcid"],
            "drug_safety_profile": ["drug_safety_profile", "therapy_safety_profile"]
        }
        
        found_fields = []
        for label, aliases in field_checks.items():
            val = None
            found_alias = None
            for alias in aliases:
                val = item.get(alias)
                if val:
                    found_alias = alias
                    break
            
            if val:
                print(f"  - {label} ({found_alias}): {str(val)[:50]}...")
                found_fields.append(label)
            else:
                print(f"  - {label}: [MISSING]")
        
        # Save output
        output_path = OUTPUTS_DIR / f"{paper_id}_full_orchestration_test.json"
        with open(output_path, "w") as f:
            json.dump({
                "paper_id": paper_id,
                "evidence_items": context.state.final_extractions
            }, f, indent=2, default=str)
        print(f"Saved to: {output_path}")
        
    else:
        print("❌ Orchestration FAILED to finalize extractions (no final items found).")

    sys.exit(0)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_orchestrator_full.py <path_to_reader_checkpoint_json>")
        sys.exit(1)
    asyncio.run(run_full_orchestration_test(sys.argv[1]))

