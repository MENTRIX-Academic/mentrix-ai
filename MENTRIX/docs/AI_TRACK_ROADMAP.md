# MENTRIX / TAFlow — AI Work Roadmap v2.0
**Last updated:** 30 October 2026  
**Owner:** AI Team Lead  
**Basis:** MENTRIX Project Proposal, TAFlow Grading Research 28 Oct, and the running original-V2 FastAPI integration demonstration.  
**Important:** The statuses below distinguish *a working local research prototype* from *validated models, production features, and real student grading*.

## What changed from the 7-phase roadmap
- Updated the integration phase to record an actual **working local demo**: the frontend calls FastAPI, which invokes the user's original `grader_v2.py` via `adapter.py`. This is more than a mock UI, but not a production deployment.
- Kept the real-data / ground-truth and OCR phases **not complete**; they cannot be inferred from successful local typed-answer grading.
- Separated **rule/method development** from **ML model fine-tuning**; training should be justified by validated error analysis rather than treated as mandatory for MCQ, short-key, or exact math.
- Made *review/approval*, backend security, versioning, reliability, and frontend handoff explicit deliverables.
- Added concrete prerequisites, completion criteria, QA cases, suggested ownership, and the next two sprints.

## Source-of-truth status on 30 Oct 2026
| Phase | Name | Status | Evidence / missing gate |
|---|---|---|---|
| P1 | Scope, research & baseline freeze | HANDOFF PREPARED / SIGN-OFF PENDING | Source hash, 29-case reproducible *new* demonstration comparison, scope/inventory/decisions documented; TA sign-off and original test-data rerun pending |
| P2 | Authentic dataset & ground truth | NOT STARTED / PLANNED | Synthetic examples exist; no authenticated, independently labelled student set |
| P3 | Type-aware grading & model evaluation | PROTOTYPE AUDITED / VALIDATION BLOCKED | Original graders rerun on 29 new design cases and documented; original 123-case author labels historical only; human holdout and essay rerun pending |
| P4 | OCR / HTR / math OCR | NOT STARTED | Printed handwriting quiz prepared; no measured handwriting run |
| P5 | End-to-end grading & human review | PROTOTYPE ONLY | Typed-text → V2 → TA sign-off working locally; image/OCR path missing |
| P6 | AI service, backend/frontend integration | LOCAL DEMO RUNNING | FastAPI+HTML/JS+adapter; no auth, persistent database, deployment or production contract |
| P7 | Conversational assistant, optional generation, system release | PLANNED | AI chatbot and real-system evaluation not implemented |

**Existing measurements, correctly labelled:** 123 *author-designed synthetic policy cases* (MCQ 27, short 47, math 49); V2 agreed with authored decisions on all 123 after tuning on these cases, and deferred **51/123 (41.5%)** to review. **Not held-out real-student accuracy.** Historical descriptive comparison: 25 assistant-generated answers; no validated model winner. The original sample quiz includes four displayed questions (`MC01`, `SA02`, `MA03`, `E01`) from a 22-question bank; the essay example always requests review.

---

## Phase 1 — Scope, AI architecture & reproducible research  [PARTIAL]
**Goal:** All members understand exactly what AI covers, how questions are routed and what previous experiments actually prove.

### Tasks
- [x] Separate true 1–3-word short answers from descriptive / essay-like questions.
- [x] Establish provisional baselines: Strict, Type-aware V1 and Type-aware V2 for typed MCQ/short/math.
- [x] Preserve historical TF-IDF, SBERT, NLI, Rubric+SBERT, Rubric+NLI comparison as preliminary evidence.
- [x] Record synthetic stress experiment (123 cases), 24 previous unit tests, 500 malformed-input exception probes.
- [ ] Organize `ai/research/`, `ai/grading/`, `ai/data/`, `ai/ocr/`, `ai/evaluation/`, `ai/api/` within the team repository.
- [ ] Archive exact datasets, code commits, requirements, run commands and individual failure cases; rerun on a teammate's laptop.
- [ ] Confirm four assessment types, key/rubric review policy, scoring scales and which modules are v1 scope with supervisor.
- [ ] Obtain an actual TA/supervisor review of answer keys, aliases, known-wrong lists, numeric tolerance and rubric; record date/version.
- [ ] Keep a decision log distinguishing **Method**, **Pretrained Model**, **Fine-tuned Model** and **Pipeline**.

**Owner:** AI Lead + grading owners.  
**Deliverables:** Research inventory, reproducible baseline scripts, decision log, signed-off question/rubric versions, system AI scope diagram.  
**Definition of done:** A different teammate reproduces the experimental outputs and every number is labelled synthetic vs independently validated; approval claims are evidenced, not assumed.

## Phase 2 — Real dataset, annotation & ground truth  [PLANNED — HIGH PRIORITY]
**Goal:** Move beyond ChatGPT-generated student answers into ethically sourced, representative data with trustworthy labels.

### Tasks
- [ ] Prepare versioned question bank: `course_id`, `quiz_id`, `question_id`, explicit `question_type`, `max_score`, key/rubric version.
- [ ] Agree with supervisor on permission, voluntary participation / consent where needed, retention and access controls before collecting handwriting.
- [ ] Use the prepared printable handwriting quiz; create anonymous `writer_id` and `submission_id` (no names in research files).
- [ ] Collect correct, incorrect, partly correct, blank, crossed-out, uncertain, and varied handwriting examples.
- [ ] Annotate exact manual transcriptions **separately** from final marks; keep answer image linked by anonymous IDs.
- [ ] Have at least two human graders score a subset; adjudicate disagreements and record criterion-level essay marks.
- [ ] Split train/validation/test **by writer**, freeze an untouched test set before tuning; create question-disjoint test if claiming novel-question generalization.
- [ ] Write data dictionary, labelling instructions, provenance and license / privacy sheet.

**Owner:** AI Data/OCR owner + supervisor/TA.  
**Deliverables:** `dataset_v1` manifest, annotation guidelines, approved keys, verified transcripts, scored labels, privacy protocol, frozen splits.  
**Definition of done:** Label audit passes and the test set was not used to select thresholds or engineer V2 rules.  
**Dependency:** Phase 1 key/rubric validation; data collection authorization.

## Phase 3 — Question-specific graders & meaningful evaluation  [PARTIAL]
**Goal:** Compare suitable methods for *each* question type on the same relevant human-labelled benchmark.

### Workstreams
**A. MCQ — rule-based first**
- [x] Original V2 parses one clear A–D letter and reviews multiple/unsupported input.
- [ ] Evaluate cropped/verified transcriptions; test blank, ambiguity and OCR confusion.
- [ ] Check false auto-correct/false auto-incorrect as well as coverage.

**B. Short Answer (1–3 words)**
- [x] Normalization, approved variants, known-wrong contrasts and abstention in uploaded V2.
- [ ] Assess synonyms, negation, typos, abbreviations and course-specific vocabulary on independent labels.
- [ ] Only compare embedding/NLI or fine-tuning if the human-labelled baseline reveals a measurable problem and enough data exists.

**C. Math / equations**
- [x] Restricted parser + SymPy, numerical/unit checking, symbolic domain guard in V2 prototype.
- [ ] Clarify course-specific numeric precision/tolerance, units, assumptions, symbolic-domain policy.
- [ ] Separate single final answer from multi-step marking/partial credit; create dedicated rubric.
- [ ] Apply parser/resource limits and adversarial safety tests before service hardening.

**D. Descriptive / essay-like**
- [x] Earlier synthetic comparison: lexical TF-IDF, SBERT, NLI and rubric combinations.
- [ ] Fix inconsistent reference grades vs rubric criterion labels.
- [ ] Compare rubric-centric scoring to real human judgments; explicitly test contradictions, missing steps and unsupported statements.
- [ ] Select a candidate only after independent evaluation; no auto-final essay score at present.

**Metrics:** MCQ/short classification: accuracy, precision/recall/F1, false auto-decision, automation coverage; math: equivalence decisions + numeric error where applicable; scored responses: MAE, RMSE, QWK, review workload and runtime. Keep per-question-type tables; do not rank numbers with different metrics as a shared leaderboard.

**Owner:** Grading/NLP owner, Math owner, AI Lead.  
**Deliverables:** Per-type experiment matrix, versioned graders, failure taxonomy, evaluation report/model-or-rule card.  
**Definition of done:** Held-out human-labelled results + acceptable error/review trade-off + code and tests.  
**Dependency:** Phase 2. The existing typed prototype remains available meanwhile.

## Phase 4 — Handwritten quiz ingestion, OCR/HTR & Math OCR  [NOT STARTED]
**Goal:** Turn scanned answers into verified text or LaTeX *without losing the original image*.

### Tasks
- [ ] Design quiz page layout / answer region detection and per-question cropping; retain mapping to `question_id`.
- [ ] Add image orientation, quality, blur and readability checks; allow recapture/re-upload.
- [ ] Benchmark English handwriting OCR/HTR candidates (e.g., TrOCR) against exact human transcriptions.
- [ ] Benchmark math handwriting OCR/equation-to-LaTeX candidates (e.g., Mathpix as a candidate) separately.
- [ ] Compare CER, WER, exact-transcription rate, equation recognition, runtime, failure modes by handwriting quality.
- [ ] Build OCR validation UI: original crop next to extracted text and confidence/review reason; TA corrects uncertain text.
- [ ] Never turn a failed/low-confidence OCR transcription into an automatic zero.

**Owner:** OCR/Data owner + frontend liaison.  
**Deliverables:** OCR benchmark, image preprocessing code, region→question mappings, corrected-text feedback path.  
**Definition of done:** OCR errors quantified separately from grader errors, and the fallback works on ambiguous images.  
**Dependency:** Representative Phase 2 handwriting + Phase 1 quiz layout specification.

## Phase 5 — End-to-end grading pipeline & TA approval  [TYPED DEMO PARTIAL]
**Goal:** A complete, recoverable workflow from source answer to reviewed, approved grade.

### Already implemented in local demo
- [x] Typed question IDs → loaded question metadata → original V2 grader → result/reason/status.
- [x] `needs_review` yields `proposed_score: null` (not zero); a demo TA can enter final score.
- [x] Demo can distinguish proposed grade from final approval status.

### Remaining production-facing work
- [ ] Upload PDF/image → detect pages/answers → OCR → verified transcription → grading route → TA review → final grade.
- [ ] Store separate OCR confidence and grading decision, where meaningful; do not fabricate rule-based probabilities.
- [ ] Add per-item review queue, source image, rubric explanation, review edits and teacher override reasons.
- [ ] Add asynchronous jobs and statuses: `queued`, `ocr_processing`, `grading`, `needs_review`, `awaiting_approval`, `approved`, `failed`.
- [ ] Support retries, idempotency, duplicate submissions, timeouts, partial job failure and cancellation.
- [ ] Version image, transcription, rubric, grading engine, proposed score and TA edits in an immutable audit trail.
- [ ] Compare grading on clean text against grading from OCR outputs on the *same held-out records*.

**Owner:** AI Lead + OCR owner + Backend + Frontend.  
**Deliverables:** Pipeline orchestrator, review workflow, end-to-end dataset benchmark, QA scenarios.  
**Definition of done:** A handwritten quiz can be uploaded, OCR-verified, graded, human-approved and auditable without silently losing data.  
**Dependencies:** Phases 3 + 4; the typed-only route can keep evolving in parallel.

## Phase 6 — AI API & Frontend integration  [LOCAL DEMO RUNNING]
**Goal:** Let product teams build safely against a documented, stable AI-service contract, without waiting for OCR completion.

### Already implemented in this demo
- [x] FastAPI server at `http://127.0.0.1:8000` serving quiz and results UI.
- [x] `adapter.py` imports the user's **original** `grader_v2.py`, `grader.py` and `questions.json`.
- [x] `GET /api/v1/demo/quiz` returns questions **without the answer keys** (22 in full bank; 4 shown by default).
- [x] `POST /api/v1/demo/grade` runs the typed V2 and records an attempt in volatile server memory.
- [x] `POST /api/v1/demo/compare` compares Strict/V1/V2 for one typed answer.
- [x] `POST /api/v1/demo/attempts/{attempt_id}/items/{question_id}/approve` models TA sign-off; simple score bounds and duplicate-approval checks.
- [x] API documentation at `/docs`; local integration tests cover core behavior.

### Missing for actual integration
- [ ] Agree with Backend/Frontend on a production contract and ID ownership (`student_id`, `course_id`, `quiz_id`, `attempt_id`, `question_id`, status/review/error codes).
- [ ] Define separate image upload and long-running processing APIs; return job IDs and progress.
- [ ] Move attempt storage from an in-memory dict to Backend-owned persistent database with transaction boundaries.
- [ ] Add real login, TA authorization and object-level access checks: free-text reviewer name is not authentication.
- [ ] Keep reference keys and approved rubrics on protected server side; restrict data leakage and rate-limit endpoints.
- [ ] Add CORS **only for approved frontend origins** or configure a dev proxy (this demo currently uses same-origin static pages).
- [ ] Add frontend screens: upload, OCR edit, grading results, TA review queue, approval, audit history.
- [ ] Validate loading/retry/network failure, invalid and duplicate submissions, stale attempts, and accessibility/mobile behavior.
- [ ] Prepare versioned API examples, test fixtures, Postman/Swagger collection, error documentation and handoff checklist.

**Owner:** AI Integration Liaison + Backend Team + Frontend Team.  
**Deliverables:** API contract, sample payloads, mock/sandbox environment, QA checklist, persistent and authorized integration.  
**Definition of done:** Frontend can demonstrate correct/incorrect/review/approved/error flows through the real backend with authenticated roles and persisted auditable results.  
**Dependency:** Can proceed NOW, in parallel with Phases 2–4. The current working demo is an integration proof only.

## Phase 7 — TA assistant, optional quiz generation & final validation  [PLANNED]
**Goal:** Complete the authorized AI features, validate the integrated system and prepare a defensible graduation demo.

### Conversational assistant (in proposal)
- [ ] Define read-only TA intents: attendance summaries, quiz scores, course reports and authorized exports.
- [ ] Build restricted tools/functions exposed by the Backend, not direct unrestricted database access.
- [ ] Validate role filtering, prompt-injection defense, no hallucinated student scores and explanation of unavailable data.
- [ ] Introduce any write action only after permission check, explicit confirmation and audit logging.

### Quiz generation (earlier project discussion — reconfirm v1 scope)
- [ ] Confirm with supervisor whether PDF→question suggestions belongs in final v1; it is **not a demonstrated feature in the latest proposal**.
- [ ] If included: extract source → generate candidate questions → attach source/rubric → TA edits/selects → save approved quiz; evaluate fidelity and correctness.

### Final integration, quality & handoff
- [ ] User acceptance test with TAs using anonymous/consented representative quizzes.
- [ ] Measure reviewer time saved, review %, OCR+grader performance, latency, failures and resource usage.
- [ ] Document system boundaries (attendance QR and Excel synchronization owned by backend; AI only integrates with authorized data).
- [ ] Prepare system architecture diagram, comparison report, error analysis, demo scenarios and oral-defense explanations.

**Owner:** AI Lead + Backend + Frontend + supervisor/TA.  
**Deliverables:** Authorized assistant API, optional quiz generator decision, release checklist, final research report, working defense demo.  
**Definition of done:** Demonstrated, permission-aware features and honest held-out evaluation; no unsupported accuracy or security claims.

---

## Shared interfaces: how AI helps Frontend right now
1. **Question metadata contract:** ID, type, prompt/options, max score; keys stay in backend only.
2. **Result contract:** proposed score (nullable), reason, method/version, review flag and separate TA-approved final score.
3. **TA review UX:** show original answer and eventually image + OCR text; an unscored review is not zero.
4. **Async state design:** loading, processing, needs review, awaiting approval, approved, failed, retry.
5. **Test fixtures:** MCQ `Answer: B` correct; SA02 `freq` review; MA03 `2 Hz` correct; MA03 `2.000000001 Hz` review; E01 review.
6. **Security responsibilities:** backend enforces identity, object permissions, storage and keys; frontend hides only what user shouldn't see, not as sole security.
7. **Open items:** server runtime, image upload storage, mapping question crops, review comments and audit policy.

## Suggested owner assignments (adapt to team size)
| Work package | Main AI owner | Key collaborator |
|---|---|---|
| Research, standards, milestones, TA decisions | AI Lead | Supervisor / TA |
| Data & annotations | Data owner | TA reviewers |
| MCQ / Short / Essay NLP grading | NLP & grading owner | Data owner |
| Math numerical & symbolic grading | Math owner | Backend |
| OCR / handwriting / LaTeX | OCR owner | Data & Frontend |
| AI API and review contract | AI integration owner | Backend & Frontend |
| Chatbot and optional generator | NLP/assistant owner | Backend / TA |

## Next 2 short sprints (goals, not invented delivery dates)
### Sprint 01 — Stable handoff + research readiness
- [ ] Demo the *current* live V2: MC01 correct, SA02 `freq` review, MA03 correct, E01 review.
- [ ] Save screenshots/API payloads and compare Strict / V1 / V2 using `/docs`.
- [ ] Rerun previous experiment scripts and attach original report, commit and decision log.
- [ ] Meet Backend/Frontend and freeze provisional `Question`, `GradingDecision`, `Approval` JSON schemas.
- [ ] Get TA sign-off for question bank, scoring/rubric/aliases/numeric rules.
- [ ] Prepare ethical/approved handwriting collection and annotation package.

**Sprint 01 acceptance:** A teammate can run the same demonstration and describe why some cases go to TA review; frontend has agreed JSON examples and error states.

### Sprint 02 — Authentic evidence + first OCR benchmark
- [ ] After approval, collect a limited varied handwritten sample; attach anonymous IDs and exact human transcriptions.
- [ ] Human-score/resolve disagreements; freeze a truly untouched holdout.
- [ ] Measure typed V2 results on approved human labels; record false auto-decisions and TA workload.
- [ ] Run OCR-only baseline on the collected images; compare transcripts by CER/WER.
- [ ] Prototype OCR text confirmation → V2 grading while retaining original images.

**Sprint 02 acceptance:** First genuine end-to-end sample and a measurable OCR-only/typed-grader error report, clearly marked pilot scale.

## Cross-phase rules & definition of done
- **Never invent confidence:** original rule V2 returns `confidence: null`; do not paint a percentage in the UI.
- **Never call synthetic policy agreement real accuracy.** A held-out human evaluation is required.
- **Never finalize grades automatically:** TA approval is a separate state and needs verified authorization in the real system.
- **Don't train by default:** use model training only when baseline gaps, labelled data and measurable benefit justify it.
- Each Done task has: owner, relevant Git commit, data/model/rubric version, tests, results, failure examples, privacy note and reviewer.

**Suggested kanban:** Backlog → Ready → In progress → Experimenting → TA / Code review → Done.  
**Tracked per phase:** correctness, review burden, latency/cost, safety/authorization and integration blockers.


## 30 Oct — Phase 1/3 research handoff update
See `README_PHASE1_PHASE3_AR.md`, `docs/HANDOFF_STATUS_AR.md`, `docs/PHASE_3_EVALUATION_REPORT_AR.md`, the live `/research` interface and `research/results/observed_comparison.csv`. Existing Phase 1/3 checklists remain open where the actual TA approval, complete historical source CSVs and independent student labels are missing.
