# MENTRIX Original V2 → Frontend Handoff (corrected)

## What works in THIS local demo
- Backend serves its own static HTML/JS at `/`, so calls are same-origin.
- Question list: `GET /api/v1/demo/quiz` (default 4 IDs: `MC01`, `SA02`, `MA03`, `E01`; `?all=true` returns 22).
- Typed scoring: `POST /api/v1/demo/grade`, using **original** `grader_v2.py` through `adapter.py`.
- Compare rules: `POST /api/v1/demo/compare` returns `strict`, `v1`, `v2` decisions for one question.
- Review/approve endpoints are a **non-authenticated, RAM-only simulation**.

## Example typed request
```json
{"answers":[{"question_id":"MC01","answer":"Answer: B"},{"question_id":"SA02","answer":"freq"},{"question_id":"MA03","answer":"2 Hz"},{"question_id":"E01","answer":"A continuous signal varies with time."}]}
```

## Interpreting result rows
- `decision`: `correct`, `incorrect`, or `needs_review`.
- `proposed_score`: numeric when auto-graded; **null on needs_review (not zero)**.
- `confidence`: null; rule-based result has no validated confidence metric.
- `approval_status`: `pending_ta` until user hits demo `Approve score`; then `approved`.
- `final_score`: null before sign-off; backend checks `0 <= final_score <= max_score`.
- `grader_version`, `method`, `reason`, `attempt_id`: show/retain for reproducibility.

## React + FastAPI in separate local dev processes
This demo does **not** configure `CORSMiddleware`; do **not** assume that `localhost:5173` can call `localhost:8000` directly. Configure a Vite development proxy, or let backend configure a strictly allowlisted origin. Never enable an unrestricted CORS policy for authenticated real-student grading.

## Screens to implement in the real product
1. Quiz/courses workspace; 2. PDF/image upload and processing jobs; 3. OCR transcription correction; 4. Grading results; 5. TA review queue; 6. TA-approved finalization; 7. versioned audit/history.

## Integration contract questions for backend & AI lead
- Who owns `attempt_id`, `student_id`, `quiz_id` and `question_id`? How does system validate enrollment/permissions?
- How are PDF uploads stored and how do image crops map to question IDs?
- Which job states (`queued`, `ocr_processing`, `grading`, `needs_review`, `awaiting_approval`, `approved`, `failed`) are part of v1?
- What happens on retry, duplicate upload, timeout, corrected OCR text or regrade?
- How are model/rubric versions, grading reasons and the TA's override captured in the audit trail?
- Which approved answer keys/rubrics live on protected backend, and who can change them?

## QA to run as a team
- [ ] MC01 `Answer: B` → correct/1; MC01 `A` → incorrect/0; MC01 `A or B` → review.
- [ ] SA02 `frequency` → correct; SA02 `freq` → review/null; SA02 `period` → incorrect.
- [ ] MA03 `2 Hz` → correct; `2.000000001 Hz` → review.
- [ ] E01 remains review/null; don't display a fake AI-essay score.
- [ ] Approved final score is distinct from proposed; 409 on repeated approval and 422 on over-max scores.
- [ ] No answer keys exposed by quiz endpoint. Loading and failed network states visible.
- [ ] Confirm mobile layout and that real data is never used in this unauthenticated prototype.

**NOT production-ready:** No student authentication, object-level permission checks, persistent database, audit log, security hardening, uploads/OCR or calibration. No real student data should be entered.
