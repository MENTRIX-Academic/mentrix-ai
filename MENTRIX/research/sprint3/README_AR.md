# MENTRIX Sprint 03 — ASAG on 646 real human-scored records

## Quick start على Windows
1. فك الضغط في **فولدر مستقل**، بدون Replace فوق فولدر Sprint 02.
2. داخل `MENTRIX_UNIFIED_CORRECT_SITE` اضغطي `RUN_ASAG_BENCHMARK.bat`.
3. افتحي `OPEN_ASAG_REPORT.bat` لعرض التقرير الملون في المتصفح حتى بدون تشغيل Python.
4. لو ظهر `ModuleNotFoundError`، افتحي PowerShell داخل نفس الفولدر وشغلي:
   `INSTALL_ASAG_DEPENDENCIES_ONCE.bat` (بديل PowerShell: `py -m pip install -r research/sprint3/requirements.txt`)
   وبعدها افتحي الـBAT تاني.
5. هتلاقي التقرير في `research/sprint3/results/asag_s03_report_AR.md`.
6. اختبارات الواجهة القديمة untouched. اختبار التجربة: `TEST_ASAG_SPRINT03.bat`.

> نسخة البيانات التي رفعتها المستخدم مدمجة هنا **كما هي بدون تعديل** في `research/sprint3/data/asag_dataset.csv`. لم نحتج تسجيل دخول Kaggle. لا تعيدي تنزيل ASAP-SAS.

## What was actually done?
- 646 سجلاً، 17 سؤالًا، 39 إجابة فارغة (كلها درجة 0)، 607 غير فارغة.
- تم **تشغيل** الـBaseline benchmark على ملف ASAG المرفوع، وتم حفظ Metrics وTest Predictions والـSplits.
- 7 baseline methods: `mean`, `tfidf_word_ridge`, `tfidf_char_ridge`, `token_overlap_knn`, `tfidf_word_knn`, `tfidf_char_knn`, و`reference_jaccard_ridge`.
- لكل سؤال تدريب وتقييم منفصلان؛ تم اختيار طريقة مناسبة للسؤال باستخدام Validation فقط.
- Split تقريبي 60/20/20، random seed 42؛ بنمنع التطابق الحرفي لنفس الإجابة في نفس السؤال عبر Train/Val/Test.
- درجات 0/1/2. نحسب MAE وQWK وExact Match. بنعرض Test الـ7 طرق لتوثيق المقارنة؛ مش بنختار على الـTest.

## Important limitations
- كل سؤال فيه 27–38 إجابة غير فارغة فقط، وعدد أسئلة 17؛ ده Pilot Benchmark مش تدريب واسع النطاق.
- Dataset إجابات مكتوبة إلكترونيًا ومطولة (متوسط ~58 كلمة)، وليست صور Handwriting، ولا هي مناسبة وحدها لتقييم 1–3 كلمات.
- تقييم بواسطة مصحح واحد؛ لا يوجد Student ID في الملف يتيح Student-disjoint partition.
- MinLM, NLI and Rubric-based historical experiments **haven't** been executed على الملف ده؛ الأرقام القديمة غير قابلة للمقارنة المباشرة معه.
- النتائج الجديدة **لا تثبت** صلاحية نشر درجات تلقائيًا. TA review remains mandatory for uncertain cases.
- بيانات الطلاب الـ30 التجريبية بالموقع لا علاقة لها بداتا تدريب/Benchmark هنا.

## Folder map
- Dataset: `research/sprint3/data/asag_dataset.csv`
- Runner: `RUN_ASAG_BENCHMARK.bat`
- Results: `research/sprint3/results/asag_s03_report_AR.md`
- Predictions (no student answer text): `research/sprint3/results/asag_s03_test_predictions.csv`
- Split manifest (sample IDs only): `research/sprint3/results/asag_s03_splits.csv`
- Metrics & source hash: `research/sprint3/results/asag_s03_metrics.json`

## Source & credit
- DigiKlausur: https://github.com/DigiKlausur/ASAG-Dataset
- GitHub repository reports MPL-2.0: https://github.com/DigiKlausur/ASAG-Dataset/blob/master/LICENSE
- Cite the original project/dataset when publishing results. See upstream license, do not interpret this benchmarking pack as a new license for the source data.

**No existing MENTRIX website files or old result files changed.**

- HTML report: `research/sprint3/results/asag_s03_report.html` (open with `OPEN_ASAG_REPORT.bat`).
