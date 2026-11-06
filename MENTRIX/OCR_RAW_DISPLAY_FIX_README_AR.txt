MENTRIX — Fix for empty OCR editor when a handwritten crop has no Q1/Q2 label
2026-11-04

Problem diagnosed from UI: the server reported 0/4 matched question labels,
although it warned about unassigned OCR lines. The original code ONLY put
question-assigned answers into extracted_text. Thus raw TrOCR lines were hidden.

What is fixed:
* Show all raw OCR lines separately, even with 0 question labels matched.
* When nothing matches, populate Editable OCR with raw recognized text.
* Include the original Q label in raw OCR preview (where a label was detected).
* Save raw_ocr_text, unassigned_lines and line_stats in the draft JSON.
* Show the saved raw OCR again when reopening an existing paper, including
  a draft saved by the previous version (read old 'lines' data).
* Keep question-answer fields empty when no question was matched.
* Never auto-grade OCR drafts without human transcription verification.

How to verify:
1. Close the MENTRIX terminal/server (Ctrl+C). Make a backup of MENTRIX first.
2. Apply the patch (if using the small patch ZIP) or open this full project.
3. Start START_MENTRIX_HERE.bat and login.
4. Open Quiz Grading -> Review & publish -> click the existing paper ID
   (or upload p01_region_01.jpg again). Any saved OCR draft should display
   a 'Raw TrOCR output' panel automatically; re-run TrOCR if there is no draft.
5. An IAM-style single crop does not contain Q1/Q2/Q3/Q4 markers, so 0/4
   question labels is expected. OCR words should be inspected in the RAW panel.
6. For whole-paper grading, use a complete paper with Q1/Q2/Q3/Q4 clearly
   written, or provide staff-labeled regions. Verify all text before grading.

Regression checks: 85 automated tests passed in the build environment,
including tests with stub OCR output. Real handwritten-model accuracy on the
user's image has NOT been independently measured by these tests.
