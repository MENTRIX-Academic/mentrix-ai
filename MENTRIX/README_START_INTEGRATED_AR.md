# MENTRIX V1 - مشروع واحد متكامل (Pilot)

## أول تشغيل على Windows

1. فكّي ملف ZIP كاملًا في فولدر جديد مستقل (لا تعملي Replace لفولدرات Sprint القديمة).
2. افتحي فولدر `MENTRIX` وشغّلي **`START_MENTRIX.bat`** فقط. الإصدار المصحح ينشئ فولدر `.venv` تلقائيًا ويثبّت المكتبات داخله، من غير تعديل Python العام على الجهاز.
3. في أول تشغيل، قد يحتاج تنزيل مكتبات Python الخفيفة (إنترنت). اختاري **TA PIN** بطول 6 رموز على الأقل، ويمكنك أيضًا تحديد **Admin PIN** منفصل.
4. سيفتح الموقع تلقائيًا على **http://127.0.0.1:8765/**. أدخلي PIN المعيد أو المدير.
5. عند الإغلاق، اضغطي Ctrl+C أو أغلقي نافذة التشغيل. قاعدة البيانات تبقى في `local_private_data/`.

**لو تشغيل Windows فشل:** تأكدي من Python 3.10+، ولا تشغّلي `pip install` على Python العام. أعيدي تشغيل `START_MENTRIX.bat`؛ فهو يستخدم `.venv` فقط. لو تعطلت البيئة المحلية نفسها، أعيدي تسمية فولدر `.venv` إلى `.venv_old` ثم شغّلي الملف مجددًا. لو Tesseract OCR غير مثبت على Windows، تفريغ الصور الممسوحة قد يرجع نصًا فارغًا؛ ثبّتي Tesseract English يدويًا أو استخدمي ترانسكريبشن المعيد. ملفات PDF التي تحتوي نصًا إلكترونيًا تعمل من غير Tesseract.

## ما الذي يعمل الآن فعليًا؟

- **Dashboard:** إحصائيات حية من SQLite للنسخة التجريبية.
- **Attendance:** إنشاء Session، QR يتجدد كل 30 ثانية، مدته 5 دقائق افتراضيًا، Student ID + PIN، منع التكرار، Random Check، إدخال يدوي، إغلاق واضح ومحاسبة غياب بعد الإغلاق فقط، Export CSV.
- **Student Check-in:** صفحة `/checkin` منفصلة عن Dashboard. حسابات التجربة: ST001 إلى ST030، وPIN من 740001 إلى 740030 بالترتيب. هذه حسابات وهمية فقط.
- **AI Assistant:** استعلامات قاعدة البيانات الإنجليزية وبعض العربية (مثلاً ST001، AI-SEC01، Quiz submissions)، بدون اختلاق بيانات. ليس LLM عامًا غير محدود.
- **Quiz Grading:** اختيار Quiz/Student، رفع ورقة PDF أو صورة كاملة، استخراج PDF النصي أو مسودة OCR للصور، تصحيح النص يدويًا، تصحيح حتمي فقط للحالات الواضحة، مراجعة TA للباقي، Batch Publish، سجل Audit، Export Grades CSV.
- **Question Bank:** أسئلة Demo بأربعة أنواع؛ إنشاء Quiz JSON جديد وحفظه كمسودة واعتماده صراحة بعد المراجعة؛ رفع مواد PDF/TXT للمقرر.
- **AI Experiments:** يعرض نتائج ASAG المحفوظة ومعايير MAE وQWK وأسباب رفض الاعتماد الآلي؛ روابط Sprint03–05 وأرشيف التجارب والملف التاريخي `Work_Wrap_up_original.pdf`.
- **TA/Admin:** حساب staff محلي بجلسات Cookies؛ Admin له Audit Log إضافي.

## اختبار سريع

- تسجيل الحضور: اختاري Attendance > Start Session. اضغطي رابط تجربة Check-in من نفس اللابتوب وسجّلي ST001 / 740001. ارجعي اعملي Refresh ثم Random Check وأكّدي الحضور يدويًا، وبعدها Close.
- تصحيح ورقة كاملة: اختاري Quiz Grading > AI-QUIZ01 > ST001، وارْفعي `demo_samples/DEMO_FULL_ANSWER_SHEET.pdf`. افحصي النص الأصلي، علمّي checkbox التحقق، واضغطي Verify & Grade. Q1/Q2/Q3 واضحة وتتسجل كدرجات مبدئية؛ Q4 يحتاج مراجعة TA. بعد اعتمادها اختاري الورقة واضغطي Batch Publish.
- Assistant: اكتبي `How many times was ST001 absent?` أو `Attendance in AI-SEC01`.
- Experiments: افتحي AI Experiments واقرئي Metrics والتقارير.
- اختبارات الكود: شغّلي `RUN_ALL_CHECKS.bat` أو `python -m pytest -q` بعد تثبيت pytest وhttpx.

## حدود مهمة لا يجوز تجاهلها

- نسخة **محلية Pilot** وليست منصة آمنة لاستقبال بيانات جامعية حقيقية أو للتشغيل العام على الإنترنت.
- `http://127.0.0.1:8765` لا يُفتح على هواتف الطلاب عبر QR لأن `localhost` يشير لجهاز الهاتف. تجربة الهاتف الحقيقية تحتاج نشرًا مركزيًا مع HTTPS وإدارة حسابات حقيقية وتهيئة `MENTRIX_BASE_URL` وتعزيز الأمن؛ لم ننفّذ هذا النشر هنا.
- OCR لخط اليد غير مضمون، وTrOCR يحتاج أوزانًا غير مرفقة بالـZIP. التجارب القديمة محفوظة وأدواتها موجودة، لكن لا يوجد تقييم جديد على صور بخط اليد ذات Ground Truth مستقل في هذا الإصدار.
- **لا يوجد Fine-tuning جديد لـMiniLM أو NLI أو TrOCR** ضمن هذا التسليم، ولا دليل يسمح بنشر درجات Essay تلقائيًا. نتائج ASAG الحقيقية تخص نصوصًا مكتوبة ودرجات 0–2، ولا تثبت نجاح إجابات 1–3 كلمات أو OCR.
- وجود ملف Course Materials لا يجعل كل إجابة قابلة لتصحيح تلقائي صحيح؛ التصحيح الآمن يعتمد على الـRubric ومفاتيح الإجابة المعتمدة وقرار مراجعة TA.
- Audit يهدف لتتبع العمليات داخل التجربة فقط، وليس سجلًا أمنيًا غير قابل للتعديل.

## أهم الملفات

- `START_MENTRIX.bat` تشغيل الموقع.
- `app.py` FastAPI entrypoint.
- `integrated_workflow.py` منطق SQLite + QR + Quiz + Assistant + Research APIs.
- `static/index.html` + `static/workspace.js` + `static/workspace.css` واجهة الموقع النهائية.
- `static/student_checkin.html` بوابة الطالب.
- `tests/test_integrated_workflow.py` اختبارات End-to-End.
- `docs/MENTRIX_FINAL_IMPLEMENTATION_REPORT_AR.html` التقرير النهائي.
- `docs/Work_Wrap_up_original.pdf` الملف التاريخي من المستخدم.
- `research/sprint1..5` كل النتائج والكود البحثي السابق.
- `local_private_data/mentrix_unified_v1.sqlite3` قاعدة البيانات التجريبية (تُنشأ تلقائيًا لو غير موجودة).

**ملاحظة:** يوجد سكربتات Batch قديمة من Sprints سابقة في جذر المشروع للتوثيق؛ **ابدئي بـ`START_MENTRIX.bat` فقط**، وبلاش تشغيل ملفات START القديمة.
