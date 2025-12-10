"""
Evidence Core Prompt
====================

Core evidence field definitions and guidelines.
"""

EVIDENCE_CORE_PROMPT = """
## Core Evidence Fields

Every evidence item must have these 5 core fields:

### 1. evidence_description
- 1-3 sentence summary of the clinical finding
- Must be standalone and informative
- Include key statistics if available (HR, p-value, response rate)
- Example: "Patients with EGFR L858R mutation showed 71% response rate to erlotinib compared to 1% in wild-type patients (p<0.001)."

### 2. evidence_level (A, B, C, D, E)
- A: Validated association - meta-analyses, multiple large studies, guidelines
- B: Clinical evidence - clinical trials, prospective/retrospective cohorts
- C: Case study - individual case reports, small case series
- D: Preclinical - cell lines, animal models, in vitro studies
- E: Inferential - indirect evidence, computational predictions

### 3. evidence_type
- PREDICTIVE: Variant predicts response to a therapy
- DIAGNOSTIC: Variant helps diagnose a disease
- PROGNOSTIC: Variant predicts disease outcome (independent of treatment)
- PREDISPOSING: Variant increases disease risk
- ONCOGENIC: Variant contributes to cancer development
- FUNCTIONAL: Variant affects gene/protein function

### 4. evidence_direction
- SUPPORTS: Evidence supports the clinical association
- DOES_NOT_SUPPORT: Evidence refutes the clinical association

### 5. evidence_significance
Must match the evidence_type:

| evidence_type | Valid significance values |
|---------------|---------------------------|
| PREDICTIVE | SENSITIVITY, RESISTANCE, ADVERSE_RESPONSE, REDUCED_SENSITIVITY, NA |
| DIAGNOSTIC | POSITIVE, NEGATIVE, NA |
| PROGNOSTIC | BETTER_OUTCOME, POOR_OUTCOME, NA |
| PREDISPOSING | PREDISPOSITION, PROTECTIVENESS, NA |
| ONCOGENIC | ONCOGENICITY, NA |
| FUNCTIONAL | GAIN_OF_FUNCTION, LOSS_OF_FUNCTION, UNALTERED_FUNCTION, NEOMORPHIC, DOMINANT_NEGATIVE, NA |
"""

EVIDENCE_TYPES_GUIDE = """
## Evidence Type Selection Guide

### PREDICTIVE Evidence
**Question**: Does this variant predict how a patient will respond to a specific therapy?

**Examples**:
- "EGFR L858R predicts sensitivity to erlotinib" → PREDICTIVE, SENSITIVITY
- "KRAS G12C confers resistance to cetuximab" → PREDICTIVE, RESISTANCE

**Requirements**:
- MUST have a specific therapy (therapy_names field)
- MUST describe treatment response

### DIAGNOSTIC Evidence
**Question**: Does this variant help establish a disease diagnosis?

**Examples**:
- "BCR-ABL1 fusion confirms diagnosis of CML" → DIAGNOSTIC, POSITIVE
- "Absence of NPM1 mutation excludes AML with NPM1 mutation subtype" → DIAGNOSTIC, NEGATIVE

### PROGNOSTIC Evidence
**Question**: Does this variant predict patient outcome INDEPENDENT of treatment?

**Examples**:
- "TP53 mutation associated with worse overall survival" → PROGNOSTIC, POOR_OUTCOME
- "Low BRCA1 expression correlates with better prognosis" → PROGNOSTIC, BETTER_OUTCOME

**Note**: If outcome depends on a specific treatment, it's PREDICTIVE not PROGNOSTIC

### PREDISPOSING Evidence
**Question**: Does this variant increase or decrease cancer risk?

**Examples**:
- "BRCA1 pathogenic variants increase breast cancer risk" → PREDISPOSING, PREDISPOSITION
- "CHEK2 c.1100delC variant doubles breast cancer risk" → PREDISPOSING, PREDISPOSITION

### ONCOGENIC Evidence
**Question**: Does this variant contribute to cancer development/progression?

**Examples**:
- "BRAF V600E is an oncogenic driver in melanoma" → ONCOGENIC, ONCOGENICITY

### FUNCTIONAL Evidence
**Question**: Does this describe variant's effect on protein/gene function?

**Examples**:
- "V600E causes constitutive kinase activation" → FUNCTIONAL, GAIN_OF_FUNCTION
- "R248W abolishes DNA binding" → FUNCTIONAL, LOSS_OF_FUNCTION
"""