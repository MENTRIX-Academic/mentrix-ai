# Candidate data sources (verified 2026-11-03; not downloaded)

| Task | Source | Status | Important condition |
|---|---|---|---|
| Handwriting OCR | [IAM official](https://fki.tic.heia-fr.ch/databases/download-the-iam-handwriting-database); [IAM word Kaggle mirror](https://www.kaggle.com/datasets/nibinv23/iam-handwriting-word-database) | Source located, download NOT attempted | Original IAM requires non-commercial research use & asks registration. Inspect mirror file/metadata; writer IDs need verification. Word images are not full quiz pages. |
| Student answer grading | [ASAP-SAS competition](https://www.kaggle.com/competitions/asap-sas/data) | Verified Kaggle file structure; download NOT attempted | Competition account must accept rules. `train.tsv` labels are human scores; average response ~50 words, *not* 1-3 words. |
| Essay, later | [AES 2.0](https://www.kaggle.com/competitions/learning-agency-lab-automated-essay-scoring-2/data) | Future | Kaggle competition page declares CC BY-NC 4.0. Not for Short Answer 1-3. |
| Math, later | [HME100K](https://www.kaggle.com/datasets/cutedeadu/hme100k) | Future | Image -> LaTeX; not a grading score dataset; large download. |

License, attribution and data privacy require project-specific review before distribution or training. Don't upload student images to a public repository.

## Authenticated Kaggle commands to run on your PC (optional, after terms accepted)

```powershell
py -m pip install kaggle
kaggle competitions download -c asap-sas -p research/sprint1/data/asap
kaggle datasets download -d nibinv23/iam-handwriting-word-database -p research/sprint1/data/iam
```

Unzip the competition archive locally, then check it includes `train.tsv` (some file paths or naming may differ).
Read the competition rules on Kaggle first and generate your own API token privately. Never share `kaggle.json`.

For **real 1-3 word answer grading**: Prepare a separate TA-approved question/key/answer/label dataset, and preserve ambiguous responses and unknown synonyms. No claim that ASAP-SAS validates this task.
