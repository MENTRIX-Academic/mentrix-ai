# Sprint 02 Status — 2026-11-03

- **Done:** code for a six-baseline comparison, 70/15/15 prompt-wise duplicate-group split via Sprint 01, per-prompt test MAE/QWK, error CSV, validation selection, full reproducibility metadata.
- **Done:** tests on programmatically generated fake rows; those rows do NOT indicate model quality.
- **Blocked pending authorized input:** Kaggle's ASAP-SAS competition `train.tsv` cannot be downloaded without sign-in + competition-rule acceptance. Hence no real benchmark metrics have been generated or claimed.
- **Not yet done:** training TrOCR on IAM; OCR CER/WER on human-verified Kaggle or IAM samples; Rubric+NLI comparative rerun on the same Kaggle dataset; 1-3-word calibration on MENTRIX-specific human graded answers.
- **Safeguards:** never overwrite old experimental results, don't output fake accuracy numbers, don't publish student scores, keep all student login and database work out of this research-only sprint.
