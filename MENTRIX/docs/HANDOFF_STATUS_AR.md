# Phase 1 + Phase 3 status — actual deliverables vs dependencies

## Completed in this research pack
- Formal AI scope, module architecture, question type taxonomy and AI/Backend/Frontend boundaries documented.
- Methods/models/pipelines inventory and V1/V2 technical explanation written.
- Source originals preserved exactly, SHA256 manifest created.
- Self-contained new 29-case **illustrative** design matrix; rerunnable Strict/V1/V2 comparison producing per-case decisions and reasons.
- Historical study values copied with provenance and caveat; not falsely re-run.
- Current recommendation matrix by question type, failure taxonomy and open decision log.
- TA/supervisor signoff checklist and blank human-holdout evaluation template.
- Integrated webpage `/research` allows direct compare input without overwriting demo.

## External gates STILL OPEN (cannot mark fully complete)
- TA/supervisor actual approval of answers, scoring rules and rubrics.
- Complete original `synthetic_cases.csv`, `stress_cases.csv`, `test_grader.py`, `test_v2.py` needed to reproduce exact historical 24 tests and 123-case benchmark.
- New real (or independent human-labeled) dataset collected with permissions and frozen holdout.
- Validated essay model experiment using consistent independent criterion labels.
- Independent laptop reproduction and Git commit/PR review.

## Recommendations for leadership
Mark P1 = **Engineering package prepared; waiting formal sign-off/reproduction**. Mark P3 = **Typed experimental prototype completed; scientific evaluation blocked by Phase 2 and rubric signoff**. Do not mark these milestones as fully 'validated' or model-ready.

## Quick commands (Windows)
```powershell
py -m pip install -r requirements.txt
py research/compare.py
py -m unittest discover -s tests -v
py -m unittest discover -s research/tests -v
py -m uvicorn app:app --reload
```
Open http://127.0.0.1:8000/research to compare Strict, V1 and V2 live.
