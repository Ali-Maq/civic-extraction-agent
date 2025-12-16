# OncoCITE Paper: Complete Section Overview

## Quick Navigation

| File | Section | Figures/Tables | Key Inputs |
|------|---------|---------------|------------|
| `01_title_authors.tex` | Title & Authors | None | Author list, affiliations |
| `02_abstract.tex` | Abstract | None | All metrics |
| `03_introduction.tex` | Introduction | **Table 1** | Database stats, clinical workflow data |
| `04_results_2.1_data_sources.tex` | Results 2.1 | None | Dataset sizes, dictionary counts |
| `05_results_2.2_react_extraction.tex` | Results 2.2 | **Figure 1** | Precision/recall, processing speed |
| `06_results_2.3_gprc5d_case.tex` | Results 2.3 | None (→Supp) | 15 variants, 3 categories |
| `07_results_2.4_nl_to_sql.tex` | Results 2.4 | **Figure 2** | Accuracy, baselines, latency |
| `08_results_2.5_knowledge_interface.tex` | Results 2.5 | **Figure 3** | Success rates, canonicalization |
| `09_discussion.tex` | Discussion | None | Synthesis of results |
| `10_back_matter.tex` | Declarations | None | Funding, COI, URLs |
| `11_methods.tex` | Methods | None | Technical specs |
| `12_references.tex` | References | None | 21 citations |
| `13_figures.tex` | Figure Specs | Figs 1-3 | Design specifications |
| `14_table1.tex` | Table 1 | Table 1 | Database comparison |

---

## Dependency Map

```
                    ┌─────────────────┐
                    │  01_TITLE       │
                    │  (standalone)   │
                    └────────┬────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────────┐
│                        02_ABSTRACT                              │
│  Depends on: ALL metrics from Results sections                  │
│  Key numbers: 97.5%, 83.24%, 76%→92%, 40%→90%                  │
└────────────────────────────────────────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────────┐
│                      03_INTRODUCTION                            │
│  Inputs: Database stats, clinical workflow data                 │
│  Requires: TABLE 1                                              │
│  References: [1-15]                                             │
└────────────────────────────────────────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ 04_RESULTS_2.1  │ │ 05_RESULTS_2.2  │ │ 06_RESULTS_2.3  │
│ Data Sources    │ │ ReACT Extract   │ │ GPRC5D Case     │
│                 │ │                 │ │                 │
│ Inputs:         │ │ Inputs:         │ │ Inputs:         │
│ - 1,300 pubs    │ │ - P/R metrics   │ │ - 15 variants   │
│ - 21,000 pairs  │ │ - 97.5% acc     │ │ - 3 categories  │
│ - Dictionary #s │ │ - 2 PDF/min     │ │                 │
│                 │ │                 │ │ Refs: [20-21]   │
│ No figures      │ │ ▶ FIGURE 1      │ │ → Supp S2, S3   │
│                 │ │ Refs: [16-19]   │ │                 │
└─────────────────┘ └─────────────────┘ └─────────────────┘
                             │
         ┌───────────────────┴───────────────────┐
         ▼                                       ▼
┌─────────────────────────────┐ ┌─────────────────────────────┐
│ 07_RESULTS_2.4              │ │ 08_RESULTS_2.5              │
│ NL-to-SQL                   │ │ Knowledge Interface         │
│                             │ │                             │
│ Inputs:                     │ │ Inputs:                     │
│ - 83.24% accuracy           │ │ - 76%→92% success           │
│ - 55% baseline              │ │ - 40%→90% synonyms          │
│ - 6-7 sec latency           │ │ - <10ms canonicalization    │
│                             │ │                             │
│ ▶ FIGURE 2                  │ │ ▶ FIGURE 3                  │
│                             │ │ → Supp Fig S3               │
└─────────────────────────────┘ └─────────────────────────────┘
                             │
                             ▼
┌────────────────────────────────────────────────────────────────┐
│                        09_DISCUSSION                            │
│  Synthesizes: All Results sections                              │
│  Key claims: 10x speed, 100% GPRC5D concordance, safety        │
│  Future work: Patient-level reporting (separate study)         │
└────────────────────────────────────────────────────────────────┘
                             │
         ┌───────────────────┼───────────────────┐
         ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ 10_BACK_MATTER  │ │ 11_METHODS      │ │ 12_REFERENCES   │
│                 │ │                 │ │                 │
│ - Funding       │ │ - ReACT impl    │ │ - 21 citations  │
│ - COI           │ │ - NL-SQL train  │ │ - Verify DOIs   │
│ - Data/Code URL │ │ - Knowledge sys │ │                 │
│ - Contributions │ │ → Supp Methods  │ │                 │
└─────────────────┘ └─────────────────┘ └─────────────────┘
                             │
         ┌───────────────────┴───────────────────┐
         ▼                                       ▼
┌─────────────────────────────┐ ┌─────────────────────────────┐
│ 13_FIGURES                  │ │ 14_TABLE1                   │
│                             │ │                             │
│ Figure 1: ReACT pipeline    │ │ Database comparison         │
│ Figure 2: NL-to-SQL         │ │ - CIViC                     │
│ Figure 3: Knowledge interface│ │ - OncoKB                    │
│                             │ │ - COSMIC                    │
│ Design specs for each       │ │ - ClinVar                   │
│ PNG files needed            │ │                             │
└─────────────────────────────┘ └─────────────────────────────┘
```

---

## Metrics Cross-Reference Table

| Metric | Abstract | Results | Discussion | Location |
|--------|:--------:|:-------:|:----------:|----------|
| 1,300 publications | ✓ | 2.1, 2.2 | - | Training data |
| 21,000 Q-SQL pairs | ✓ | 2.1, 2.4 | - | NL-SQL training |
| 97.5% extraction accuracy | ✓ | 2.2 | ✓ | ReACT performance |
| 72.2% auto-validation | - | 2.2 | - | Validation stats |
| 2 PDFs/min | - | 2.2 | - | Processing speed |
| 15 evidence items | - | 2.3 | - | GPRC5D case |
| 83.24% SQL accuracy | ✓ | 2.4 | - | NL-SQL performance |
| 55% baseline | ✓ | 2.4 | - | Baseline comparison |
| 6-7 sec latency | - | 2.4, 2.5 | ✓ | Response time |
| 76% → 92% success | ✓ | 2.5 | ✓ | Overall improvement |
| 40% → 90% synonyms | ✓ | 2.5 | ✓ | Synonym handling |
| <10ms canonicalization | - | 2.5 | - | Latency |
| 10x speed vs human | - | - | ✓ | Claim |
| 100% concordance | - | - | ✓ | GPRC5D validation |

---

## Figure Requirements Summary

### Figure 1: ReACT Pipeline (Results 2.2)
**File:** `figure1.png`

```
┌─────────────────────────────────────────────────────────────┐
│  INPUT          PARSING        ReACT           OUTPUT       │
│  ┌─────┐       ┌───────┐     ┌─────────┐     ┌─────────┐   │
│  │ PDF │ ───▶  │PyPDF2 │ ──▶ │ R→A→C→T │ ──▶ │ CIViC   │   │
│  │     │       │omniOCR│     │         │     │  JSON   │   │
│  └─────┘       └───────┘     └─────────┘     └─────────┘   │
│                                                             │
│  Callouts: 2 PDFs/min | 97.5% acc | 1,300 items | 70/30    │
└─────────────────────────────────────────────────────────────┘
```

### Figure 2: NL-to-SQL (Results 2.4)
**File:** `figure2.png`

```
┌─────────────────────────────────────────────────────────────┐
│  TRAINING DATA              MODEL              PERFORMANCE  │
│  ┌──────────────┐         ┌────────┐         ┌──────────┐  │
│  │ 21K Q-SQL    │ ──────▶ │Llama-3 │ ──────▶ │ 83.24%   │  │
│  │ 4 tiers      │         │+ LoRA  │         │ vs 55%   │  │
│  └──────────────┘         └────────┘         └──────────┘  │
│                                                             │
│  Tiers: Simple 5K | Medium 5K | Complex 5K | Super 6K      │
│  Callouts: 83.24% acc | 6-7s latency | 28-pt improvement   │
└─────────────────────────────────────────────────────────────┘
```

### Figure 3: Knowledge Interface (Results 2.5)
**File:** `figure3.png`

```
┌─────────────────────────────────────────────────────────────┐
│  MESSY INPUT    5 COMPONENTS           CLEAN OUTPUT         │
│  ┌─────────┐   ┌──────────────┐       ┌──────────────┐     │
│  │"HER1"   │   │ 1.Knowledge  │       │ Structured   │     │
│  │"breast  │──▶│ 2.Multi-step │──────▶│ Clinical     │     │
│  │ ca"     │   │ 3.DB Manager │       │ Report       │     │
│  └─────────┘   │ 4.Interface  │       └──────────────┘     │
│                │ 5.Transparency│                            │
│                └──────────────┘                            │
│  Callouts: 76%→92% | 40%→90% synonyms | 80% recovery       │
└─────────────────────────────────────────────────────────────┘
```

---

## Table 1 Summary

| Feature | CIViC | OncoKB | COSMIC | ClinVar |
|---------|:-----:|:------:|:------:|:-------:|
| Access model | **Open** | License | License | **Open** |
| API support | Yes | Yes | Yes | Yes |
| NL query | **Partial** | No | No | No |
| Evidence standards | Dual | AMP/CAP | Mixed | ACMG |
| JSON export | **Yes** | License | License | **Yes** |
| Gene normalization | **Yes** | Partial | Partial | Partial |
| EHR integration | Partial | Partial | No | Partial |

**Key insight:** CIViC is only database with partial NL support (gap OncoCITE addresses)

---

## Editing Checklist

### Before Editing Any Section:
- [ ] Review metrics cross-reference table
- [ ] Note which figures/tables are required
- [ ] Check dependencies on other sections

### After Editing:
- [ ] Update Abstract if metrics changed
- [ ] Verify figure callouts match figure content
- [ ] Check reference numbers still correct
- [ ] Ensure Methods aligns with Results

### Final Review:
- [ ] All metrics consistent across Abstract/Results/Discussion
- [ ] All 3 figures have PNG files
- [ ] Table 1 present and referenced
- [ ] 21 references verified
- [ ] Supplementary materials referenced correctly
