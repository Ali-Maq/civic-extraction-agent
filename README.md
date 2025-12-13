# CIViC Evidence Extraction Agent

A specialized multi-agent system for extracting clinical evidence from scientific literature, powered by the **Claude Agent SDK**.

This system implements a **"Reader-First" Architecture** with **Agentic Normalization**, separating visual document understanding from clinical logic and ontology standardization to maximize accuracy and auditability.

---

## 🏗 System Architecture

The extraction pipeline operates in three distinct phases:

### Phase 1: The Reader (Visual Processing)
**Goal:** Convert the raw PDF (images) into a structured "Single Source of Truth".

*   **Agent:** `Reader` (Claude 3.5 Sonnet / Opus)
*   **Strategy:** **Chunked Image Injection**. Images are sent in batches (2 pages/turn) to manage token limits and avoid pipe errors.
*   **Input:** Full PDF rendered as high-resolution images.
*   **Action:** Reads every page, analyzing text, tables, figures, and footnotes simultaneously.
*   **Output:** A structured JSON object containing metadata, full text, structured tables, figure captions, and key statistics.
*   **Checkpoint:** Saves to `01_reader_output.json`.

### Phase 2: The Orchestrator (Clinical Logic)
**Goal:** Extract and validate evidence items using the Reader's output.

*   **Coordinator:** `Orchestrator` Agent
*   **Context:** Works **exclusively** from the text/JSON extracted by the Reader (no image re-reading).
*   **Sub-Agents:**
    1.  **Planner:** Analyzes content to determine relevance and extraction strategy. Saves `02_planner_output.json`.
    2.  **Extractor:** Identifies candidate evidence items with 8 required fields and **Reasoning Fields** (verbatim quotes, page numbers). Saves `03_extractor_output.json`.
    3.  **Critic:** Validates every item against the text. Checks for hallucination and logic. Rejects items requiring revision.

### Phase 3: Agentic Normalization
**Goal:** Standardize entities to Global Ontologies (RxNorm, EFO, NCIt).

*   **Agent:** `Normalizer` Agent
*   **Method:** **Agentic Loop** (not just a script). The agent actively uses tools to lookup IDs, handles errors (typos, synonyms), and retries if needed.
*   **Tools:** Granular lookups (`lookup_rxnorm`, `lookup_efo`, `lookup_gene_entrez`, `lookup_clinical_trial`, etc.).
*   **Output:** Final standardized JSON with Tier 2 fields (IDs). Saves `04_normalization_output.json` and final `{paper_id}_extraction.json`.

---

## 🌐 Beyond CIViC: Expanded Clinical Intelligence

We have extended this system to support a comprehensive "Clinical Curation Assistant" role.

*   **Capabilities:**
    *   **✅ RxNorm:** Drug normalization and RXCUI resolution.
    *   **✅ EFO:** Disease/Phenotype normalization.
    *   **✅ FAERS:** Drug safety profiles (adverse events).
    *   **✅ MyGene / MyVariant:** Gene and Variant normalization.
    *   **✅ ClinicalTrials.gov:** Trial metadata enrichment.
    *   **✅ NCIt:** NCI Thesaurus for therapies and factors.
    *   **✅ ID Conversion:** PMCID resolution.

---

## 📂 Project Structure

```text
civic_extraction/
├── client.py               # MAIN ENTRANCE: Defines Client & All Agents (Reader, Planner, etc.)
├── context/                # State Management
│   ├── civic_context.py    # Global Context & Paper Loader
│   └── state.py            # Data Classes (PaperInfo, EvidenceItem, ExtractionState)
├── tools/                  # MCP Tool Implementations
│   ├── normalization_tools.py # External API lookups (RxNorm, EFO, etc.)
│   ├── extraction_tools.py # CRUD for evidence items & Checkpointing
│   ├── paper_content_tools.py # Reader output storage
│   └── validation_tools.py # Logic checks
├── tool_registry.py        # Central MCP Server Builder
├── schemas/                # Pydantic Models
│   └── evidence_item.py    # Strict Schema for Output & Normalization
├── scripts/
│   └── run_extraction.py   # CLI Entry Point
└── tests/                  # Verification Suite
    ├── test_system_integrity.py # Zero-cost setup check
    ├── test_normalizer_agent.py # Agentic normalization test
    └── test_orchestrator_full.py # Full integration test
```

---

## 🚀 Usage

### Prerequisites

**Python Version:** This project requires **Python 3.11 or higher**. The `claude-agent-sdk` requires Python >=3.10, but we recommend 3.11 for compatibility.

```bash
# Check your Python version
python3.11 --version  # Should show Python 3.11.x or higher
```

### Setup

1. **Create and activate a virtual environment:**

```bash
# Create venv with Python 3.11
python3.11 -m venv .venv

# Activate the environment
source .venv/bin/activate  # On macOS/Linux
# OR
.venv\Scripts\activate  # On Windows
```

2. **Install dependencies:**

```bash
# Install from pyproject.toml
pip install -e .

# Or install core dependencies manually
pip install claude-agent-sdk==0.1.14 PyMuPDF aiohttp pydantic python-dotenv
```

3. **Configuration (.env):**
   Create a `.env` file in the project root directory with your API keys.
   
   ```bash
   # .env example
   ANTHROPIC_API_KEY=sk-ant-api03-...
   # Optional settings
   DEFAULT_MODEL=claude-3-5-sonnet-20241022
   MAX_ITERATIONS=3
   MAX_TURNS=50
   ```

### Running Extraction

**Important:** The script expects a `paper_id` (not a full PDF path) and uses the `PAPERS_DIR` environment variable to locate PDFs.

```bash
# Set PAPERS_DIR to your papers directory
export PAPERS_DIR=/path/to/your/papers/directory

# Run extraction on a paper (using paper_id derived from PDF filename)
python3.11 scripts/run_extraction.py <paper_id>

# Example: If your PDF is at data/papers/Dutta_et_al-2024-Blood_Neoplasia.pdf
export PAPERS_DIR=$(pwd)/data/papers
python3.11 scripts/run_extraction.py Dutta_et_al-2024-Blood_Neoplasia
```

**Paper ID derivation & checkpoints:** 
- The `paper_id` is derived from the PDF filename (without extension)
- If the PDF is in a subfolder (e.g., `data/papers/s41591-023-02491-5/s41591-023-02491-5.pdf`), the `paper_id` is `s41591-023-02491-5`
- Each run creates per-paper checkpoints under `outputs/checkpoints/<paper_id>/01-04_*.json`
- Final results are saved to `outputs/<paper_id>_extraction.json`
- The system supports **Smart Resume**: if a Reader checkpoint exists, it skips the expensive image reading phase

**Context Normalization Fix:**
The system now automatically normalizes legacy Reader output formats (where `sections` might be a string instead of a structured list). This ensures the full paper text is always available to downstream agents, preventing "abstract-only" extraction failures.

### Outputs
Results are saved to `civic_extraction/outputs/{paper_id}_extraction.json`.

---

## 🧠 Learnings & Fixes (Recent Workflow)

*   **Content Filter Mitigation:** The Reader agent now uses a "Succinct Acknowledgment" strategy ("Received Part X") during image injection. This prevents the LLM from generating long summaries that might inadvertently trigger safety filters before the final extraction step.
*   **Agentic Normalization:** We moved from a "batch tool" to a dedicated **Normalizer Agent**. This allows the LLM to "think" about failed lookups (e.g., trying "Vemurafenib" if "Zelboraf" fails) and retry, significantly improving ID coverage.
*   **Schema Hardening:** The `EvidenceItem` schema was updated to explicitly support normalized fields (`gene_id`, `disease_id`, `therapy_ids`) and their aliases, ensuring data isn't silently stripped during validation.
*   **Checkpointing:** Essential for cost management. Checkpoints (`01`...`04`) allow restarting from any phase without re-spending tokens on previous steps.
*   **SDK pinning:** The public `claude-agent-sdk` tops out at `0.1.14` (no 1.x on PyPI). We pin to that version in `pyproject.toml` to match the runtime.
