# MENTRIX Sprint 05 — جهد متعدد المهام في نسخة واحدة

هذه نسخة **تراكمية**: تضم Sprint 01–04 بدون تعديل ملفاتها القديمة. ملفات Sprint05 الجديدة فقط داخل `research/sprint5` وملفات BAT الجديدة في جذر المشروع. **لم نعدل الموقع.**

## تشغيل سهل على Windows

1. فكّي الـZIP داخل `Graduation Project/MENTRIX_SPRINT05` **كمجلد مستقل**؛ بلاش Replace لملفات Sprint04.
2. افتحي `MENTRIX_UNIFIED_CORRECT_SITE`.
3. `OPEN_SPRINT05_REPORT.bat`: يفتح التقرير المحفوظ فورًا، لا يحتاج تنزيل نماذج.
4. `RUN_SPRINT05_AUDIT_AND_REPORT.bat`: يعيد حساب 7 baselines والتأكد من نتائج Sprint03، ويحدّث التقرير. لو مكتبات التحليل ناقصة، شغّلي `INSTALL_ASAG_DEPENDENCIES_ONCE.bat` الأول.
5. `RUN_SPRINT05_MOCK_DATA.bat`: ينشئ demo منفصلًا بـ30 طالبًا و12 Session ومجموع 360 حالة حضور وهمية. دي **مش بيانات تدريب** و**مش تسجيل حضور حقيقي**.

### Models (الأوزان غير مدرجة بالنسخة)

6. شغّلي `INSTALL_SPRINT04_MODELS_ONCE.bat` (مرة واحدة؛ إنترنت) ثم `RUN_SPRINT05_MINILM_NLI_CPU.bat`؛ قد يكون بطيئًا على CPU، ويحتاج مساحة وRAM. النتائج الحقيقية، إن اكتمل التشغيل، ستُحفظ في `research/sprint4/results/s04_transformer_results.json` ويُحدّث Sprint05 HTML تلقائيًا. يمكن تشغيل `RUN_SPRINT04_MINILM_ONLY.bat` أولًا لو الجهاز ضعيف.

### OCR

7. صور OCR **غير موجودة في هذا الـZIP**. لإجراء تجربة حقيقية احفظي الصور في `research/sprint5/data/images/`، وانسخي `ocr_manifest_TEMPLATE.csv` إلى `ocr_manifest.csv` واملئي الأعمدة:
   - `sample_id`: رقم فريد للصورة؛ `writer_code`: كود كاتب مستقر؛ `split`: train/validation/test؛ `image_path`: اسم ملف نسبي داخل images؛ `ground_truth`: نص راجعه إنسان **مستقل**؛ `verified_by`: رمز المراجع.
   - يجب ألا يظهر كاتب في أكثر من split. النظام يرفض غياب النص المرجعي أو المراجعة أو مسارات الملفات غير الآمنة.
   - في أول مرة: `INSTALL_SPRINT05_OCR_MODELS_ONCE.bat`؛ بعد إعداد الصور: `RUN_SPRINT05_OCR_REAL.bat`. الكود يستخدم TrOCR **Original RGB E01** ويحسب CER/WER بعد التحقق. يمنع اختلاق Metric بدون صور صحيحة.

## ملخص النتائج المُشغّلة الآن

- 7 baseline methods أعيد تشغيلها على نفس بيانات ASAG ونفس تقسيم Sprint03، وكل الـTest predictions تطابقت (129 إجابة Test).
- طريقة الاختيار حسب validation: 54 درجة غير مطابقة، ومنها 26 إجابة منحها النموذج 2/2 رغم أن الدرجة البشرية أقل.
- تجربة 3 سياسات اتفاق: عند اتفاق السبعة على الدرجات في 77 حالة Validation، الدقة الملاحظة 51/77 = 66.2%. **لم تنجح أي سياسة** في اجتياز شرط سلامة research gate، لذلك تبقى كل درجات ASAG تحت المراجعة بحسب هذه السياسة.
- لا MiniLM/NLI جديد مُشغّل هنا، ولا OCR جديد، ولا Rubric+NLI بدون Rubrics معتمدة. الأرقام الموجودة في ملف Work Wrap up تخص Dataset قديمة مختلفة، فالمقارنة الرقمية معها غير عادلة.
- 30 طالبًا و12 Session و360 check-in statuses كلها بيانات **synthetic demo** للتكامل فقط، بدون PINs.

## ملفات مهمة

- `research/sprint5/results/s05_unified_research_report.html` — تقرير بحثي عربي/إنجليزي قابل للمشاركة **بدون نصوص الإجابات**.
- `research/sprint5/results/s05_reproducibility_and_gate.json` — أرقام موثقة، ومقارنة 7 Methods.
- `research/sprint5/mock_data/s05_mock_backend_data.json` — demo integration only.
- `research/sprint5/API_MOCK_CONTRACT.md` — تصميم endpoints للـTA/Admin/Check-in/Grading/Assistant، ليس Backend مكتملًا.
- `research/sprint4/results/s04_human_review_template_LOCAL_ONLY.csv` — يحمل نصوصًا أصلية، فلا تنشريه في موقع عام.
- `research/sprint3/results/` — Frozen benchmark، لا يتغير.

## حدود البحث

الـASAG إجابات مطبوعة طويلة ومقياسها 0/1/2 بمصحح بشري واحد، وليست إجابات MENTRIX النهائية من 1–3 كلمات ولا OCR بخط اليد. اختبار ASAG استُخدم سابقًا في Sprint03 و04، فلا يصبح اختبارًا جديدًا مستقلًا بمجرد إعادة تشغيله. اختيار النماذج أو سياسات الموافقة النهائية يجب أن يتم قبل تقييم Test جديد مستقل، مع Rubrics بشرية معتمدة. **لا يوجد نشر درجات تلقائي مفعل.**
