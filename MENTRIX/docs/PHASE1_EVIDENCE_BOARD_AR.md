# Phase 1 — Evidence-based closeout board

| Ticket | المهمة | Evidence in this ZIP | الحالة الفعلية | Owner |
|---|---|---|---|---|
| P1-01 | Scope + module ownership | `docs/PHASE_1_AI_SCOPE_ARCHITECTURE_AR.md` | Prepared, formal approval pending | AI Lead + Supervisor |
| P1-02 | Inventory methods/models/pipelines | `docs/PHASE_1_METHOD_INVENTORY.md` | Prepared | AI Lead |
| P1-03 | Preserve original versions | `research/source_manifest.json`, source SHA256 pass | Verified in this runtime | AI Lead |
| P1-04 | Current code rerunnable | `REPRODUCE_PHASE1.py` + `reports/` | Verified in this runtime; teammate repeat pending | Research Owner |
| P1-05 | Historical 123/127 rerun | Only `research/data/stress_summary.json` + `summary.json` | BLOCKED: missing source case CSVs/test scripts | Research Owner |
| P1-06 | GitHub PR / team review | `.github/`, `docs/GITHUB_HANDOFF_GUIDE_AR.md` | Ready for manual push, not pushed | AI Lead |
| P1-07 | Real TA/Supervisor sign-off | `docs/TA_AND_SUPERVISOR_SIGNOFF_CHECKLIST_AR.md` | BLOCKED: needs authorized reviewers | TA + Supervisor |

### Phase 1 exit criteria
Only label Phase 1 **Closed** after P1-05, P1-06 and P1-07 are genuinely completed, and one team member reproduces the original benchmark on another device. Do not mark research archived summary as reproduced experiment.

### Phase 3 relationship
Current sample/engine/code comparison is ready. Full Phase 3 scientific exit remains blocked on independently human-labelled data and approved grading rubrics (Phase 2 dependency). No evidence of model fine-tuning, OCR, grading reliability on real students or production deployment is included.
