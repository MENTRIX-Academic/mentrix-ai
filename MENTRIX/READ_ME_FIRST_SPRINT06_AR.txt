MENTRIX / TAFlow — النسخة المتكاملة + Sprint 06 (4 نوفمبر 2026)

ملف البداية: START_MENTRIX_HERE.bat
رابط الموقع: http://127.0.0.1:8765  (ليس 8010 القديم)

تشغيل المشروع:
1) فكّي ZIP بالكامل في فولدر مستقل، ثم افتحي MENTRIX.
2) شغّلي START_MENTRIX_HERE.bat. يجهز .venv في نفس فولدر المشروع.
3) اكتبي PIN للمعيدة، وافتحي الموقع واختاري Quiz Grading.
4) ارفعي ورقة PDF أو صورة. للتعامل مع خط اليد شغّلي
   INSTALL_SPRINT06_OCR.bat مرة واحدة مع اتصال إنترنت.
5) في محرر الورقة اضغطي Read handwriting with TrOCR، واختاري Pipeline.
   النتيجة Draft فقط؛ افتحي صور Overlay لترى حدود السطور.
6) راجعي الورقة الأصلية، صححي النص بنفسك، ثم Verify & grade.
7) أسئلة Essay والإجابات الغامضة تحتاج TA review قبل النشر.

للبحث العلمي:
- research/sprint6/README_AR.md : الحصول على IAM وإعداد Manifest.
- RUN_SPRINT06_CPU_SMOKE.bat : تجربة صغيرة للتأكد من التشغيل فقط.
- RUN_SPRINT06_VALIDATION.bat : مقارنة المرشحين على Validation.
- RUN_SPRINT06_FROZEN_TEST.bat : اختبار الفائز فقط بعد تثبيت الاختيار.
- RUN_SPRINT06_TESTS.bat : اختبارات هندسية، ليست Accuracy فعلية.

التقرير الكامل:
- OPEN_SPRINT06_FULL_REPORT.bat
- docs/MENTRIX_ALL_PHASES_SPRINT06_REPORT_AR.pdf
- docs/MENTRIX_ALL_PHASES_SPRINT06_REPORT_AR.html

مهم جدا: IAM وصور خط اليد الجديدة وأوزان TrOCR ليست داخل ZIP.
لم تحدث مقارنة CER/WER جديدة لموديلات حقيقية في هذا التسليم.
الاختبارات الموجودة تستخدم صورا مصطنعة وFake OCR لفحص التكامل.

Keep a backup of local_private_data if it has any saved work.
Never publish real student images, transcripts or grades without permission.
