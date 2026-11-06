# MENTRIX — Phase 1 & Phase 3 Research Handoff

**What's here?** A copy of your previously working FastAPI original-V2 demo plus a `/research` comparison page, 29 new assistant-authored illustrative cases, working comparison runner, test suite, baseline/provenance reports, decision log and TA signoff checklist. The original `grader.py`, `grader_v2.py` and `questions.json` are unchanged byte-for-byte. Existing `/`, `/roadmap`, `/docs` preserved.

## Start on Windows
1. Extract ZIP, open `MENTRIX_AI_Phase1_Phase3_Research_Pack` folder.
2. First stop earlier PowerShell process using `Ctrl + C` (port 8000).
3. Run `START_V2_DEMO.bat` (or in PowerShell `py -m pip install -r requirements.txt` and `py -m uvicorn app:app --reload`).
4. Open `http://127.0.0.1:8000/research` for live comparisons, and `http://127.0.0.1:8000/` for existing demo.
5. To regenerate observations, run `py research/compare.py`.
6. To run tests: `py -m unittest discover -s tests -v` and `py -m unittest discover -s research/tests -v`.

To present to the team, open `docs/PHASE_1_3_PRESENTABLE_REPORT_AR.html` in any browser, and print from the browser if useful.

## Open documents in this order
- `docs/V1_V2_EXPLAINED_AR.md`
- `docs/PHASE_1_AI_SCOPE_ARCHITECTURE_AR.md`
- `docs/PHASE_1_METHOD_INVENTORY.md`
- `docs/PHASE_3_EVALUATION_REPORT_AR.md`
- `docs/PHASE_1_3_DECISION_LOG.md`
- `docs/TA_AND_SUPERVISOR_SIGNOFF_CHECKLIST_AR.md`
- `docs/HANDOFF_STATUS_AR.md`

## Important caution
- **Scientific Phase 3 is NOT validated/completed** without TA-reviewed labels and held-out samples.
- The historical 123 authored synthetic stress cases and 24 tests were reported earlier but their source CSVs/test scripts were not provided in this request; only summary outputs are available. New 29 examples are different, assistant authored, *not human labels*.
- No OCR, model training, authenticated TA approval, production security, persistent student grades or genuine student data.
