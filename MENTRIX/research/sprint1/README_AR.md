# MENTRIX | Sprint 01: OCR + Short Answer Evaluation

**الغرض:** تجهيز Pipeline اختبارات قابلة للتكرار على بيانات حقيقية، مع حفظ الكود القديم وواجهة الموقع كما هي.

## الحالة الحالية
- تم إنشاء أدوات تجهيز البيانات والتقييم واختبارها بأمثلة اصطناعية للاطمئنان أن الكود يعمل.
- **لم يتم تنزيل أي Dataset من Kaggle أو تشغيل Fine-tuning أو قياس نتائج على بيانات حقيقية.**
- لا تدخل أي نتائج جديدة إلى AI Experiments على أنها Accuracy إلا بعد تشغيل التقييم على Dataset موثوقة وتسجيل المصدر والإعدادات.

## التشغيل الأسهل على Windows

1. فك ضغط `MENTRIX_SPRINT01_WITH_PREVIOUS_WORK.zip` في فولدر عادي.
2. افتح فولدر `MENTRIX_UNIFIED_CORRECT_SITE` واضغط مرتين على `RUN_SPRINT1_CHECKS.bat`.
3. هتظهر نتيجة فحص الملفات واختبارات البرنامج. **ده مش تدريب ولا قياس دقة**.
4. لإنشاء حساب Kaggle وتحميل البيانات، اتبع `research/sprint1/DATASET_SOURCES.md` واحفظ الـAPI token على جهازك فقط.

## Short Answer: Kaggle ASAP-SAS (~50 words)

بعد تحميل ملفات مسابقة ASAP-SAS والموافقة على شروطها، استخرج `train.tsv` للفولدر:
`research/sprint1/data/asap/train.tsv`

ثبت الاعتمادات الاختيارية:

```powershell
py -m pip install -r research/sprint1/requirements.txt
```

جهز الداتا: (يمنع وقوع نص الإجابة المكرر في أكثر من Split للسؤال نفسه)

```powershell
py research/sprint1/prepare_asap.py --input research/sprint1/data/asap/train.tsv
```

اختبر baseline على تقسيم Train/Validation/Test. هيجرب متوسط الدرجة وTF-IDF words وTF-IDF chars، ويختار بالمجموعة Validation ثم يقيس الـTest مرة واحدة:

```powershell
py research/sprint1/evaluate_short_asap.py --input research/sprint1/data/asap_prepared.csv
```

ستجد `research/sprint1/results/asap_baseline_metrics.json` مع MAE وQWK لكل Prompt. هذه تجربة **جديدة منفصلة**، فلا تقارن أرقامها بأرقام تقرير Work Wrap up PDF القديم قبل توحيد الداتا ومعيار التصحيح.

مهم: Dataset دي مش اختبار ممثل لإجابات 1-3 كلمات، ولا هي معيار اعتماد لدرجات الطلاب. سوف نحتاج independent TA human labels لاحقًا.

## OCR: تقييم TrOCR / E01 على صور حقيقية

**بعد** استخراج نصوص ground truth يدويًا بشكل مستقل عن OCR والتأكد من writer IDs وتقسيمهم Train/Validation/Test من غير تداخل:

اكتب ملف CSV بترتيب الأعمدة الموجود في:
`research/sprint1/data/ocr_verified_template.csv`

- sample_id: كود صورة/سطر غير مكرر
- writer_code: نفس الشخص له نفس الكود في كل الصور (مهم!)
- split: train / validation / test (لا نفس الكاتب بين تقسيمين)
- ground_truth: نص تم نسخه ومراجعته بشريًا بشكل مستقل
- prediction: النص الذي أخرجه OCR كما هو

بعدها:

```powershell
py research/sprint1/evaluate_ocr.py --input research/sprint1/data/ocr_verified.csv
```

هيكتب CER وWER على الـTest، ومتوسط كل كاتب وأصعب العينات في `research/sprint1/results/ocr_metrics.json`. **لن يخترع نتائج** لو ملف الحقيقة المرجعية غير موجود. ولا يقيس OCR الخاص بالصور الكاملة تلقائيًا؛ هو يقيس توقعات جاهزة على مستوى الأسطر/الصور المقارنة.

أداة Fine-tuning GPU السابقة موجودة كما هي في `training/finetune_trocr_gpu.py`، ولا تُستخدم قبل وجود Ground Truth وتوثيق صلاحية الاستخدام وWriter-Disjoint Splits.

## ترتيب التجارب القادمة
1. Freeze خط الأساس TrOCR E01 Original RGB (إن توفرت original predictions + human GT).
2. تشغيل خط أساس OCR على IAM وتقييم CER/WER، قبل تدريب أي موديل.
3. تشغيل baseline Short Answer على ASAP-SAS (سؤال بسؤال).
4. تجميع **داتا 1–3 كلمات** بأسئلة معتمدة بشريًا لتقييم coverage وunsafe-auto decisions.
5. بعدها فقط: fine-tuning أو تعديل الـpipeline، وتوثيق مقارنة عادلة ونشرها في AI Experiments عند تنفيذ الواجهة.

## حدود أخلاقية وتقنية
- عدم رفع بيانات طلاب أو صور شخصية عامة على Kaggle/GitHub.
- لا تستخدم Synthetic Case Labels باعتبارها Human-Graded Validation.
- لا تستخدم أرقام confidence عشوائية لتحديد الحالات المسموح بالنشر التلقائي.
- حسابات Student ID + PIN وfull-page quiz processing مطلوبان للـV1 لكن غير منفذين في هذه الإضافة البحثية.
