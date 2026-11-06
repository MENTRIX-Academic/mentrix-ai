# Sprint 01 — تنفيذ وتجهيز البحث (2026-11-03)

## ما تم في هذا التسليم بالفعل
- المحافظة على واجهة MENTRIX الأصلية وموديولات OCR والتصحيح والـAttendance والـChatbot من ZIP المستخدم بدون تغيير جوهري.
- إضافة ملف واضح بقرارات V1: `docs/MENTRIX_V1_DECISIONS_AR.md`.
- حفظ نسخة كاملة من مرجع المستخدم `Work Wrap up.pdf` داخل `docs/reference`.
- إضافة `experiment_inventory.csv` لتهيئة عرض التجارب في AI Experiments لاحقًا، مع فصل المقارنات القديمة ذات البيانات المصطنعة وعدم الادعاء بأنها متحققة خارجيًا.
- سكريبت تجهيز ASAP-SAS يقسم Train/Validation/Test ويمنع ظهور إجابة مطابقة لنفس السؤال في أكثر من تقسيم.
- سكريبت baseline اختياري (Mean وTF-IDF Word وTF-IDF Char مع Ridge) يحتفظ بالـTest حتى اختيار الطريقة على الـValidation، ويكتب MAE/QWK.
- سكريبت OCR يقارن Predictions بالنصوص البشرية المرجعية، وينتج CER/WER لكل كاتب ولكل اختبار.
- فحص للهاشات والملفات القديمة، واختبارات كود باستخدام بيانات اصطناعية صغيرة فقط.

## نتائج الاختبارات الفعلية لهذه النسخة
- Sprint 01 unit/smoke: **4/4 PASSED** (يتطلب الاختبار الرابع scikit-learn، وإلا Skip مع تنبيه).
- اختبارات البحث الأصلية: **5/5 PASSED**.
- اختبارات تطبيق الويب الأصلية: **25/25 PASSED**.
- **لا يوجد أي رقم جديد لدقة OCR أو grading على Kaggle لأن البيانات لم تُنزّل ولم يُشغّل Benchmark حقيقي.**

## ما لا يعنيه هذا التسليم
- ليس تحديثًا للواجهة أو رابط تشغيل موقع جديد؛ لا يوجد تغيير في Sidebar هنا.
- لم يضف Student ID + PIN إلى الـBackend بعد؛ هذا مطلب مثبت للتطوير التالي.
- لم تُجهَّز بيانات 30 طالبًا داخل قاعدة التطبيق؛ Mock Data تبقى جزءًا من المرحلة التالية.
- لم ينفذ Full Paper Segmentation أو Model Training / Fine-tuning على GPU.

## أول خطوة عملية بعد تشغيل الفحوصات
تحميل Kaggle ASAP-SAS وفق شروط المسابقة وتشغيل:

`py research/sprint1/prepare_asap.py --input research/sprint1/data/asap/train.tsv`

ثم:

`py research/sprint1/evaluate_short_asap.py --input research/sprint1/data/asap_prepared.csv`

أما الـOCR فيحتاج Ground Truth بشريًا ثم تشغيل `evaluate_ocr.py`.
