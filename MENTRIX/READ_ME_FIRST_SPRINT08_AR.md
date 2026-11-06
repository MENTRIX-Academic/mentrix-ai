# MENTRIX — Sprint 08: تقييم حقيقي للـHandwriting OCR

## أهم فرق بين الاختبار البرمجي وتجربة خط اليد

**اختبار الـcode مش معناه إن TrOCR بيقرأ خط اليد بدقة.** لازم ملف IAM أصلي بعد التسجيل، والنص المرجعي لكل سطر، وبعدها تشغيل الموديل، وقراءة CER / WER من ملفات النتائج الجديدة. ما فيش في الـZIP ده IAM ولا أوزان موديل Hugging Face؛ ومفيش رقم CER/WER علمي جديد نقدر ننسبه لنفسنا.

## ترتيب التشغيل على Windows

1. فكّي الـZIP، وافتحي `MENTRIX` وشغّلي `START_MENTRIX_HERE.bat`؛ هيشغل الموقع المحلي.
2. لو هدفك مجرد اختبار الموقع، اختاري `RUN_SPRINT08_CODE_TESTS.bat`. هو **مش** قياس الخط اليدوي.
3. سجّلي رسميًا في [IAM Handwriting](https://fki.tic.heia-fr.ch/databases/iam-handwriting-database) واحصلي على `lines.tgz` و`ascii.tgz` و`xml.tgz` وقوائم الـ **Large Writer Independent Text Line Recognition Task**.
4. استخدمي قوائم Train / Validation 1 / Test الرسمية (اختاري واحدة للـValidation، واحفظي Validation 2 منفصلة للتطوير أو التقييم المستقل؛ لا تخلطيها مع Test). لا تعدلي writer IDs أو النصوص المرجعية.
5. فكّي الصور داخل `research/sprint6/data/iam_lines/`، و`lines.txt` وXML والقوائم داخل `research/sprint6/data/iam_meta/`. راجعي المسارات أدناه.
6. جهّزي الـManifest بالأمر الجاي من PowerShell في جذر MENTRIX:

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

7. شغّلي `RUN_SPRINT08_CHECK_DATA.bat` — يتأكد من ملفات الداتا وأن كل Writer موجود في Split واحد فقط وأن الملفات مشتركة بين الـSplits مش متكررة. إذا فشل، أصلحي البيانات بدل تعطيل الحماية.
8. شغّلي `INSTALL_SPRINT06_OCR.bat` لتنزيل المكتبات؛ أول تشغيل للـmodels يحتاج إنترنت ووقت ومساحة RAM/VRAM مناسبين.
9. للتأكد من الجهاز فقط، شغّلي `RUN_SPRINT06_CPU_SMOKE.bat` (خمسة سطور، موديل Small، **تشخيص فقط**).
10. شغّلي `RUN_SPRINT08_REAL_VALIDATION.bat` — الأربع Pipelines على نفس Validation بشكل كامل. هيطلع ملف `validation_metrics.json` و`validation_error_analysis_LOCAL_ONLY.json` فيه مقارنة حسب كل Writer والسطور الأكثر خطأ. لو تجربة جزئية مش هيتولد Winner.
11. **مرة واحدة فقط** بعد اكتمال الـValidation، شغّلي `RUN_SPRINT08_FROZEN_TEST.bat` — يختبر الـWinner فقط على Test. بعد نجاحه، امتنعوا عن إعادة اختيار موديل بناء على Test.
12. افتحي الموقع، Upload ورقة بخط يد فعلًا، `Quiz Grading` → `Read handwriting with TrOCR` → `Compare original handwriting with OCR`. الواجهة ترشح Pipeline الفائز من Validation لو ملف النتائج الحقيقي موجود وسليم؛ وإلا E01. ممكن تختاري واحد يدويًا.
13. لو Q1/Q2 مش متعرف عليهم صح، حددي مستطيلات مناطق الإجابات، اعملي OCR تاني، وصححي النص جنب الصورة. ثم `Verify & grade` ثم Review ثم Batch Publish، من غير تصحيح تلقائي قبل المراجعة.

## صفحة بخط يد حقيقي + Ground Truth منفصلة

* صور الأوراق الأصلية تبقى خاصة، وما ترفعيش أسماء طلاب أو بياناتهم لأي repo عام.
* جرّبي من الـPowerShell بعد التأكد من تثبيت TrOCR (غيّري المسار وQIDs حسب أسئلتك):

```powershell
.\.venv\Scripts\python.exe -m research.sprint6.full_sheet `
  --input "C:\papers\student_handwritten.png" `
  --out "research/sprint6/results/paper01_draft_LOCAL_ONLY.json" `
  --question-ids Q1,Q2,Q3,Q4 `
  --pipeline E01_base_rgb `
  --line-detection smart `
  --annotated-dir "research/sprint6/results/paper01_overlay_LOCAL_ONLY"
```

* لمساعدة مُراجِع مستقل على التفريغ البشري، أنشئي **قالبًا فارغًا** لا ينسخ النص المتوقع من OCR:

```powershell
.\.venv\Scripts\python.exe -m research.sprint8.ground_truth_template `
  --draft "research/sprint6/results/paper01_draft_LOCAL_ONLY.json" `
  --output "research/sprint6/results/paper01_GT_BLANK_LOCAL_ONLY.json"
```

* يُراجع شخص مستقل الصورة الأصلية ويكتب `transcription` و`verified_by` و`question_id` لكل سطر في `lines`، ويُصحح `bbox` لو سطر ناقص أو مقصوص، ويضيف أي سطر لم يكتشفه النظام. ويدخل النص الصحيح لكل سؤال في `questions`; لو توفر تصحيح بشري معتمد، يضع `gold_grade` ويضيف بنك الأسئلة المعتمد.
* بعد اكتمال القالب، أعيدي تشغيل `full_sheet` بنفس الورقة و`--ground-truth-json` و`--question-bank-json` لو موجود. القياسات هتظهر داخل ملف المسودة تحت `evaluation`:
  - `independent_line_evaluation.line_detection`: Precision/Recall/F1 + IoU بعد matching سطر-لسطر.
  - `independent_line_evaluation.recognition_on_matched_lines`: CER/WER للسطور اللي اتعرف مكانها؛ السطور المفقودة منفصلة، ومش بيتضحك على النتائج.
  - `independent_line_evaluation.question_mapping_on_matched_lines`: هل السطر مربوط بالسؤال الصح.
  - `ocr_metrics`: CER/WER للنص المجمّع لكل سؤال، بما فيه السطور التي ضاعت.
  - `grading_diagnostics`: القواعد على الإجابات البشرية الصحيحة مقابل إجابات OCR غير المتحقَّق منها، بشكل تشخيصي فقط.

## أربع Pipelines موجودة بالفعل

| ID | Model | معالجة الصور |
|---|---|---|
| E01 | TrOCR Base Handwritten | Original RGB — Baseline |
| E02 | TrOCR Base Handwritten | Autocontrast |
| E03 | TrOCR Small Handwritten | Original RGB |
| E04 | TrOCR Base Handwritten | Padding + conditional upscale |

اختيار الأفضل من *Validation CER* وWER لكسر التعادل، وليس من التوقعات أو اختبارات البرمجة. **مهم:** Base وSmall اتدربوا/اتضبطوا أصلًا على IAM؛ نتيجة IAM اختبار in-domain وليست دليل تعميم على أوراق كويز فعلية. نحتاج Holdout بورق حقيقي من كتاب جدد لم يشوفهم التطوير، وموافقة الاستخدام والتفريغ المستقل.

## حدود مثبتة

- الـPipeline والشبكة وAPI والـUI موجودين من Sprint06/07؛ Sprint08 يضيف تدقيق البيانات، اختيار آمن، Error Analysis حسب الكاتب، ومقاييس مستقلة للسطور.
- الموديل الحقيقي وأوزانه وIAM غير مرفقين. لا يوجد CER/WER جديدة حتى التشغيل الفعلي، ولا تصحيح تلقائي آمن قبل اعتماد الترانسكربت.
- اختيار الفائز في الموقع يعتمد على نتيجة Validation مسجلة كاملة ومتسقة في ملفات محلية؛ مازال يلزم فحص Human Holdout قبل الاعتماد العلمي.
- البيانات الخاصة داخل `local_private_data` لا تُعبأ في هذه النسخة المخصصة للتسليم؛ التطبيق ينشئ DB جديدة عند أول تشغيل.

## مراجع بحثية

- IAM official: https://fki.tic.heia-fr.ch/databases/iam-handwriting-database
- TrOCR Base: https://huggingface.co/microsoft/trocr-base-handwritten
- TrOCR Small: https://huggingface.co/microsoft/trocr-small-handwritten
- Official TrOCR: https://github.com/microsoft/unilm/tree/master/trocr
