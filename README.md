# OncoCITE — Claude Agent SDK implementation

Companion code for the OncoCITE manuscript (Research Square preprint,
[DOI 10.21203/rs.3.rs-9160944/v1](https://doi.org/10.21203/rs.3.rs-9160944/v1)):
a multi-agent AI system for source-grounded extraction and harmonization
of clinical genomic evidence from full-text oncology publications.

This repository is the **primary (Claude Agent SDK)** implementation
referenced in Section 6 (Code Availability) of the manuscript. All
extraction and validation agents run Claude 3.5 Sonnet
(`claude-3-5-sonnet-20241022`) with deterministic inference settings
(`temperature=0.0`, `top_p=1.0`, fixed seed per Supplementary Note S3.4).
A sibling implementation built on LangChain / LangGraph (which targets
Fireworks AI GLM-4 / Qwen3-VL) lives at
[Ali-Maq/oncocite-langchain](https://github.com/Ali-Maq/oncocite-langchain).

## Features

- **Six-agent "Reader-first" architecture** — Reader → Orchestrator →
  Planner → Extractor → Critic → Normalizer (Section 2.2, Supplementary
  Figure S2)
- **MCP server** — all 22 paper-spec tools (Supplementary Table S15)
  exposed through `claude_agent_sdk.create_sdk_mcp_server`, defined in
  [`tool_registry.py`](tool_registry.py)
- **Source-grounded evidence** — verbatim quotes, page references,
  0–1 confidence scores for every extracted item
- **45-field JSON schema** — 25 Tier-1 extraction + 20 Tier-2
  normalization fields (Supplementary Tables S17 and S18)
- **Ontology normalization** — MyGene, MyVariant, EBI OLS
  (DOID / NCIt / EFO / HPO), RxNorm, ClinicalTrials.gov (Supplementary
  Table S21)
- **Interactive web UI** — React 18 + Express.js viewer with side-by-side
  PDF / evidence-card display and a knowledge-graph visualization
  (Supplementary Figure S3)

## Quick start — extraction pipeline

Requires Python 3.11+ and an Anthropic API key.

```bash
git clone https://github.com/Ali-Maq/civic-extraction-agent.git
cd civic-extraction-agent

pip install -r requirements.txt

cp .env.example .env   # edit ANTHROPIC_API_KEY=sk-ant-...

# Extract one of the bundled validation papers
python run_extraction.py \
    --input data/papers/PMID_18528420/PMID_18528420.pdf \
    --output outputs/
```

Outputs land in `outputs/{paper_id}_extraction.json` with the 45-field
evidence-item schema documented in Supplementary Tables S17 and S18.

## Quick start — web UI (local)

```bash
# Build and run both services (API + frontend) in Docker
docker compose up -d

# Visit the viewer
open http://localhost:8080
```

See [`DEPLOYMENT.md`](DEPLOYMENT.md) for AWS deployment details
(containerized on EC2 + ECR + EBS per Supplementary Figure S5).

## Reproducing the validation metrics

`data/papers/` bundles the full 15-paper validation corpus:

- 10 retrospective Multiple Myeloma papers (`PMID_*`) — CIViC-indexed,
  used for the three-way validation framework in Section 2.6 and Supp
  Note S1
- 5 prospective-application papers — Da Vià 2023 (Nature Medicine,
  `s41591-023-02491-5`), Derrien 2023 (Nature Cancer,
  `s43018-023-00625-9`), Dutta 2024 (Blood Neoplasia), Restrepo 2022
  (JCO Precision Oncology), Elnaggar 2022 (J Hematol Oncol) — used for
  the prospective application in Section 2.8

Outputs and checkpoints for each paper live under `outputs/` and
`outputs/checkpoints/`. Per-paper extraction metrics are summarized in
Supplementary Table S4.

## Repository layout

```
civic-extraction-agent/
├── run_extraction.py        # Extraction pipeline CLI
├── client.py                # Programmatic Claude Agent SDK client
├── tool_registry.py         # MCP server with the 22 tools from Table S15
├── tools/                   # Tool implementations
├── config/                  # Settings and path resolution
├── normalization/           # Variant annotators and ontology lookup logic
├── schemas/                 # Pydantic models for the 45-field evidence schema
├── hooks/                   # Session logging / audit trail
├── scripts/                 # Batch runners, CIViC data loaders, evaluation
├── frontend/                # React 18 + Vite 4 viewer (Supplementary Note S4)
├── data/papers/             # 15-paper validation corpus
├── outputs/                 # Per-paper extraction outputs + staged checkpoints
├── final_papers/            # Manuscript source (LaTeX)
├── Dockerfile, docker-compose.yml, deployment/   # Containerized deployment
├── DEPLOYMENT.md            # AWS / EC2 deployment runbook
├── requirements.txt         # Pinned dependencies
└── pyproject.toml
```

## MCP server

The 22-tool MCP server is declared in [`tool_registry.py`](tool_registry.py)
through `claude_agent_sdk.create_sdk_mcp_server`. Agents call into the
server over the Claude Agent SDK's internal MCP transport; external
MCP-compatible clients can also attach by launching the server process
directly. See Supplementary Table S15 for the complete tool list and
agent assignments.

## Live demonstration

A public demo instance referenced in Supplementary Figure S5 is hosted
at **http://13.217.205.13** (EC2 `t4g.micro`, `us-east-1`). The
instance is intended for reviewer access and is not a production
service.

## Normalized CIViC database (11,316 items, 45 fields each)

The full normalized CIViC corpus referenced in Section 2.4 and Section 5
of the manuscript ships as a release asset on the `v1.0-preprint` tag:

- **Download:** [`civic_normalized_evidence_v1.jsonl.gz`](https://github.com/Ali-Maq/civic-extraction-agent/releases/download/v1.0-preprint/civic_normalized_evidence_v1.jsonl.gz) (2.9 MB → 24 MB uncompressed)
- **Coverage report:** [`civic_normalized_coverage_report.md`](https://github.com/Ali-Maq/civic-extraction-agent/releases/download/v1.0-preprint/civic_normalized_coverage_report.md) — per-field resolution matrix (Supp Table S24 analogue)

The artifact was produced by the `scripts/normalize_civic_corpus.py`
script in the sibling [`oncocite-langchain`](https://github.com/Ali-Maq/oncocite-langchain)
repository; the JSONL schema (25 Tier-1 + 20 Tier-2 fields) is the same
in both implementations.

## Manuscript snapshot

The analyses reported in the manuscript correspond to release
**`v1.0-preprint`**, commit
[`e174841`](https://github.com/Ali-Maq/civic-extraction-agent/commit/e1748416374f5f0c43cf25ae28b64ee624a10d1a).

## Citation

```
Quidwai M., Thibaud S., Shasha D., Jagannath S., Parekh S., Laganà A.
OncoCITE: Multimodal Multi-Agent Reconstruction of Clinical Oncology
Knowledge Bases from Scientific Literature. Research Square (2026).
DOI: 10.21203/rs.3.rs-9160944/v1
```

## License

[MIT](LICENSE) — matching Section 6 (Code Availability) of the manuscript.
