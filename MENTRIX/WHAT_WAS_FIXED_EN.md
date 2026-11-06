# MENTRIX — What was fixed

**This is the correct unified English website, not Original V2 Lab.**

- Dedicated address **http://127.0.0.1:8765/**. The old apps on port 8000/8010 cannot replace the new website at this address.
- Clear **GREEN EDITION · v4** label at the top and on the sign-in screen.
- New start file `START_MENTRIX_HERE.bat` with printed website address and error messages.
- `OPEN_CORRECT_WEBSITE.bat` opens the exact address.
- No Live Grading Demo or AI Work Roadmap in the new site.
- One workspace: Home, Students & Attendance, OCR & Grading, Assistant.
- The typed answer checker now accepts one selected question, not an old demo quiz.
- Grading questions, attendance lists, and OCR configuration now load **after staff sign-in**, preventing the old misleading `Staff sign-in required` loading error.
- Added website build identifier and cache-busting URLs to distinguish newer files.

**Testing:** The Python API and unit tests passed in this environment. HTML layout was checked by rendering a local static snapshot. Actual Windows `.bat` execution and real TrOCR inference still require a run on your PC.

**Safety:** Local research prototype. Student records are not safe for public hosting. Essay scores require human review; OCR text must be checked against the handwriting.
