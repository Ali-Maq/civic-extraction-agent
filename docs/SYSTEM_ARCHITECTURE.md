# System Architecture: CIViC Extraction Agent

> **Status:** Production Ready (Verified on 2025-12-10)
> **Architecture:** "Reader-First" Multi-Agent System
> **Framework:** Claude Agent SDK

---

## 1. Project Overview (For Interns)

**What is this?**
This is an AI system that reads scientific papers (PDFs) and extracts structured clinical evidence for the [CIViC](https://civicdb.org) database (Clinical Interpretations of Variants in Cancer).

**The Problem:**
Extracting data from papers is hard because:
1.  Papers are visual (PDFs) with tables and figures.
2.  Clinical logic is complex (genes, variants, drugs, diseases).
3.  We need strict accuracy (no hallucinations).

**The Solution:**
We split the brain into specialized "Agents":
*   **The Reader:** Like a scanner. It reads the PDF once and converts it to clean text/JSON.
*   **The Orchestrator:** The boss. It manages the team.
*   **The Planner:** The strategist. "This is a breast cancer paper about BRCA1."
*   **The Extractor:** The worker. "I found a sentence on page 3 saying BRCA1 V1833F is sensitive to Olaparib."
*   **The Critic:** The reviewer. "Wait, page 3 actually says *resistant*. Fix it."
*   **The Normalizer:** The librarian. "Standardizing 'Olaparib' to RxNorm ID 12345."

**Key Concept: "Reader-First"**
Instead of letting every agent read the PDF (expensive & slow), the **Reader** runs *once*. Everyone else works from the text it extracts. This is the "Single Source of Truth."

---

