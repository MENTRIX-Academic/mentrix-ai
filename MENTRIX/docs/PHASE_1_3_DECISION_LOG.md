# AI Team Decision Log (proposed, for TA and team review)

| ID | Decision | Status | Rationale | Required sign-off |
|---|---|---|---|---|
| D01 | Use explicit question_type metadata | Prototype implemented | Avoid inferring type from answer length | Backend + TA |
| D02 | Separate short (1–3 words) from descriptive | Research decided | Different scoring and evaluation | TA |
| D03 | Use V2 for typed MCQ candidate | Provisional | Parse unambiguous single choice | TA |
| D04 | Use V2 known aliases/contrasts on short candidates | Provisional | Unknown synonyms reviewed rather than discarded | TA per course |
| D05 | Use V2 + SymPy for single final math answers | Provisional | Exact equivalence + domain guard | TA tolerance/domain policy |
| D06 | Do NOT auto-grade essays in current demo | Implemented | Uncalibrated and inconsistent rubric research | TA and supervisor |
| D07 | Require final score approval by authorized TA | Design policy / mocked in demo | Human accountability | Backend security owner |
| D08 | Do NOT call 123 synthetic policy agreements accuracy | Adopted documentation rule | Tuned against authors' designed cases | AI Lead |
| D09 | Human data/holdout prerequisite for Phase 3 scientific closure | Pending | Prevent overfitting and label leakage | Supervisor |
| D10 | OCR evaluated separately from typed grading | Planned | Isolate recognition vs grader errors | OCR owner |

Record: Date / approver / course / question_bank_version / rubric_version / approved exceptions / signature or link. None of these sign-offs is asserted here.
