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

---

## 🛠 Tech Stack

*   **Framework:** `claude-agent-sdk` (Official Anthropic Python SDK)
*   **Protocol:** Model Context Protocol (MCP) for tool definitions.
*   **Language:** Python 3.11+
*   **PDF Engine:** `PyMuPDF` (fitz) for rendering pages.
*   **Normalization:** Asynchronous calls to MyGene.info, MyVariant.info, and OLS.

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
    ```bash
    python3.11 -m venv .venv
    source .venv/bin/activate
    pip install -e .
    ```
2.  **Keys:** Ensure `ANTHROPIC_API_KEY` is set in your environment.

### Running Extraction
Run the pipeline on a specific paper (PDF or folder).

```bash
# Using a direct PDF path
python civic_extraction/scripts/run_extraction.py /path/to/paper.pdf

# Using a CIViC Paper ID (folder in data/papers/)
python civic_extraction/scripts/run_extraction.py 00085_Hodi_2013
```

### Output
Results are saved to `outputs/{paper_id}_extraction.json`.
The output includes:
*   `paper_info`: Metadata
*   `paper_content`: The raw extraction from the Reader.
*   `extraction`: Final list of evidence items.
*   `plan`: The strategy used.
*   `final_critique`: The Critic's final assessment.

---

## 🧪 Testing

We use isolated unit tests to verify agent logic without running the full pipeline every time.

```bash
# Test Planner (requires a saved extraction JSON)
python civic_extraction/tests/test_planner.py outputs/00085_Hodi_2013_extraction.json

# Test Extractor
python civic_extraction/tests/test_extractor.py outputs/00085_Hodi_2013_extraction.json
```

