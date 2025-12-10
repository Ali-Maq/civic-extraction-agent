"""
Molecular Profile Prompt
========================

Guidelines for variant and gene fields.
"""

MOLECULAR_PROFILE_PROMPT = """
## Molecular Profile Fields

### feature_names (Required)
- Gene symbol in standard nomenclature
- Examples: EGFR, BRAF, KRAS, TP53, ALK
- Use official HGNC symbols

### feature_full_names (Optional)
- Full gene name if mentioned in paper
- Example: "epidermal growth factor receptor"

### feature_types
- GENE: For standard genes (default for most CIViC entries)
- FACTOR: For non-gene factors (rare)

### variant_names (Required)
- Specific variant name
- Examples: V600E, L858R, EXON 19 DELETION, T790M
- Be as specific as the paper allows

### variant_origin
- SOMATIC: Acquired in tumor
- GERMLINE: Inherited
- RARE_GERMLINE: Rare inherited variant
- NA: Origin not specified
- COMBINED: Both somatic and germline considered

### variant_type_names
- Missense Variant
- Frameshift Truncation
- Nonsense
- In-frame Deletion
- In-frame Insertion
- Amplification
- Deletion (copy number)
- Fusion
- Splice Site Variant
- Promoter Mutation

### variant_hgvs_descriptions
- HGVS notation if provided in paper
- Protein level: p.V600E, p.L858R
- cDNA level: c.1799T>A
- Genomic level: g.140453136A>T

### molecular_profile_name
- Format: "[GENE] [VARIANT]"
- Examples: "BRAF V600E", "EGFR L858R", "ALK FUSION"

### Fusion-Specific Fields

For fusion variants, also populate:

**fusion_five_prime_gene_names**
- The 5' partner gene in the fusion
- Example: In BCR-ABL1, BCR is the 5' partner

**fusion_three_prime_gene_names**
- The 3' partner gene in the fusion
- Example: In BCR-ABL1, ABL1 is the 3' partner
"""

VARIANT_TYPES_GUIDE = """
## Variant Type Classification Guide

### Single Nucleotide Variants (SNVs)

**Missense Variant**
- Single nucleotide change causing amino acid substitution
- Example: BRAF V600E (valine → glutamate)

**Nonsense**
- Creates premature stop codon
- Example: TP53 R213*

### Insertions and Deletions (Indels)

**Frameshift Truncation**
- Insertion/deletion not divisible by 3, disrupts reading frame
- Example: APC c.3927_3931delAAAGA

**In-frame Deletion**
- Deletion of nucleotides divisible by 3
- Example: EGFR Exon 19 deletion (delE746-A750)

**In-frame Insertion**
- Insertion of nucleotides divisible by 3
- Example: EGFR Exon 20 insertion

### Copy Number Variants

**Amplification**
- Increased gene copy number
- Example: HER2 amplification, MYC amplification

**Deletion**
- Loss of gene copies (homozygous or heterozygous)
- Example: CDKN2A deletion

### Structural Variants

**Fusion**
- Two genes joined together
- Example: EML4-ALK fusion, BCR-ABL1 fusion

**Rearrangement**
- Chromosomal rearrangement affecting gene
- Example: RET rearrangement

### Other

**Splice Site Variant**
- Affects mRNA splicing
- Example: MET exon 14 skipping

**Promoter Mutation**
- Affects gene regulatory region
- Example: TERT promoter mutation

**Expression**
- Changed expression level (not sequence change)
- Example: PD-L1 overexpression
"""