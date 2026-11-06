MENTRIX - WINDOWS FIX (WinError 5 / pymupdf)

سبب المشكلة: كان تشغيل المشروع يثبت المكتبات في Python العام،
ففشل استبدال pymupdfp64.dll بسبب صلاحيات Windows او لان الملف مستخدم.

الطريقة الجديدة:
1) فك الضغط في فولدر منفصل او احتفظي بالنسخة القديمة كنسخة احتياطية.
2) افتحي MENTRIX وشغلي START_MENTRIX.bat.
3) هينشئ فولدر .venv ويثبت المكتبات فيه فقط في اول تشغيل.
4) بعد ذلك هيفتح الموقع على http://127.0.0.1:8765

مهم:
- لا يلزم Run as Administrator ولا اعادة تثبيت Python.
- لا تمسحي local_private_data اذا عندك بيانات سجلات مهمة.
- لو .venv حصل لها تلف، اقفلي نافذة التشغيل، غيري اسم .venv الى .venv_old وشغلي START_MENTRIX.bat مرة اخرى.
- بعض صور OCR تحتاج Tesseract مثبتاً بشكل منفصل؛ إصلاح تشغيل Python لا يثبت برنامج Tesseract.

This launcher uses a local virtual environment. It never runs pip against global Python.
