# MENTRIX - 4 نوفمبر 2026 - Sprint 06

## ماذا تغير مقارنة بالملف المرفوع؟

1. أُضيف `research/sprint6/prepare_iam.py`، وهو IAM importer يقرأ Writer-ID من XML، ويرفض Split Leak وتضارب IDs.
2. أُضيف `research/sprint6/benchmark.py`: TrOCR-base original / autocontrast / padded، وTrOCR-small original، مع CER/WER corpus-level، اختيار Validation وقفل Test بالموديل الفائز فقط، وفحص Hash محتوى الصور.
3. أُضيف `research/sprint6/full_sheet.py`: PDF/Image، اكتشاف خطوط، تعيين Question IDs، Manual Regions، OCR Draft، Bounding-box overlays، تقييم OCR / Question mapping / Region IoU؛ مقارنة Grading على **النص البشري المرجعي مقابل مسودة OCR** لمعرفة سبب الخطأ.
4. أُضيف `handwriting_routes.py` وربط بـ`app.py`، مع زر OCR للورقة المحفوظة في صفحة Quiz Grading؛ الإخراج غير مؤكد ويحتاج TA review، ولن يطلق Auto-grade قبل التأكيد.
5. تحديث Cache-bust وبناء تطبيق واحد على 8765، لا صفحة منفصلة ولا AI Roadmap.
6. ملفات BAT لثبيت الموديلات (اختياري)، Diagnostic CPU، Validation، Frozen Test، فحوصات، وفتح التقرير.
7. التقرير الشامل من البداية حتى اليوم بصيغتي PDF وHTML، مع نتائج ASAG المجمدة ومقارنة الطرق الموجودة في الملفات.

## ما الذي اختبرناه؟

`python -m pytest -q` → **81 passed** محليًا. 69 اختبارًا قديمًا + 12 اختبارًا جديدًا، منها TestClient لرفع ورقة تجريبية وتوليد OCR draft وعرض الـOverlay ثم تأكيد النص وتطبيق قواعد التصحيح. كل OCR في الاختبارات الجديدة **Fake recognizer** على **صفحة Printed synthetic**. هذا يثبت API/segmentation/grading plumbing وليس جودة TrOCR. فُحصت صحة JavaScript باستخدام `node --check`، وتم فتح `/health` ورجع HTTP 200، وقراءة `/api/workspace/handwriting/config` بلا PIN رجعت HTTP 401.

## المتبقي والذي لا يجوز الإشارة إليه كمكتمل

- IAM images + metadata + official split IDs: لم توضع هنا، تُنزل رسميًا بعد التسجيل.
- TrOCR pretrained model weights: غير مُحمّلة أو مُدرجة، لذلك لم ينفذ Inference جديد.
- CER/WER حديثة لـIAM أو صورة بخط يد واقعية، وQuestion Bounding Box IoU حقيقي، وGrading accuracy حقيقية: **غير متاحة**.
- مراجعة بشرية مستقلة للـGround Truth والـRubric وتوقيع TA، واختبار Windows + Laptop CPU فعلي، قبل اعتماد أي نموذج.

لا تنشري ZIP يحتوي على صور الطلاب أو SQLite حقيقية أو CSV Predictions خاصة.
