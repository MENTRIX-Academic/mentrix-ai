---
name: Validate grader against independent human labels
about: Phase 3 validation blocked by Phase 2 data & rubric approval
labels: ai, evaluation, p3
---
- [ ] Collect consented answers; use anonymous writer IDs
- [ ] Independent TA grade and transcription, with adjudication for disagreements
- [ ] Freeze writer-disjoint holdout before tuning
- [ ] Compare strict/V1/V2: per-type auto-coverage, unsafe auto correct, unsafe auto incorrect, manual review share
- [ ] Re-run essay comparison against consistent rubric labels; include MAE / QWK / failure cases
- [ ] Report runtime and compute cost; choose candidate with documented limitations
