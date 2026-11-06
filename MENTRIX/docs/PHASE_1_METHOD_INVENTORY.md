# Phase 1 — Method vs Model vs Pipeline inventory

| Component | Classification | Question type | Status | Key limitation |
|---|---|---|---|---|
| Strict literal matching | Rule baseline / method | MCQ, short, math | executed | Literal equality, brittle |
| Type-aware v1 | Rules-based pipeline | MCQ, short, math | executed | Unapproved synonyms rejected; math tolerance can auto-accept |
| Type-aware v2 | Conservative rules-based pipeline | MCQ, short, math | executed | Higher review burden, not externally validated |
| Restricted AST + SymPy | Parsing / symbolic math library method | Math | executed | No robust symbolic-domain proof or partial credit |
| Token overlap | Lexical method | Descriptive | historical, 25 assistant-generated cases | Meaning not reliable |
| TF-IDF word + char | Feature extraction / method | Descriptive | historical, 25 | Weak semantic sensitivity |
| SBERT `all-MiniLM-L6-v2` | Pretrained embedding MODEL | Descriptive | historical, 25 | Similarity not truth/validity |
| NLI `nli-MiniLM2-L6-H768` | Pretrained inference MODEL | Descriptive | historical, 25 | Misses contradictions |
| Rubric + SBERT / NLI | Scoring PIPELINES | Descriptive | historical, 25 | Preliminary inconsistent labels; no credible winner |
| OCR / Math OCR | Model/service pipeline category | Handwriting | NOT EXECUTED | No image dataset or OCR benchmark |

**No project-specific fine-tuning was performed.** Historical essay metrics are separately reported and not interchangeable with the current typed answer categorical decisions.
