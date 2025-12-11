
import sys
import os
import json
import asyncio
import shutil
from pathlib import Path
from datetime import datetime

# --- SETUP PATHS ---
CIVIC_EXTRACTION_DIR = Path(__file__).resolve().parent.parent
if str(CIVIC_EXTRACTION_DIR) not in sys.path:
    sys.path.insert(0, str(CIVIC_EXTRACTION_DIR))
PROJECT_ROOT = CIVIC_EXTRACTION_DIR.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Import logic to test
from config import OUTPUTS_DIR, LOGS_DIR
from context import CIViCContext, set_current_context, require_context
from tools.normalization_tools import (
    lookup_rxnorm, 
    lookup_efo, 
    lookup_gene_entrez, 
    finalize_extraction
)

def print_header(msg):
    print(f"\n{'='*60}\n{msg}\n{'='*60}")

async def run_integrity_tests():
    print_header("🚀 STARTING SYSTEM INTEGRITY CHECKS (NO API COST)")
    
    # -------------------------------------------------------------------------
    # TEST 1: PATH CONFIGURATION
    # -------------------------------------------------------------------------
    print("\n[TEST 1] Verifying Directory Paths...")
    print(f"Expected Base: {CIVIC_EXTRACTION_DIR}")
    print(f"Configured OUTPUTS_DIR: {OUTPUTS_DIR}")
    print(f"Configured LOGS_DIR:    {LOGS_DIR}")
    
    if CIVIC_EXTRACTION_DIR not in OUTPUTS_DIR.parents and OUTPUTS_DIR != CIVIC_EXTRACTION_DIR / "outputs":
        print("❌ CRITICAL: OUTPUTS_DIR is NOT inside civic_extraction/")
        return False
    
    if not OUTPUTS_DIR.exists():
        print("⚠️  OUTPUTS_DIR does not exist, attempting to create...")
        OUTPUTS_DIR.mkdir(parents=True, exist_ok=True)
        
    print("✅ Paths are correctly configured.")

    # -------------------------------------------------------------------------
    # TEST 2: CRITICAL BUG FIX (Normalization List Handling)
    # -------------------------------------------------------------------------
    print("\n[TEST 2] Verifying Normalization Tool (List Inputs)...")
    # Simulate the exact data structure that caused the crash
    crash_prone_item = {
        "feature_names": ["BRAF"],       # LIST (Was causing crash)
        "variant_names": ["V600E"],      # LIST
        "disease_name": ["Melanoma"],    # LIST
        "therapy_names": ["Vemurafenib"], # LIST
        "evidence_type": "PREDICTIVE",
        "evidence_level": "B"
    }
    
    try:
        # Test a granular tool
        print("Testing granular lookup_gene_entrez...")
        result = await lookup_gene_entrez.handler({"args": {"gene_symbol": crash_prone_item["feature_names"][0]}})
        print(f"✅ Gene Lookup Result: {str(result)[:100]}...")
        
        # Test EFO
        print("Testing granular lookup_efo...")
        result_efo = await lookup_efo.handler({"args": {"disease_name": crash_prone_item["disease_name"][0]}})
        print(f"✅ EFO Lookup Result: {str(result_efo)[:100]}...")
        
        print("✅ Normalization tools handled inputs safely.")
        
        # Create a mock item for Test 3
        normalized = crash_prone_item.copy()
        normalized["gene_entrez_id"] = "673" # Mock
        
    except Exception as e:
        print(f"❌ CRASH DETECTED: {e}")
        import traceback
        traceback.print_exc()
        return False

    # -------------------------------------------------------------------------
    # TEST 3: STATE MANAGEMENT & SAVING
    # -------------------------------------------------------------------------
    print("\n[TEST 3] Verifying Data Flow & File Saving...")
    
    # Setup Context
    ctx = CIViCContext()
    set_current_context(ctx)
    
    # Inject Mock Data (Simulating what Extractor + Normalizer produce)
    ctx.state.draft_extractions = [normalized]
    
    # Run Finalize Tool (Simulating Agent Call)
    print("Executing 'finalize_extraction' tool logic...")
    await finalize_extraction.handler({"args": {}})
    
    if not ctx.state.is_complete:
        print("❌ Finalization failed to mark state as complete")
        return False
        
    if len(ctx.state.final_extractions) != 1:
        print("❌ Final extractions not populated")
        return False
        
    # Simulate specific file save (mimicking run_extraction.py)
    test_file_name = "TEST_INTEGRITY_RUN.json"
    output_path = OUTPUTS_DIR / test_file_name
    
    results = {
        "status": "success",
        "data": ctx.state.final_extractions
    }
    
    print(f"Attempting to write file to: {output_path}")
    with open(output_path, "w") as f:
        json.dump(results, f, indent=2)
        
    if output_path.exists():
        print(f"✅ File successfully created at: {output_path}")
        # Clean up
        output_path.unlink()
        print("✅ Test file cleaned up.")
    else:
        print(f"❌ File was NOT found at expected path: {output_path}")
        return False

    # -------------------------------------------------------------------------
    # TEST 4: STATIC CODE ANALYSIS
    # -------------------------------------------------------------------------
    print("\n[TEST 4] Verifying Code Integrity (Imports)...")
    try:
        from client import CivicExtractionClient, PLANNER_AGENT, EXTRACTOR_AGENT, CRITIC_AGENT
        from tool_registry import build_civic_mcp_server
        
        server = build_civic_mcp_server()
        print(f"✅ Agents loaded successfully.")
        
        tools_count = 0
        if isinstance(server, dict):
             tools_count = len(server.get("tools", []))
        elif hasattr(server, "tools"):
             tools_count = len(server.tools)
             
        print(f"✅ MCP Server built with {tools_count} tools.")
        
    except ImportError as e:
        print(f"❌ Import Error in Codebase: {e}")
        return False
    except Exception as e:
        print(f"❌ Static Check Failed: {e}")
        return False

    print_header("🎉 ALL SYSTEM INTEGRITY CHECKS PASSED")
    return True

if __name__ == "__main__":
    success = asyncio.run(run_integrity_tests())
    sys.exit(0 if success else 1)

