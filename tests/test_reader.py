
import asyncio
import json
import sys
import os
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))
# Add civic_extraction to path so 'import config' works (legacy support)
sys.path.insert(0, str(Path(__file__).parent.parent))

from context import set_current_context, CIViCContext, get_current_context
from client import CivicExtractionClient
from config import OUTPUTS_DIR

async def run_reader_test(pdf_path):
    """Run Reader agent and save checkpoint."""
    print(f"=== TESTING READER AGENT ===")
    
    input_path = Path(pdf_path)
    if not input_path.exists():
        print(f"❌ PDF not found: {pdf_path}")
        sys.exit(1)
        
    paper_id = input_path.parent.name
    print(f"Paper ID: {paper_id}")
    
    # 1. Setup Context
    context = CIViCContext()
    context.load_paper(paper_id)
    set_current_context(context)
    
    # 2. Run Reader
    client = CivicExtractionClient(verbose=True)
    
    print("\n--- Starting Reader Phase ---")
    await client.run_reader_phase()
    
    if not context.paper_content:
        print("❌ Reader failed to extract content.")
        sys.exit(1)
        
    print("\n✅ Reader Complete.")
    
    # 3. Save Checkpoint
    checkpoint_dir = OUTPUTS_DIR / "checkpoints" / paper_id
    checkpoint_dir.mkdir(parents=True, exist_ok=True)
    
    checkpoint_path = checkpoint_dir / "01_reader_output.json"
    
    output_data = {
        "paper_id": paper_id,
        "paper_content": context.paper_content
    }
    
    with open(checkpoint_path, "w") as f:
        json.dump(output_data, f, indent=2)
        
    print(f"💾 Checkpoint saved: {checkpoint_path}")
    print(f"➡️  Next step: python civic_extraction/tests/test_planner.py {checkpoint_path}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python test_reader.py <path_to_pdf>")
        sys.exit(1)
    
    asyncio.run(run_reader_test(sys.argv[1]))

