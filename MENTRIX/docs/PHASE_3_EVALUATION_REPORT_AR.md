# Phase 3 — Typed grading comparison & open validation gates
**Research prototype / no real-student labels / no final model selected.**

## Experiment 1: historical descriptive benchmark (from uploaded report, NOT rerun)
- 5 descriptive questions and 25 assistant-generated answers; 7 reported lexical/model/rubric variants.
- Reported MAE / QWK: Rubric+NLI 1.5200 / 0.4794; MiniLM+NLI 1.6058 / 0.4597; Rubric+SBERT 1.6800 / 0.3031; Token Overlap 1.7821 / 0.3404; TF-IDF character 1.8217 / 0.3023; TF-IDF word 1.9839 / 0.2702; SBERT MiniLM 2.0616 / 0.2991.
- **No winner:** Rubric+NLI recorded a severe 5/5-to-0/5 error and 24/25 cases referred for review. The pilot labels were not fully consistent with criterion-level scores.

## Experiment 2: historical typed synthetic stress report (copied, NOT rerun)
- 123 assistant-authored policy cases: MCQ=27, short=47, math=49.
- Strict 37/123=30.1%, V1 100/123=81.3%, V2 123/123=100% agreement **against authors' policy labels**, not held-out student scoring.
- V2 auto 72/123 (58.5%) and review 51/123 (41.5%). V1 review 38/123. Historical 24 unit tests + 500 malformed string probes reported but original cases/tests unavailable, so not reproduced in this pack.
- An earlier 127-case typed synthetic comparison is historical, not valid independent validation.

## Experiment 3: new *reproducible illustrative demo matrix* (rerun in this pack)
- `research/data/curated_demo_cases.csv` contains 29 **assistant-authored** cases spanning MCQ, short, math, descriptive.
- Run `py research/compare.py`, inspect `research/results/observed_comparison.csv` and `observed_summary.json`.
- Strict/V1/V2 are invoked from the **original grader source**. This verifies wiring and policy behavior, *not scientific accuracy*. Do **not** report the match rate as model accuracy.

## Current provisional decisions
| Type | Prototype choice | Why | Human-validation need |
|---|---|---|---|
| MCQ | V2 rules | Clear single option; no heavy NLP | Handwritten ambiguous-choice data + false-auto rate |
| Short (1-3 words) | V2 aliases + known-wrong + review | Prevent unreviewed false negatives on unknown synonyms | Independent TA labels & alias review; measure reviewer time |
| Math | V2 restricted parser + SymPy | Equivalence/units with conservative domain/precision cases | TA policy for numerical tolerance, domain, multi-step rubric |
| Essay / Descriptive | TA-only now, Rubric+NLI/SBERT as *candidates* | Historical synthetic trial too weak to select | Independent criterion scores; contradictions; held-out MAE/RMSE/QWK |

## Valid metrics to collect later
- Classification: auto-decision confusion, unsafe auto-correct, unsafe auto-incorrect, review rate, coverage, accuracy on **automatic subset** together with coverage.
- Scored questions: MAE, RMSE, QWK, error severity, response time; don't mix categorical policy agreement and essay numerical grades.
- OCR measured independently CER/WER; end-to-end as separate experiment.
- Split by student/writer and (when needed) by unseen question. Keep untouched holdout frozen before tuning.

## What remains blocked for formal completion
1. Actual TA sign-off of keys, aliases, wrong contrasts and rubric.
2. Human-scored real or independently created answers with frozen writer-disjoint holdout; no leakage.
3. Essay rubric consistency correction and actual re-run with human labels.
4. Numerical precision, units, domain, partial credit policies and review cost thresholds approved.
5. Package-wide independent laptop reproduction / Git commit and review.

**Phase 3 engineering baseline/research paperwork is ready; scientific model selection / accuracy claims remain BLOCKED.**
