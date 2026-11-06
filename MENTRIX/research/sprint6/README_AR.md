# Sprint 06 — Handwriting OCR Development & Evaluation

**الحالة عند تسليم ZIP:** التنفيذ البرمجي + اختبار تكامل Synthetic/Mock مُنجز. **لم يحدث تشغيل فعلي للنموذج على IAM أو ورقة خط يد جديدة داخل بيئة التسليم** بسبب عدم توفر صور IAM المسجلة وأوزان TrOCR في البيئة. لذلك لا توجد CER/WER جديدة موثقة.

## اتنفذ إيه فعليًا؟

- `prepare_iam.py`: تحويل IAM lines.txt + XML إلى CSV مرجعي مع `writer-id` ومعرّف السطر والمصدر البشري؛ رفض تسريب الكُتاب Train/Validation/Test. لا يختار Split من تلقاء نفسه؛ يحتاج قوائم التقسيم الرسمية writer-independent.
- `benchmark.py`: مقارنة **نفس السطور ونفس الـGround Truth** عبر E01 Base RGB، E02 Base Autocontrast، E03 Small RGB، E04 Base Padded. يحسب corpus-level CER / WER / exact line rate وWriter guard وSHA256 ويرصد النصوص في ملف محلي. يختار أفضل CER على Validation فقط، والـTest يقيّم **الفائز الذي ثبت مسبقًا**. تغيير ملف Manifest بعد Validation يوقف اعتماد نتيجة Test.
- `full_sheet.py`: قراءة PDF أو صورة، اكتشاف سطور تقريبي، تجميعها حسب Q1/Q2… أو مناطق TA محددة مسبقًا، وإخراج Draft مع كل Bounding Box وتحذيرات، وصور Overlay يمكن فتحها من الواجهة لمراجعة مكان كل سطر. `evaluate_full_sheet` يقيس OCR، استرجاع معرفات الأسئلة، وIoU للمناطق **إذا كانت هناك annotations بشرية**، واتفاق قواعد التصحيح مع درجات بشرية **إذا توفر مفتاح/روبرك**.
- `handwriting_routes.py`: اختيار موديل OCR من واجهة Grading للورقة المرفوعة. تُحفظ مسودة مُعلّمة بأنها **غير مؤكدة** ويُصفّر `transcript_verified` وتُمسح درجات المسودة السابقة، ولا يُسمح بنشر درجات قبل مراجعة المعيدة ثم `verify-and-grade`.
- اختبارات Fake OCR على **صور مصطنعة مطبوعة** تؤكد أن الكود والمسارات تعمل، **وليست** اختبار دقة نموذج الخط اليدوي.

## 1 — تحميل IAM بشكل قانوني

**المصدر الرسمي:** <https://fki.tic.heia-fr.ch/databases/iam-handwriting-database>

1. سجّلي في IAM واحترمي ترخيص البحث غير التجاري، واستشهدي بـ Marti & Bunke (2002).
2. حمّلي أرشيف **line images** و`ascii/lines.txt` وملفات `xml/` وقوائم الـ **Large Writer Independent Text Line Recognition Task** الرسمية (`train`, `validation`, `test`).
3. **لا تضيفي IAM إلى GitHub عام أو تشاركي ملفاته داخل ZIP**، فالبيانات غير مضمنة هنا.
4. فكّي صور السطور داخل `research/sprint6/data/iam_lines/` بنفس البنية: `a01/a01-000u/a01-000u-00.png`، أو مسطحة `a01-000u-00.png`.
5. ضعي `lines.txt` في `research/sprint6/data/iam_meta/lines.txt` وXML في `research/sprint6/data/iam_meta/xml/` وSplit ID lists في `research/sprint6/data/iam_meta/`.

توليد Manifest (من PowerShell في جذر `MENTRIX`، بعد تشغيل `START_MENTRIX_HERE.bat`):

```powershell
.\.venv\Scripts\python.exe -m research.sprint6.prepare_iam `
  --lines-txt research/sprint6/data/iam_meta/lines.txt `
  --xml-dir research/sprint6/data/iam_meta/xml `
  --images-dir research/sprint6/data/iam_lines `
  --train-ids research/sprint6/data/iam_meta/train.txt `
  --validation-ids research/sprint6/data/iam_meta/validation.txt `
  --test-ids research/sprint6/data/iam_meta/test.txt `
  --output research/sprint6/data/iam_manifest.csv
```

**مهم:** أسماء ملفات التقسيم يمكن أن تختلف عند IAM؛ أعيدي تسمية القوائم التي نزلتيها وليس محتواها. بعض إصدارات IAM تستخدم Validation 1/2؛ حددي واحدة Validation، والأخرى لا تضميها إلى Test بشكل تلقائي. إذا ظهر Writer leakage، توقفي بدل تعديل الكود لإخفائه.

## 2 — تشغيل النماذج (نتائج فعلية فقط بعد تنفيذها)

1. `INSTALL_SPRINT06_OCR.bat` — يثبت Transformers/PyTorch في `.venv` وينزل الأوزان عند أول استدعاء للنموذج مع الإنترنت. **TrOCR-base أكبر من Small وقد يكون بطيئًا جدًا على CPU**.
2. `RUN_SPRINT06_CPU_SMOKE.bat` — 5 سطور فقط + Small، للتأكد من الجهاز؛ `partial_run: true` ويحفظ نتائجه في `results/diagnostics/` ولا ينتج Winner ولا يستبدل الـValidation العلمي.
3. `RUN_SPRINT06_VALIDATION.bat` — الأربع Pipelines على كل سطور Validation؛ يكتب `research/sprint6/results/selected_from_validation.json`، و`validation/validation_metrics.json`.
4. `RUN_SPRINT06_FROZEN_TEST.bat` — موديل الـWinner فقط على Test المجمد؛ يكتب `test/test_metrics.json`.
5. الإصدارات وبيئة التشغيل والـSHA-256 للـManifest **ولمحتوى الصور** محفوظة في JSON؛ راجعي Prediction CSV عند أي حالة سيئة.

**المعياران:** CER = عدد أخطاء Levenshtein على الأحرف / الأحرف المرجعية؛ WER = نفس الفكرة للكلمات. كلاهما **كلما قل كان أفضل** وقد يزيد عن 100% بسبب الإدخال الزائد. حرف كبير/علامة ترقيم محسوب، والمسافات المتكررة فقط تُوحّد. النتيجة هي Corpus Micro-average، وليست متوسط CER للأسطر.

**تنبيه منهجي:** نماذج TrOCR-handwritten نفسها Fine-tuned على IAM؛ IAM **In-domain benchmark** ولا يثبت جودة الورقة الجامعية المصرية أو خط طالب جديد، لذلك ضيفي صور متنوعة حقيقية وGround Truth مستقل (بعد الموافقات) ولا تستخدمي نفس صور تطوير السيستم كـHoldout.

## 3 — ورقة كاملة (خط يد)

بعد رفع الورقة في صفحة Grading اضغطي **Read handwriting with TrOCR**، واختاري pipeline. سيحاول تقسيم السطور والتعرف على `Q1:`, `Q2:`... في بداية السطر. لو فشل، استخدمي JSON الخاص بالـManual Regions (نموذج في `data/manual_regions_TEMPLATE.json`) مع إحداثيات Pixels. **الـPDF عند المعالجة يُرندر ×1.5**، وصفحة البداية index=0.

يمكن تنفيذ الاختبار من PowerShell أيضًا:

```powershell
.\.venv\Scripts\python.exe -m research.sprint6.full_sheet `
  --input "C:\Path\to\real_handwritten_paper.png" `
  --out research/sprint6/results/my_full_sheet_LOCAL_ONLY.json `
  --question-ids Q1,Q2,Q3,Q4 `
  --pipeline E01_base_rgb `
  --ground-truth-json research/sprint6/data/my_verified_full_sheet_gt.json `
  --question-bank-json research/sprint6/data/question_bank_TEMPLATE.json `
  --annotated-dir research/sprint6/results/my_overlays_LOCAL_ONLY
```

**القياس المستقل:** `evaluate_full_sheet` يقارن Transcript كل Q بنص بشري مستقل، ويحسب Recall/Precision لتعريف السؤال، ويقارن أداء سياسة التصحيح على نص بشري صحيح (Oracle) مقابل نفس السياسة على نص OCR المرشح — لتفريق خطأ القراءة عن خطأ الـGrading؛ لو أضفتِ `regions:[{question_id,page,bbox:[x0,y0,x1,y1]}]` إلى GT يحسب Mean IoU وRecall IoU≥0.5. ودرجات البشر `gold_grade` مع Question Bank فقط تسمح باختبار توافق قواعد التصحيح التشخيصي. **لا يتم التصحيح أو النشر مباشرة بناءً على OCR غير مراجَع**.

## 4 — حالة التحقق

- **مُنجز:** Pipeline code + API + UI + unit/integration tests + traceable instructions.
- **غير مُنجز عند التسليم:** IAM actual model inference، استخراج CER/WER حقيقية جديدة، تجربة خط يد ورقة كاملة، Ground Truth ورقة معتمد، قياس IoU مع annotation حقيقية، اعتماد grader على Holdout مستقل.
- **مطلوب من فريق المشروع:** الحصول على صور مرخّصة وموافقة TA والرخص، Annotation مستقلة وعينات بخطوط متعددة، وقت تشغيل CPU أو GPU، مراجعة Errors ثم التقييم المجمد، اعتماد Rubrics والتوقيع الرسمي.

## المصادر

- IAM official: https://fki.tic.heia-fr.ch/databases/iam-handwriting-database
- TrOCR Base model: https://huggingface.co/microsoft/trocr-base-handwritten
- TrOCR Small model: https://huggingface.co/microsoft/trocr-small-handwritten
- TrOCR paper implementation: https://github.com/microsoft/unilm/tree/master/trocr

## الخصوصية

`*_LOCAL_ONLY.csv` وOCR drafts تحتوي **نص إجابات طلاب** عند الاستخدام الحقيقي. لا تُرفعيها إلى مستودع عام، ولا تُنقلي معلومات شخصية إلى خدمات طرف ثالث. قواعد بيانات المشروع الحالية محلية وتجريبية وليست مصادقة إنتاجية.
