---
name: Recover original experiment artifacts
about: Phase 1 blocker - historical case/test reproduction
labels: ai, research, p1
---
## Problem
Historical 123 stress cases and 24 original tests are documented by aggregated results, but their original inputs are absent from the handoff package.

## Attach source originals (do not synthesize replacements)
- [ ] `stress_cases.csv` (123 authored cases)
- [ ] `synthetic_cases.csv` (127 earlier authored cases)
- [ ] `test_grader.py` (original tests)
- [ ] `test_v2.py` (original tests)
- [ ] Versions / checksums / original timestamps documented

## Acceptance criteria
- [ ] Old `run_stress.py` and `run_pilot.py` rerun on original CSVs
- [ ] Old unit tests reproduce historical count; report exact environment and git commit
- [ ] Results distinguished from new 29-case illustrative benchmark
