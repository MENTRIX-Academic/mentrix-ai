MENTRIX — SPRINT 07 HANDWRITING OCR UPGRADE (4 NOV 2026)
=======================================================

ابدئي من هنا:
1) فكّي ZIP في مكان جديد. افتحي فولدر MENTRIX نفسه.
2) اقفلي أي نسخة قديمة من الموقع (Ctrl+C في نافذة السيرفر القديمة).
3) اضغطي START_MENTRIX_HERE.bat لتشغيل الموقع المحلي.
4) اضغطي INSTALL_SPRINT06_OCR.bat مرة واحدة لتثبيت مكتبات TrOCR
   ومعها OpenCV الجديدة. إعادة تشغيل هذا الملف ضرورية حتى لو سبق تثبيت Sprint06.
   أول استخدام للموديل يحتاج إنترنت لتحميل الأوزان غير الموجودة في ZIP.
5) في الموقع: Quiz Grading > Upload ورقة PDF/JPG/PNG > افتحي الورقة.
6) اختاري Smart line detection (recommended)، ثم Read handwriting with TrOCR.
   للاحتفاظ بسرعة أكبر اتركي Extra pass مغلق، وفعليه إن ظهرت سطور فاضية.
7) افتحي Compare original handwriting with OCR وراجعي كل صورة سطر مع نصه.
8) لو الأسئلة مش متقسمة صح افتحي Mark question areas directly on image؛
   اختاري السؤال Q1، واسحبي بالماوس مستطيل حول إجابته، وكرري للأسئلة.
   ثم اضغطي Read handwriting with TrOCR من جديد لتطبيق المناطق المحددة.
9) صححي النص والإجابات بنفسك؛ اختاري I compared every answer،
   ثم Verify & grade. التصحيح والنشر لا يتمان من OCR غير متحقق منه.

لو الصورة مائلة بشدة أو الخط صعب، اختاري Legacy lines للمقارنة، أو
حددي المناطق بالماوس. النتيجة دائمًا Draft تحتاج مراجعة.

للتأكد من الكود: RUN_SPRINT07_TESTS.bat (اختبارات هندسية فقط).
التقرير الفني: docs/SPRINT07_HANDWRITING_REPORT_AR.md

مهم: ليس في هذا ZIP أوزان TrOCR أو IAM ولا Dataset لخط يد جديدة،
ولم ننفذ في هذه البيئة inference فعلي على صور خط يد بشرية.
لذلك لا توجد نسبة CER/WER حقيقية جديدة يمكن نشرها.
