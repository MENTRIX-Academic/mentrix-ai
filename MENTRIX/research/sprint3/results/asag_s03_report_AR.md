# MENTRIX — Sprint 03 | ASAG Human-Scored Benchmark

**Status:** ACTUALLY EXECUTED on the uploaded `asag_dataset.csv`. No OCR experiment or website changes.

## Dataset profile

- Total **646** graded records from **17** questions.
- Nonblank answers for learned baselines: **607**. Blank answers excluded: **39**, each human-graded zero.
- Word count median: **53**, mean: **57.73**; only **1** answer(s) have 1–3 words.
- Score labels: {'0': 94, '1': 219, '2': 333}. SHA-256: `8ca6ff6f565997379fc2b6a591cf07809a968f0f2916250387db8feb2da1cc4d`.

## Held-out test results (same split and scale)

| Method | Macro MAE ↓ | Micro MAE ↓ | Pooled QWK ↑ | Exact match ↑ |
|---|---:|---:|---:|---:|
| token_overlap_knn | 0.3634 | 0.3566 | 0.4339 | 65.1% |
| mean | 0.4310 | 0.4264 | 0.3396 | 57.4% |
| tfidf_word_ridge | 0.4300 | 0.4264 | 0.3432 | 57.4% |
| tfidf_char_knn | 0.4338 | 0.4264 | 0.3381 | 58.9% |
| tfidf_word_knn | 0.4412 | 0.4341 | 0.3105 | 58.1% |
| reference_jaccard_ridge | 0.4468 | 0.4419 | 0.3175 | 55.8% |
| tfidf_char_ridge | 0.4531 | 0.4496 | 0.2865 | 55.8% |

### Validation-selected method per question

This strategy (selected separately per question on VALIDATION) achieved **Micro MAE 0.4264**, **pooled QWK 0.3476**, **exact match 58.1%** on **129** held-out nonblank answers.

| Question | Train | Val | Test | Selected (validation) | Test MAE | Test QWK |
|---|---:|---:|---:|---|---:|---:|
| 1 | 22 | 8 | 8 | tfidf_char_knn | 0.1250 | 0.7143 |
| 2 | 22 | 8 | 8 | token_overlap_knn | 0.1250 | 0.0000 |
| 3 | 20 | 7 | 7 | mean | 0.4286 | 0.0000 |
| 4 | 22 | 8 | 8 | token_overlap_knn | 0.0000 | N/A |
| 5 | 20 | 7 | 7 | token_overlap_knn | 0.1429 | 0.0000 |
| 6 | 22 | 8 | 8 | tfidf_char_knn | 0.6250 | 0.0909 |
| 7 | 22 | 8 | 8 | mean | 0.3750 | 0.0000 |
| 8 | 21 | 7 | 7 | reference_jaccard_ridge | 0.8571 | -0.1053 |
| 9 | 21 | 7 | 8 | tfidf_word_knn | 0.5000 | 0.1579 |
| 10 | 22 | 8 | 8 | tfidf_char_ridge | 0.7500 | 0.0000 |
| 11 | 22 | 8 | 8 | tfidf_word_knn | 0.1250 | 0.0000 |
| 12 | 18 | 6 | 7 | token_overlap_knn | 0.2857 | 0.6667 |
| 13 | 21 | 8 | 8 | tfidf_word_knn | 0.7500 | -0.5000 |
| 14 | 21 | 7 | 8 | tfidf_char_ridge | 0.6250 | 0.0000 |
| 15 | 21 | 7 | 7 | tfidf_char_knn | 0.5714 | 0.1250 |
| 16 | 21 | 7 | 8 | tfidf_char_knn | 0.3750 | 0.7000 |
| 17 | 15 | 6 | 6 | mean | 0.6667 | 0.0000 |

## How to interpret / إزاي نفسّر النتائج؟

- الأرقام أعلاه **حقيقية من تشغيل الكود على الملف المرفوع**، لكن حجم البيانات لكل سؤال صغير (27–38 إجابة غير فارغة).
- **النتائج مش مقارنة مباشرة مع أرقام Work Wrap up**؛ لأن الداتا وتقسيمها ومقياس الدرجات مختلفين.
- النماذج 7 Baselines خفيفة مناسبة للجهاز؛ مش MiniLM/NLI/Rubric models التاريخية، ومش Fine-tuning.
- Blank (39) مسار تصحيح rule-based منفصل؛ لم نحتسبها ضمن Test ML حتى لا ترفع الدقة ظاهريًا.
- تقسيم Train / Validation / Test بيمنع تطابق نفس نص الإجابة داخل نفس السؤال عبر المجموعات، لكن لا يوجد Student ID يساعدنا نعمل Writer/Student-disjoint split.
- نجاح Baseline هنا لا يسمح بتفعيل نشر الدرجات تلقائيًا، ولا يثبت قراءة OCR أو إجابات 1–3 كلمات.
- صاحب البيانات يصفها بأنها مناسبة للتصحيح المساعد Assissted وليس بديلًا للمراجع البشري.

## Next experiments

1. Error Analysis for incorrect, paraphrased and contradictory answers using manual adjudication.
2. Build an independent 1–3 word human-scored dataset for MENTRIX.
3. Evaluate actual Rubric+NLI and MiniLM on EXACT same split; report costs, review rate, and false approvals.
4. Separately evaluate TrOCR CER/WER on independently transcribed handwriting samples.

Outputs: `asag_s03_metrics.json`, `asag_s03_profile.json`, `asag_s03_splits.csv`, `asag_s03_test_predictions.csv`.
