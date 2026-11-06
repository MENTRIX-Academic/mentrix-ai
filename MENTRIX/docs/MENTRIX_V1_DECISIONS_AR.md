# MENTRIX V1 — Decisions frozen on 2026-11-03

## قرارات المستخدم (معتمدة كمواصفات، وليست ميزات تم تنفيذها)
- Dashboard roles: TA + Admin. Students use a *restricted* mobile Check-in only.
- Student authentication for attendance: Student ID + PIN (hashed, never plaintext); persistent authenticated session as applicable.
- Backend integration: Mock data first, then backend team APIs; do not train models on mock attendance records.
- Sample section size: 30 students; mobile connectivity available.
- Sidebar: Dashboard, AI Assistant, Quiz Grading, Attendance, AI Experiments, Settings.
- AI Assistant: tool/API retrieval and statistics from authorized platform records, not invented attendance counts.
- Quiz Grading: TA selects course, quiz, student, uploads **full answer sheet**. Use TA-approved question bank, answer key, rubric and course materials.
- Grading policy: automate ONLY externally validated clear cases; exception queue; human review of uncertain cases; publish in one controlled batch after checks.
- Attendance: Dynamic rotating QR + authenticated Student ID/PIN + randomized in-room checks; session-level TA control, manual exception handling, and audit history.
- AI: use legitimate Kaggle/public dataset training/evaluation for OCR and grading where fit to task. Independent human-labeled holdout before claims of real performance.

## Still to decide, not quietly assumed
- QR rotation duration, attendance window, late policy and minimum in-room checks.
- Batch upload vs single full sheet; QR signing/token expiry method and device/session safeguards.
- Identity link (course/section enrollment), TA administrative permissions, audit and retention policy.
- Rubric score ranges, rounding and override policy for each question type.
- Acceptance thresholds set *from data*, by error severity and coverage, not by arbitrary confidence.
- Full-page segmentation strategy and labeling protocol; Student ID recognition on full sheet.
- Commercial/noncommercial licenses for public datasets; final student privacy notice.

## Historical report (attached reference)
`docs/reference/Work Wrap up.pdf` is a user-supplied 13-page source summarizing synthetic and draft experimental comparisons (not proof of deployed model accuracy).

## Sprint 01 execution scope
Read-only audit + dataset ingestion tooling + reproducible baseline evaluation + smoke tests only. No website edits or production grading deployment.
