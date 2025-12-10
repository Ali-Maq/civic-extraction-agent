"""
Clinical Context Prompt
=======================

Guidelines for disease and therapy fields.
"""

CLINICAL_CONTEXT_PROMPT = """
## Disease Fields

### disease_name (Required)
- Use the disease name as stated in the paper
- Be as specific as possible
- Examples: "Non-Small Cell Lung Cancer", "Melanoma", "Chronic Myeloid Leukemia"

### disease_display_name
- Usually same as disease_name
- May be slightly different for display purposes

## Therapy Fields

### therapy_names
- REQUIRED for PREDICTIVE evidence
- Use specific drug names, NOT drug classes
- NULL for non-PREDICTIVE evidence types

**Correct Examples**:
- "Erlotinib" (not "EGFR TKI")
- "Vemurafenib" (not "BRAF inhibitor")
- "Pembrolizumab" (not "PD-1 inhibitor")
- "Carboplatin + Paclitaxel" (for combinations)

**Wrong Examples**:
- "TKIs" → Too generic
- "Chemotherapy" → Too generic
- "Targeted therapy" → Too generic
- "Immunotherapy" → Too generic

### therapy_interaction_type
- Only used for multi-drug regimens
- NULL for single-drug therapies

**COMBINATION**: Drugs given together simultaneously
- Example: "FOLFOX" (5-FU + Oxaliplatin + Leucovorin)

**SEQUENTIAL**: Drugs given one after another
- Example: "Erlotinib followed by Osimertinib on progression"

**SUBSTITUTES**: Drugs that can replace each other
- Example: "Gefitinib or Erlotinib"

## Source Fields

### source_title
- Full title of the paper

### source_publication_year
- Year of publication (4 digits)

### source_journal
- Journal name

## Clinical Trial Fields

### clinical_trial_nct_ids
- NCT numbers if paper describes a registered trial
- Format: NCT########
- Example: NCT01774721

### clinical_trial_names
- Trial name/acronym if mentioned
- Example: "FLAURA", "KEYNOTE-024", "CheckMate 067"
"""

DISEASE_THERAPY_GUIDE = """
## Common Disease Names in CIViC

### Lung Cancer
- Non-Small Cell Lung Cancer (most common)
- Lung Adenocarcinoma
- Lung Squamous Cell Carcinoma
- Small Cell Lung Cancer

### Breast Cancer
- Breast Cancer
- Triple Negative Breast Cancer
- HER2-Positive Breast Cancer
- Estrogen Receptor Positive Breast Cancer

### Colorectal Cancer
- Colorectal Cancer
- Colon Adenocarcinoma
- Rectal Adenocarcinoma

### Melanoma
- Melanoma
- Cutaneous Melanoma
- Uveal Melanoma
- Acral Melanoma

### Hematologic Malignancies
- Acute Myeloid Leukemia
- Chronic Myeloid Leukemia
- Acute Lymphoblastic Leukemia
- Non-Hodgkin Lymphoma
- Multiple Myeloma

## Common Therapy Names

### EGFR Inhibitors
- Erlotinib (Tarceva)
- Gefitinib (Iressa)
- Afatinib (Gilotrif)
- Osimertinib (Tagrisso)

### BRAF Inhibitors
- Vemurafenib (Zelboraf)
- Dabrafenib (Tafinlar)
- Encorafenib (Braftovi)

### MEK Inhibitors
- Trametinib (Mekinist)
- Cobimetinib (Cotellic)
- Binimetinib (Mektovi)

### ALK Inhibitors
- Crizotinib (Xalkori)
- Alectinib (Alecensa)
- Ceritinib (Zykadia)
- Brigatinib (Alunbrig)
- Lorlatinib (Lorbrena)

### Checkpoint Inhibitors
- Pembrolizumab (Keytruda)
- Nivolumab (Opdivo)
- Atezolizumab (Tecentriq)
- Durvalumab (Imfinzi)
- Ipilimumab (Yervoy)

### Chemotherapy (be specific)
- Cisplatin
- Carboplatin
- Paclitaxel
- Docetaxel
- Pemetrexed
- Gemcitabine
"""