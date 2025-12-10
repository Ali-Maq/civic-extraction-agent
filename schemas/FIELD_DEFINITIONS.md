# CIViC Evidence Item Field Definitions

## Purpose

This document provides **comprehensive definitions** for all 25 Tier 1 fields that Claude extracts from cancer research papers. Each field includes:

* What it means in the CIViC context
* Where to find it in a paper
* Exact format and valid values
* Real examples
* Common mistakes to avoid

---

## CORE EVIDENCE FIELDS (5 required fields)

### 1. evidence_description

 **What it is** : A 1-3 sentence summary of the clinical finding that captures the key claim, the supporting data, and the patient population.

 **Where to find it** : Results section, abstract conclusions, figure/table legends.

 **Format** : Plain text, 50-300 words. Must include:

* The variant-disease-outcome relationship
* Key statistics (HR, OR, p-value, response rate, survival)
* Patient numbers when available

 **Good examples** :

* "In a Phase III trial of 724 NSCLC patients, those with EGFR L858R mutations showed significantly improved PFS with erlotinib vs chemotherapy (median 10.4 vs 5.1 months, HR 0.34, p<0.001)."
* "BRAF V600E-mutant melanoma patients treated with vemurafenib achieved 48% objective response rate (n=132) compared to 5% with dacarbazine (n=138), p<0.001."

 **Bad examples** :

* "EGFR mutations are associated with erlotinib response." (Too vague, no statistics)
* "The study found significant results." (No specifics)

 **Common mistakes** :

* Omitting statistics (always include HR, p-value, n if available)
* Being too brief (this is the core content of the evidence item)
* Including speculation not supported by data

---

### 2. evidence_level

 **What it is** : The strength of evidence based on study design, NOT the clinical importance.

 **Where to find it** : Methods section (study design), abstract.

 **Valid values** : A, B, C, D, E

| Level       | Study Types                                                                                      | How to Identify                                                                 |
| ----------- | ------------------------------------------------------------------------------------------------ | ------------------------------------------------------------------------------- |
| **A** | Meta-analyses, FDA approvals, NCCN guidelines, Phase III RCTs with multiple validation studies   | Look for "meta-analysis", "guideline", "FDA approved", "validated"              |
| **B** | Phase I/II/III clinical trials, large retrospective cohorts (>50 patients), case-control studies | Look for "Phase", "cohort", "retrospective", "prospective", patient numbers >50 |
| **C** | Case reports, small case series (<20 patients)                                                   | Look for "case report", "we present a patient", small n                         |
| **D** | Preclinical: cell lines, mouse models, in vitro                                                  | Look for "cell line", "xenograft", "in vitro", "mouse model"                    |
| **E** | Computational predictions, indirect inference                                                    | Look for "predicted", "inferred", "computational"                               |

 **Common mistakes** :

* Giving Level B to a case report (should be C)
* Giving Level A to a single Phase III trial (A requires validation/guidelines)
* Confusing clinical importance with evidence strength

---

### 3. evidence_type

 **What it is** : The clinical question being addressed - what aspect of clinical care does this evidence inform?

 **Where to find it** : Infer from the claim being made.

 **Valid values and their meanings** :

| Type                   | Clinical Question                                          | Requires                | Examples                                       |
| ---------------------- | ---------------------------------------------------------- | ----------------------- | ---------------------------------------------- |
| **PREDICTIVE**   | Does the variant predict response to a specific therapy?   | therapy_names field     | "EGFR L858R predicts erlotinib sensitivity"    |
| **DIAGNOSTIC**   | Does the variant help diagnose or classify a cancer?       | -                       | "IDH1 R132H distinguishes glioma from gliosis" |
| **PROGNOSTIC**   | Does the variant predict outcome independent of treatment? | -                       | "TP53 mutation associated with poor survival"  |
| **PREDISPOSING** | Does germline variant increase cancer risk?                | variant_origin=GERMLINE | "BRCA1 mutation increases breast cancer risk"  |
| **ONCOGENIC**    | Is this variant a cancer driver?                           | -                       | "BRAF V600E demonstrates oncogenic activity"   |
| **FUNCTIONAL**   | What is the biochemical effect of the variant?             | -                       | "V600E causes constitutive kinase activation"  |

 **Decision tree** :

1. Does it mention a drug/therapy response? → PREDICTIVE
2. Does it help identify/classify the cancer? → DIAGNOSTIC
3. Does it predict patient outcome without therapy context? → PROGNOSTIC
4. Is it a germline variant causing cancer susceptibility? → PREDISPOSING
5. Does it establish the variant as a cancer driver? → ONCOGENIC
6. Does it only describe molecular function? → FUNCTIONAL

 **Common mistakes** :

* Calling a drug response study PROGNOSTIC (it's PREDICTIVE)
* Missing that PREDICTIVE requires therapy_names
* Confusing ONCOGENIC (driver status) with FUNCTIONAL (mechanism)

---

### 4. evidence_direction

 **What it is** : Does the study support or refute the clinical significance claim?

 **Where to find it** : Results section, conclusions.

 **Valid values** : SUPPORTS, DOES_NOT_SUPPORT

 **When to use each** :

* **SUPPORTS** : The study provides evidence FOR the claimed association
* **DOES_NOT_SUPPORT** : The study shows no association or contradicts the claim

 **Examples** :

* Study shows EGFR L858R patients respond to erlotinib → SUPPORTS + SENSITIVITY
* Study shows BRAF V600E patients do NOT respond differently to immunotherapy → DOES_NOT_SUPPORT + NA

 **Important** : DOES_NOT_SUPPORT is NOT a failure - negative findings are valuable evidence. If a study shows "no difference in survival by BRAF status", that's a valid DOES_NOT_SUPPORT item.

---

### 5. evidence_significance

 **What it is** : The specific clinical meaning of the evidence. Values depend on evidence_type.

 **Valid values by evidence_type** :

| evidence_type | Valid significance values                                                                 |
| ------------- | ----------------------------------------------------------------------------------------- |
| PREDICTIVE    | SENSITIVITY, RESISTANCE, ADVERSE_RESPONSE, REDUCED_SENSITIVITY, NA                        |
| DIAGNOSTIC    | POSITIVE, NEGATIVE, NA                                                                    |
| PROGNOSTIC    | BETTER_OUTCOME, POOR_OUTCOME, NA                                                          |
| PREDISPOSING  | PREDISPOSITION, PROTECTIVENESS, NA                                                        |
| ONCOGENIC     | ONCOGENICITY, NA                                                                          |
| FUNCTIONAL    | GAIN_OF_FUNCTION, LOSS_OF_FUNCTION, UNALTERED_FUNCTION, NEOMORPHIC, DOMINANT_NEGATIVE, NA |

 **PREDICTIVE significance explained** :

* **SENSITIVITY** : Variant predicts response/benefit from therapy
* **RESISTANCE** : Variant predicts lack of response/resistance
* **ADVERSE_RESPONSE** : Variant predicts toxicity/adverse effects
* **REDUCED_SENSITIVITY** : Variant predicts decreased (but not absent) response

 **PROGNOSTIC significance explained** :

* **BETTER_OUTCOME** : Variant associated with improved survival/outcomes
* **POOR_OUTCOME** : Variant associated with worse survival/outcomes

 **When to use NA** : When the evidence_direction is DOES_NOT_SUPPORT (no association found), significance should typically be NA.

---

## VARIANT FIELDS (7 fields)

### 6. variant_names

 **What it is** : The specific genetic alteration, as close to how it appears in the paper as possible.

 **Where to find it** : Throughout paper, especially abstract, results, tables.

 **Format** : Use the paper's notation. Common formats:

* Point mutations: V600E, L858R, G12D
* Exon-level: EXON 19 DELETION, EXON 11 MUTATION
* Amplification: AMPLIFICATION
* Fusion: Leave blank (use fusion fields instead)
* Expression: OVEREXPRESSION, EXPRESSION

 **Examples** :

* "V600E" (not "Val600Glu" unless paper uses that)
* "EXON 19 DELETION" (not "del19" or "E746-A750del")
* "T790M"
* "AMPLIFICATION"

 **Common mistakes** :

* Using HGVS when paper uses simple notation
* Putting gene name here (gene goes in feature_names)
* Using generic "MUTATION" when paper specifies exact variant

---

### 7. variant_origin

 **What it is** : Whether the variant is inherited (germline) or acquired in the tumor (somatic).

 **Where to find it** : Methods (sample type), introduction, sometimes stated explicitly.

 **Valid values** : SOMATIC, GERMLINE, RARE_GERMLINE, COMBINED, NA

 **How to determine** :

* "tumor DNA", "tumor tissue", "biopsy" → SOMATIC
* "germline", "inherited", "blood DNA", "constitutional" → GERMLINE
* Cancer predisposition studies (BRCA, Lynch) → usually GERMLINE
* Most solid tumor variant studies → usually SOMATIC
* If not stated and unclear → NA

 **Common mistakes** :

* Assuming all variants are somatic (BRCA can be germline)
* Missing explicit germline statements

---

### 8. variant_type_names

 **What it is** : The category of genetic alteration.

 **Where to find it** : Infer from variant_names, or explicitly stated.

 **Common values** :

* **Missense Variant** : Single amino acid change (V600E, L858R)
* **Frameshift Truncation** : Insertions/deletions causing frameshift
* **In-frame Deletion** : Deletions maintaining reading frame (EXON 19 DEL)
* **In-frame Insertion** : Insertions maintaining reading frame (EXON 20 INS)
* **Nonsense** : Premature stop codon
* **Splice Site Variant** : Affects splicing
* **Amplification** : Gene copy number gain
* **Deletion** : Gene/exon loss
* **Fusion** : Gene fusion
* **Overexpression** : Increased expression

 **How to infer** :

* V600E, L858R, G12D → Missense Variant
* EXON 19 DELETION → In-frame Deletion
* AMPLIFICATION → Amplification
* BCR-ABL → Fusion

---

### 9. variant_hgvs_descriptions

 **What it is** : HGVS notation if explicitly stated in the paper.

 **Where to find it** : Methods, results, supplementary tables.

 **Format** : Protein (p.) or coding DNA (c.) notation exactly as stated.

 **Examples** :

* "p.V600E"
* "c.1799T>A"
* "p.Glu746_Ala750del"

 **Important** : Only populate if the paper explicitly states HGVS. Do NOT convert "V600E" to "p.V600E" yourself - that's database lookup work (Tier 2).

---

### 10. molecular_profile_name

 **What it is** : Combined gene + variant for display purposes.

 **Format** : "[GENE] [VARIANT]"

 **Examples** :

* "BRAF V600E"
* "EGFR L858R"
* "EGFR EXON 19 DELETION"
* "EML4-ALK" (for fusions)

---

### 11-12. fusion_five_prime_gene_names / fusion_three_prime_gene_names

 **What it is** : For gene fusions, the 5' and 3' partner genes.

 **Where to find it** : Paper will describe fusions like "EML4-ALK", "BCR-ABL1".

 **Format** : Gene symbol only.

 **Examples** :

* EML4-ALK fusion: five_prime = "EML4", three_prime = "ALK"
* BCR-ABL1 fusion: five_prime = "BCR", three_prime = "ABL1"
* ROS1 fusions (various partners): three_prime = "ROS1"

 **Important** : Only populate for fusion variants. Leave blank for point mutations, amplifications, etc.

---

## FEATURE/GENE FIELDS (3 fields)

### 13. feature_names

 **What it is** : The gene symbol.

 **Where to find it** : Throughout paper.

 **Format** : Official HGNC gene symbol, uppercase.

 **Examples** : EGFR, BRAF, KRAS, TP53, ALK, ROS1, BRCA1

 **Common mistakes** :

* Using old symbols (HER2 instead of ERBB2)
* Including variant info here (that goes in variant_names)

---

### 14. feature_full_names

 **What it is** : Full gene name if mentioned in paper.

 **Where to find it** : Introduction, sometimes first mention.

 **Examples** :

* "Epidermal Growth Factor Receptor" for EGFR
* "B-Raf Proto-Oncogene" for BRAF

 **Note** : Only populate if explicitly stated in paper.

---

### 15. feature_types

 **What it is** : The type of molecular feature.

 **Valid values** : GENE, FACTOR

 **Usage** : Almost always "GENE". Use "FACTOR" for non-gene biomarkers like:

* Microsatellite instability (MSI)
* Tumor mutation burden (TMB)
* PD-L1 expression

---

## DISEASE FIELDS (2 fields)

### 16. disease_name

 **What it is** : The cancer type or disease studied.

 **Where to find it** : Title, abstract, throughout paper.

 **Format** : Use CIViC preferred names:

* "Non-Small Cell Lung Carcinoma" (not "NSCLC", "lung cancer")
* "Melanoma" (not "skin cancer")
* "Colorectal Cancer" (not "colon cancer", "CRC")
* "Breast Cancer"
* "Acute Myeloid Leukemia" (not "AML")

 **For subtypes** : Include subtype if clinically relevant:

* "EGFR-mutant Non-Small Cell Lung Carcinoma"
* "Triple Negative Breast Cancer"

---

### 17. disease_display_name

 **What it is** : Shorter display name for UI purposes.

 **Format** : Can use abbreviations.

 **Examples** : "NSCLC", "Melanoma", "CRC", "AML"

---

## THERAPY FIELDS (2 fields)

### 18. therapy_names

 **What it is** : The specific drug(s) studied. **Required for PREDICTIVE evidence.**

 **Where to find it** : Title, methods, results.

 **Format** :

* Use generic drug names, not brand names
* For combinations: comma-separated (e.g., "Dabrafenib,Trametinib")
* NEVER use drug classes (see mistakes below)

 **Good examples** :

* "Erlotinib"
* "Vemurafenib"
* "Dabrafenib,Trametinib" (combination)
* "Pembrolizumab"

 **CRITICAL MISTAKES - Never do this** :

* ❌ "TKI" (use specific drug: Erlotinib, Gefitinib, etc.)
* ❌ "EGFR inhibitor" (use specific drug)
* ❌ "Chemotherapy" (use specific agent: Carboplatin, Paclitaxel)
* ❌ "BRAF inhibitor" (use Vemurafenib or Dabrafenib)
* ❌ "Immunotherapy" (use Pembrolizumab, Nivolumab, etc.)
* ❌ "Targeted therapy" (never acceptable)

 **If paper only uses drug class** : Try to identify specific drug from context. If truly unidentifiable, this may not be extractable as PREDICTIVE evidence.

---

### 19. therapy_interaction_type

 **What it is** : How multiple drugs are used together.

 **When to populate** : Only when therapy_names contains multiple drugs.

 **Valid values** :

* **COMBINATION** : Drugs given simultaneously (e.g., "Dabrafenib + Trametinib")
* **SEQUENTIAL** : Drugs given in defined sequence (e.g., "followed by", "after progression on")
* **SUBSTITUTES** : Interchangeable alternatives (e.g., "erlotinib OR gefitinib")

---

## SOURCE/PUBLICATION FIELDS (3 fields)

### 20. source_title

 **What it is** : The full paper title.

 **Where to find it** : First page header, running title.

 **Format** : Exact title as published.

---

### 21. source_publication_year

 **What it is** : Year the paper was published.

 **Where to find it** :

* Header/footer
* Copyright notice
* Citation format in references
* DOI (contains year)

 **Format** : 4-digit year only: "2015", "2023"

---

### 22. source_journal

 **What it is** : Journal name.

 **Where to find it** : Header, first page.

 **Format** : Full journal name preferred:

* "Journal of Clinical Oncology" (not "JCO")
* "New England Journal of Medicine" (not "NEJM")

---

## CLINICAL TRIAL FIELDS (2 fields)

### 23. clinical_trial_nct_ids

 **What it is** : ClinicalTrials.gov registration number.

 **Where to find it** : Methods, acknowledgments, sometimes in title.

 **Format** : "NCT" followed by 8 digits: "NCT01234567"

 **How to identify** : Look for "NCT" followed by numbers, "ClinicalTrials.gov", "registered trial".

---

### 24. clinical_trial_names

 **What it is** : Trial name or acronym.

 **Where to find it** : Title, abstract, methods.

 **Examples** :

* "BRIM-3" (BRAF V600E melanoma trial)
* "KEYNOTE-001" (pembrolizumab trials)
* "PACIFIC" (durvalumab in NSCLC)
* "CheckMate" trials (nivolumab)

---

## PHENOTYPE FIELD (1 field)

### 25. phenotype_names

 **What it is** : Specific clinical phenotypes or characteristics associated with the evidence.

 **Where to find it** : Results, clinical characteristics tables.

 **Examples** :

* "Increased tumor mutation burden"
* "Smoking history"
* "Prior platinum therapy"
* "Brain metastases"

 **Note** : Only populate if specific phenotypes are integral to the evidence claim.

---

## Summary Checklist

Before saving an evidence item, verify:

* [ ] evidence_description has statistics (HR, p-value, n)
* [ ] evidence_level matches study design (not clinical importance)
* [ ] evidence_type matches the clinical question
* [ ] If PREDICTIVE, therapy_names is populated with specific drugs
* [ ] therapy_names uses drug names, NOT drug classes
* [ ] variant_names matches paper notation
* [ ] feature_names is gene symbol only
* [ ] All fields use UPPERCASE enum values
