# MENTRIX V1 — Mock API contract (design proposal, NOT implemented backend)

**Locked decisions:** TA and Admin access the dashboard; students only access a restricted mobile attendance check-in; Student ID + PIN; one section contains around 30 students; rotating QR + authenticated student check-in + random physical checks; 30 fictional students for initial demonstrations; full quiz answer sheet OCR and grading is planned; approved answer keys/rubrics and materials are prerequisites; auto-score clear cases, human review exceptions, then batch publication.

**Do not confuse data sources:** `s05_mock_backend_data.json` is a fictional web/API sample. `asag_dataset.csv` is human-scored research data for model evaluation. Never merge them as if they represent enrolled students.

## Proposed API endpoints (not yet developed)

- `POST /api/auth/student-login`: `student_id`, `pin`; server-side validation with salted memory-hard PIN/password hash (Argon2id or similar); rate-limit and lockout; session binding; never log PIN.
- `POST /api/attendance/sessions`: TA/Admin only; course, section, room, scheduled duration; return session ID. Backend signs short-lived nonreplayable QR tokens; rotate every ~30 seconds; last-five-minute check-in is configurable.
- `GET /api/attendance/sessions/{session_id}/qr`: TA/Admin only; QR token + expiry. No Student ID is embedded in the QR itself.
- `POST /api/attendance/sessions/{session_id}/check-in`: authenticated student with QR token. Verify membership, expiry, single check-in, close time, block replay. Recording a check-in is not absolute proof of physical presence.
- `GET /api/attendance/sessions/{session_id}/summary`: TA/Admin only; present/absent/pending/flagged + timestamp/attendance audit trail. Absent is final only after the session closes and records are reconciled.
- `POST /api/attendance/sessions/{session_id}/random-check`: TA/Admin only; store who was checked, evidence of result, and reason for corrections.
- `GET /api/assistant/query`: design concept only; permission-restricted backend-controlled functions for counts, attendance lists, missed quizzes, and reports; parameterized queries; never unrestricted model-written SQL.
- `POST /api/grading/jobs`: TA/Admin; course + quiz + student + full-sheet PDF/image; validated approved rubric/key/material IDs. Return job status; async OCR and question segmentation design still pending.
- `GET /api/grading/jobs/{id}`: status and extracted answers, per-question provisional scores, flags and reasons.
- `POST /api/grading/reviews/{id}`: resolve exception with TA action and audit log.
- `POST /api/grading/batch-publish`: TA/Admin only; explicit action after exception handling and grade review. No silent grade publication.

## Pending decisions

- Actual backend stack and database schema, authorization framework, and official section enrollment source.
- Who can publish grades (TA vs Admin); audit retention and permission levels.
- QR clock-skew tolerance, offline fallback, duplicate/device rules and random-check sampling procedure.
- Explicit scoring rubrics for MCQ, 1–3-word answers, Essay and Math; minimum human-verified performance criteria before automatic approval.
- Privacy review before using any actual student information.

The mock data contains no real PIN or student identifiers, and no QR tokens. It is suitable only for integration/UI fixtures.
