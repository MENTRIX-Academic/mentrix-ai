# MENTRIX / TAFlow — Sprint 08
## Handwriting OCR Development & Evaluation — Implementation Report

**تاريخ التسليم:** 5 نوفمبر 2026  
**المصدر:** تكملة Sprint 07 المرفوع، وليس إعادة كتابة المشروع من الصفر.  
**نتيجة الاختبارات النهائية:** `105 passed` من الأمر `python -m pytest -q`، وفحص صياغة JavaScript نجح. التفاصيل موثقة في `docs/SPRINT08_EXECUTION_STATUS.json`.  
**حالة الـML:** تم تجهيز مسارات التجارب والتقييم المنهجي وربطها بالواجهة؛ **لم نُشغّل هنا IAM المقيَّدة بالتسجيل أو أوزان TrOCR فعلًا**، ولا يجوز اختراع CER أو WER أو تعيين Winner من دون نتائج حقيقية.

## 1. أين كنا قبل التعديل؟

- Sprint 06: استيراد IAM رسمي، أربع Pipelines E01–E04، حساب CER/WER على سطور موثَّقة، فصل تجارب Validation عن Frozen Test، استخراج سطور الورقة، وربط المسودات بمسار مراجعة المعيدة والتصحيح الآمن.
- Sprint 07: تحسين اكتشاف السطور الذكي وإزالة الميل المحدود من الصور ومراجعة السطر جنب الصورة الأصلية وتحديد مناطق السؤال بالماوس؛ كانت اختبارات محاكاة/Printed Synthetic فقط. سطر OCR غير المربوط بسؤال لا يختفي من الواجهة.
- لم تكن هناك بيانات IAM حقيقية في الملفات المرفوعة، أو Ground Truth جديد للورقة الكاملة. لذلك لا يوجد دليل كافٍ على دقة القراءة في مشروع التخرج عند بدء هذه المرحلة.

## 2. ما الذي نفذناه في Sprint 08؟

| الوحدة | التنفيذ الفعلي | الهدف/طريقة الاختبار |
|---|---|---|
| Dataset audit | `research/sprint8/preflight.py` | التحقق من وجود صور وGT ومعرّفات الكُتّاب وقوائم Train/Validation/Test؛ اكتشاف Writer/path leakage؛ حساب SHA-256 لملفات المرجع ومحتوى صور التقييم |
| IAM importer | **الإبقاء على** `research/sprint6/prepare_iam.py` | استخدام بيانات IAM الرسمية المسجلة؛ لا يتم تنزيل ملفات الترخيص تلقائيًا أو استبدال الكاتب ببيانات تخمينية |
| Paired comparison | **تقوية** `research/sprint6/benchmark.py` | أُضيف قياس زمن كل Pipeline؛ وجوب مقارنة الأربع على Validation كاملة قبل Winner؛ منع Test جزئي وإعادة تشغيل Test النهائي عن طريق نفس مسار النتائج، وفحص اتساق اختيار Winner مع نتائج Validation الفعلية |
| Error analysis | `research/sprint8/error_analysis.py` | تحليل CER/WER لكل Writer، مقارنة E02/E03/E04 بـ E01 على نفس Line IDs، استخراج سطور الأخطاء الأكبر، ومنع تحليل Mock على أنه نتائج علمية أو استخدام Test للـmodel selection |
| Ground Truth template | `research/sprint8/ground_truth_template.py` | إنتاج ملف Annotation **فارغ** للورقة، لا ينسخ تنبؤات OCR إلى النص المرجعي؛ ليملأه مراجع مستقل بناء على الصورة الأصلية |
| Line-level metrics | `research/sprint8/line_evaluation.py` | one-to-one IoU matching: Line Detection Precision/Recall/F1، ثم CER/WER للسطور المطابقة فقط، ثم Question-ID exact mapping؛ توضيح السطور المفقودة/الزائدة بدل إخفائها |
| Full-page evaluation | **تحديث** `research/sprint6/full_sheet.py` | دمج `independent_line_evaluation` مع CER/WER على مستوى إجابات الأسئلة وRegion IoU والتصحيح التشخيصي المؤسَّس على درجة بشرية مستقلة عند وجودها |
| Integration | **تحديث** `handwriting_routes.py` و`static/workspace.js` | الموديل المختار يصبح مرشحًا للواجهة فقط بعد وجود سجل حقيقي وكامل ومتسق من Validation؛ في غياب الدليل نرجع لـ E01، مع بقاء النص تحت Human Verification قبل Grading |
| التشغيل على Windows | 4 ملفات `.bat` + `READ_ME_FIRST_SPRINT08_AR.md` | Preflight → 4-Pipeline Validation + Error Analysis → Frozen Test مرة واحدة → مراجعة ورقة وGrade؛ ملف اختبارات هندسية مستقل |

## 3. الـOCR Pipelines الأربع

| Pipeline | Model | Preprocessing | ما نقيسه |
|---|---|---|---|
| E01_base_rgb | `microsoft/trocr-base-handwritten` | Original RGB | Baseline مجمد |
| E02_base_autocontrast | نفس الـBase | Autocontrast | هل معادلة الإضاءة تفيد أو تضر؟ |
| E03_small_rgb | `microsoft/trocr-small-handwritten` | Original RGB | اختلاف السعة/الأداء على CPU/GPU |
| E04_base_padded | الـBase | Padding + conditional upscaling | هل القص والحواف تؤثر على القراءة؟ |

**البروتوكول:** Split by writer، صور GT مرخصة، نفس Validation IDs لكل Pipeline، أقل corpus-level CER أفضل؛ WER لكسر التعادل، وإصدار `selected_from_validation.json` فقط بعد الأربع كاملة. Test المجمد لا يستخدم لاختيار موديل جديد، بل لتقدير أداء الاختيار المسبق مرة واحدة. الإصدارات والخطأ لكل Writer وسجلات المخرجات تُحفَظ محليًا ولا تُنشر محتوية على بيانات طلاب.

**ملاحظة علمية:** نماذج Microsoft TrOCR Handwritten **fine-tuned على IAM** أصلًا؛ نتيجة IAM مهمة للتكرارية والـin-domain، لكنها ليست Independent Out-of-domain Holdout بالنسبة لخط طلاب MENTRIX. الاختبار على أوراق امتحانات حقيقية بخطوط كُتاب جدد وتفريغ بشري مستقل ضروري قبل الادعاء بفاعلية القراءة.

## 4. إزاي نختبر ورقة كاملة بشكل علمي؟

```text
Original page/PDF
    ↓
Smart/Legacy line detection (boxes)
    ↓
One line/image → TrOCR + optional preprocessing
    ↓
Question IDs (Q1, Q2, ...) OR manually selected answer regions
    ↓
UNVERIFIED OCR draft + original crops shown in UI
    ↓
Independent human GT: full page, line boxes/transcripts, question IDs, grades
    ↓
Evaluate four distinct stages:
  1. Detection (IoU/recall/precision/F1)
  2. Reading (CER/WER on matched lines; full-question CER/WER separately)
  3. Question mapping (question IDs vs independently annotated Q IDs)
  4. Grading policy (verified-text oracle vs unverified OCR diagnostic)
    ↓
TA verifies/corrects transcript → Conservative scoring / TA review → Batch publish
```

### فصل مصادر الخطأ

- **فشل كشف السطر:** يوجد في GT لكن لا يوجد OCR box مقابله: False Negative، بصرف النظر عن دقة TrOCR نفسه.
- **فشل التعرف:** سطر صحيح في موقعه لكن النص فيه استبدال/حذف/إضافة أحرف أو كلمات؛ CER/WER على السطور المتطابقة مكانياً.
- **فشل Mapping:** اكتُشف السطر وربما قُرئ صح لكن اتنسب إلى Q خطأ؛ معدل المطابقة صحيح/إجمالي السطور المتطابقة مكانياً.
- **فشل Grading:** مقارنة ناتج القواعد مع درجة TA المستقلة عندما يتوافر Rubric، وبشكل منفصل عند تقديم الـGround Truth الصحيح أو OCR draft غير المؤكدة؛ **لا يُنشَر grade مباشرة من OCR**.

### تنبيهات في القياس

- مطابقة الـBounding Boxes تجري greedy one-to-one بناء على IoU وبحد 0.5 افتراضيًا؛ قد تحتاج المعاينة البشرية عند السطور المتداخلة.
- `recognition_on_matched_lines` يستثني السطور التي لم تُكتشف؛ لا يجب تقديمه كرقم end-to-end شامل. `ocr_metrics` على السؤال كاملًا يلتقط تأثير النص المفقود لكن قد يتداخل مع أخطاء السؤال.
- Ground Truth لا تصبح "مستقلة" بمجرد كتابة `verified_by`؛ يُشرف الفريق على مراجعة بشرية حقيقية وتوثيق من كتب النصوص بعيدًا عن تنبؤ OCR.
- الدرجات التشخيصية في الـReport لا تعني Grades صالحة للنشر.

## 5. اختبارات التنفيذ

يُستعمل `python -m pytest -q` من جذر المشروع. الإصدارات القديمة قبل التعديلات سجلت 93 Pass. أضفنا اختبارات لعلاقة IoU واحد-لواحد، المحذوفات، OCR سليم وQuestion-ID خاطئ، رفض مراجع غير مستقل/غير مكتمل، منع Mock من التحليل العلمي، فحص Writer/image leak، فحص Test Lock، وإظهار مقاييس السطر ضمن `evaluate_full_sheet`. اختبارات الـAPI الموجودة تحافظ على مسار Staff → Upload → OCR draft → Verify → Grade والمراجعة البشرية.

**كل اختبارات البرمجة تستخدم Fixture/Stub/Synthetic inputs عند الحاجة؛ وليست تجربة موديل TrOCR الحقيقي.**

## 6. حالة التسليم الفعلية

**مكتمل بالفعل:** الموديولات السابقة والملفات التشغيلية، تكامل الموقع، بيانات بحثية محفوظة تاريخيًا من Sprint 1–7، فحوصات Pipeline/Mock، وحماية النشر بعد مراجعة المعيدة.

**لم يُنفذ من دون IAM وأوزان نموذج:** تشغيل Microsoft TrOCR الفعلي على كل Validation/Test، قياس CER/WER حقيقية جديدة، اختيار فائز حقيقي للواجهة، إثبات أن Smart أفضل من Legacy على خطوط بشرية، تقييم ورقة طالب كاملة بتفريغ مستقل، واعتماد نسب تصحيح آلي رسمي.

**المطلوب من الفريق:** التسجيل في IAM رسميًا والحصول على ملفاتها وقوائم الـWriter-Independent؛ تشغيل مقارنة الأربع على جهاز مناسب؛ تجهيز 15–30 ورقة حقيقية بخطوط جديدة مختلفة على الأقل كبداية Pilot (عدد إرشادي لا ضمان إحصائي)، مراجعة النص والـBoxes والدرجات بصورة مستقلة، ثم Freeze/Test خارج البيانات التي طُوّرت عليها الطريقة، وعرض النتائج الحقيقية.

## 7. تشغيل سريع

اقرئي `READ_ME_FIRST_SPRINT08_AR.md` في جذر المشروع. ترتيب الملفات: `START_MENTRIX_HERE.bat` → تنزيل IAM بنفسك + إعداد Manifest → `RUN_SPRINT08_CHECK_DATA.bat` → `INSTALL_SPRINT06_OCR.bat` → `RUN_SPRINT08_REAL_VALIDATION.bat` → `RUN_SPRINT08_FROZEN_TEST.bat`، ثم ارفعي ورقة حقيقية من Quiz Grading وراجعي كل سطر. `RUN_SPRINT08_CODE_TESTS.bat` لا يختبر الدقة العلمية.

## 8. المصادر والحدود

- IAM Handwriting Database 3.0: <https://fki.tic.heia-fr.ch/databases/iam-handwriting-database>. أرشيف صور السطور وقوائم تقسيم الكُتّاب بعد التسجيل؛ non-commercial research.
- Base: <https://huggingface.co/microsoft/trocr-base-handwritten>
- Small: <https://huggingface.co/microsoft/trocr-small-handwritten>
- Microsoft TrOCR implementation: <https://github.com/microsoft/unilm/tree/master/trocr>

**تسليم بحثي محلي فقط. لا توجد موافقة مؤسسية على Grades رسمية، ولا بيانات خاصة للطلاب في ZIP النهائي.**
