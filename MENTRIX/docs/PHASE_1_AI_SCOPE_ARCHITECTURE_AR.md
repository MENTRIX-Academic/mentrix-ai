# Phase 1 — AI Scope & Architecture (research baseline deliverable)
**State: documentation and local baseline packaging complete; formal TA sign-off and independent teammate reproduction pending.**

## Project purpose
MENTRIX (TAFlow research track) is an integrated TA platform with centralized academic records, dynamic QR attendance, course enrollment status, typed / handwritten quiz grading with TA review, Excel import/export and a restricted TA conversational assistant. The AI team owns grading research, OCR/HTR experiments, model/rule evaluation, and constrained assistant intelligence; backend owns authorization, database consistency, attendance QR and final score transactions. Frontend owns user interfaces.

## Grade pipeline and scope boundaries
```text
[Question set / TA-approved key & rubric]        [Question image / handwriting - NOT IMPLEMENTED]
                  |                                                  |
[Question metadata: ID + known type]           [OCR/HTR/Math OCR - Phase 4]
                  |                                                  |
[Typed answer or verified text] <----------------+--------------------+
                  |
[Dispatcher by known type: MCQ / short (1-3 words) / math / descriptive]
                  |
[Type-specific grader: rules or future verified model + rubric]
                  |
[Correct / Incorrect / Needs review; nullable proposed score; explanation]
                  |
[Authenticated TA review (NOT AVAILABLE IN DEMO)]
                  |
[Backend-owned final grade and audit log (NOT AVAILABLE IN DEMO)]
```

## Question metadata and branching
- MCQ: option set and `correct_letter`; no NLP/LLM required for clear typed letter responses.
- Short: `canonical_answer`, `accepted_answers` and educator-reviewed `KNOWN_WRONG`; wording is 1–3 words, not a description.
- Math: `canonical_expression`, `base_unit`, `allowed_symbols`, `require_unit`, `allow_lhs`; parser and SymPy verification, not neural training.
- Descriptive: scored by analytic rubric and possible NLP models; CURRENT demo returns review, no live essay model.
- Question type comes from TA-authored metadata, **not** response length. One mixed definition+math question requires splitting or a multi-part rubric.
- `questions.json` is a synthetic/pilot question bank with *assumed* approval only. `ANSWER_KEY_DRAFT.md` expressly says TA approval pending.

## API integration implemented (local, insecure prototype)
- `GET /api/v1/demo/quiz`: public prompts and answer-free choices
- `POST /api/v1/demo/grade`: run V2 on typed answers
- `POST /api/v1/demo/compare`: Strict/V1/V2 comparison
- `POST /api/v1/demo/attempts/{id}/items/{qid}/approve`: mock approval without real identity verification
- `GET /roadmap`, `GET /research`, `GET /docs` pages
- No OCR, authenticated access, persistence, official grades, production deployment or human-approved dataset.

## Artifacts to maintain under GitHub
- `grader.py`, `grader_v2.py`, `questions.json` are kept byte-for-byte original (SHA256 manifest under research/source_manifest.json).
- `research/data/curated_demo_cases.csv` is new and assistant-authored — never treat as unseen or student-labeled.
- Historical `research/data/stress_summary.json`, `summary.json`, `fuzz_smoke_summary.json` copied from user's results **without re-running**, because `stress_cases.csv`, `synthetic_cases.csv`, original unit tests not provided.
- `research/compare.py` is independently executable against current original graders.

## Phase 1 gate
- DONE for documentation/architecture/taxonomy/prototype packaging.
- BLOCKED for formal completion: verified TA/supervisor approval of question bank, numerical rules, rubrics and independent teammate reproduction + Git commit evidence.
- Keep a decision-log entry and approval record rather than pretending approval happened.
