# CIViC Evidence Extraction Agent

A specialized multi-agent system for extracting clinical evidence from scientific literature, powered by the **Claude Agent SDK**.

This system implements a **"Reader-First" Architecture**, separating visual document understanding from clinical logic to maximize accuracy and cost-efficiency.

---

## 🏗 System Architecture

The extraction pipeline operates in two distinct phases:

### Phase 1: The Reader (Visual Processing)
**Goal:** Convert the raw PDF (images) into a structured "Single Source of Truth".

*   **Agent:** `Reader` (Claude 3.5 Sonnet / Opus)
*   **Input:** Full PDF rendered as high-resolution images (injected directly into context).
*   **Action:** Reads every page, analyzing text, tables, figures, and footnotes simultaneously.
*   **Output:** A structured JSON object containing:
    *   Metadata (Title, Authors, Journal, Year)
    *   Paper Type (Primary, Review, etc.)
    *   Full Text Sections
    *   **Structured Tables** (Rows, headers, captions)
    *   **Figure Data** (Captions, descriptions, visible stats)
    *   **Key Statistics** (P-values, HR, OR, CI, sample sizes)
    *   **Entities** (Genes, Variants, Diseases, Therapies mentioned)

### Phase 2: The Orchestrator (Clinical Logic)
**Goal:** Extract, validate, and normalize evidence items using the Reader's output.

*   **Coordinator:** `Orchestrator` Agent
*   **Context:** Works **exclusively** from the text/JSON extracted by the Reader (no image re-reading).
*   **Sub-Agents:**
    1.  **Planner:** Analyzes the paper content to determine *if* it is relevant and *what* specific variants/diseases to target. Creates an `ExtractionPlan`.
    2.  **Extractor:** Follows the plan to identify candidate evidence items. It must quote verbatim text and capture all 8 required CIViC fields.
    3.  **Critic:** Validates every candidate item against the text. Checks for logical consistency, hallucination, and missing fields. Can reject items or request revisions.
    4.  **Normalizer:** Standardizes entities (Drugs, Diseases, Genes) to ontologies (RxNorm, EFO, NCIt). Uses intelligent error handling to fix typos and find synonyms using granular lookup tools.

---

## 🌐 Beyond CIViC: Expanded Clinical Intelligence

We have extended this system beyond basic CIViC extraction to become a general clinical curation assistant, integrating a **"Hybrid Tooling"** approach inspired by ToolUniverse.

*   **Plan:** See [`docs/TOOLUNIVERSE_INTEGRATION.md`](docs/TOOLUNIVERSE_INTEGRATION.md) for the strategic roadmap.
*   **Status:** **Core Normalization Integrated** (Phase 1 Complete) & **Robustness Enhanced** (Phase 2 Complete).
*   **Implemented Capabilities:**
    *   **✅ RxNorm:** Drug normalization and RXCUI resolution (with fuzzy matching for typos).
    *   **✅ EFO (Experimental Factor Ontology):** Disease/Phenotype normalization (with wildcard search).
    *   **✅ MedDRA / FAERS:** Drug safety profiles and adverse event reporting (via OpenFDA).
    *   **✅ MyGene / MyVariant:** Gene and Variant normalization.
    *   **✅ ClinicalTrials.gov:** Trial title, status, and phase enrichment (API v2).
    *   **✅ HPO (Human Phenotype Ontology):** Phenotype normalization via EBI OLS.
    *   **✅ NCIt Factors & Therapies:** Normalization for non-gene entities and drugs (robust lookup).
    *   **✅ ID Conversion:** Automatic PMCID resolution for PMIDs via NCBI API.
*   **Upcoming:**
    *   **SNOMED CT:** Detailed clinical terminology (Requires Licensing).
    *   **Synthesis Agent:** Conflict resolution and negative evidence detection.

---

## 🛠 Tech Stack

*   **Framework:** `claude-agent-sdk` (Official Anthropic Python SDK)
*   **Protocol:** Model Context Protocol (MCP) for tool definitions.
*   **Language:** Python 3.11+
*   **PDF Engine:** `PyMuPDF` (fitz) for rendering pages.
*   **Normalization:** Asynchronous calls (`aiohttp`) to MyGene.info, MyVariant.info, RxNorm, EFO (OLS), and OpenFDA (FAERS).

---

## 📂 Project Structure

```text
civic_extraction/
├── agents/                 # Agent Definitions & Prompts
│   ├── reader.py           # Phase 1: Visual Extraction
│   ├── orchestrator.py     # Phase 2: Coordination
│   ├── planner.py          # Strategy & Relevance
│   ├── extractor.py        # Evidence Identification
│   └── critic.py           # Validation & Quality Control
├── client.py               # Main SDK Client & Loop Management
├── context/                # State Management
│   ├── civic_context.py    # Global Context & Paper Loader
│   └── state.py            # Data Classes (PaperInfo, EvidenceItem)
├── tools/                  # MCP Tool Implementations
│   ├── paper_tools.py      # PDF rendering
│   ├── paper_content_tools.py # Reader output storage
│   ├── extraction_tools.py # CRUD for evidence items
│   ├── validation_tools.py # Logic checks
│   └── normalization_tools.py # External API lookups
├── tool_registry.py        # Central MCP Server Builder
└── scripts/
    └── run_extraction.py   # CLI Entry Point
```

---

## 🚀 Usage

### Setup
1.  **Environment:**
    The project includes a pre-configured virtual environment in `civic_extraction/.venv`.
    ```bash
    # Activate the environment
    source civic_extraction/.venv/bin/activate
    
    # Or creating a new one if needed:
    # python3.11 -m venv civic_extraction/.venv
    # source civic_extraction/.venv/bin/activate
    # pip install -e .
    ```
2.  **Keys:** Ensure `ANTHROPIC_API_KEY` is set in your environment.

### Running Extraction
Run the pipeline on a specific paper (PDF or folder). The script now supports **Smart Resume**: if a Reader checkpoint exists, it will skip the expensive image processing step.

```bash
# Using a direct PDF path
python civic_extraction/scripts/run_extraction.py /path/to/paper.pdf

# Using a CIViC Paper ID (folder in data/papers/)
python civic_extraction/scripts/run_extraction.py 00085_Hodi_2013
```

### Checkpoints
The system saves intermediate states to `civic_extraction/outputs/checkpoints/{paper_id}/`:
*   `01_reader_output.json`: Full extracted text/tables (Expensive to re-run).
*   The main script automatically detects and loads `01_reader_output.json`.

### Output
Results are saved to `civic_extraction/outputs/{paper_id}_extraction.json`.
The output includes:
*   `paper_info`: Metadata
*   `paper_content`: The raw extraction from the Reader.
*   `extraction`: Final list of evidence items.
*   `plan`: The strategy used.
*   `final_critique`: The Critic's final assessment.

---

## 🧪 Testing & Verification

We use isolated unit tests and "zero-cost" verification scripts.

### Zero-Cost System Integrity Test
Verifies paths, tool definitions, and file saving without calling the LLM API.
```bash
python civic_extraction/tests/test_system_integrity.py
```

### Robustness Test
Verifies API lookup resilience against typos and missing IDs.
```bash
python civic_extraction/tests/test_robustness.py
```

### Modular Tests (Step-by-Step)
You can run agents individually using the checkpoint system:

```bash
# Step 1: Reader (Saves checkpoint 01)
python civic_extraction/tests/test_reader.py /path/to/paper.pdf

# Step 2: Planner (Loads 01, Saves 02)
python civic_extraction/tests/test_planner.py civic_extraction/outputs/checkpoints/{paper_id}/01_reader_output.json

# Step 3: Extractor (Loads 02, Saves 03)
python civic_extraction/tests/test_extractor.py civic_extraction/outputs/checkpoints/{paper_id}/02_planner_output.json

# Step 4: Critic & Normalizer (Loads 03, Saves Final)
python civic_extraction/tests/test_critic_normalizer.py civic_extraction/outputs/checkpoints/{paper_id}/03_extractor_output.json
```

---

## 🧠 Learnings & Fixes (Recent Workflow)

*   **Robustness:** Implemented fuzzy search and wildcard matching for OLS (EFO, NCIt) and RxNorm to handle extractor typos (e.g., "Mellanoma" vs "Melanoma").
*   **List vs String Handling:** Fixed a critical issue where the Extractor returned lists (e.g., `["Mutation"]`) for fields expected to be strings. `normalization_tools.py` now robustly handles both types.
*   **Checkpointing:** Essential for cost management. The Reader step is expensive; running it once and reusing the output via checkpoints is the standard workflow.
*   **Silent Failures:** Added explicit `traceback` logging in normalization to catch errors that were previously swallowed, ensuring we can debug API connectivity issues effectively.
*   **Absolute Paths:** Enforced absolute paths in `settings.py` to prevent output files from being scattered in wrong directories.
