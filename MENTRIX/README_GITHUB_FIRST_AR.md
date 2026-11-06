# ابدئي من هنا — MENTRIX AI Reproducibility Handoff

النسخة دي مش موديل متدرّب. دي **ملفات الكود الأصلية + الـAPI التجريبية + مقارنة قابلة للإعادة + اختبارات + إثبات مصدر**. هدفها أول إغلاق هندسي لـPhase 1 وتجهيز نقلها إلى GitHub.

## على Windows
1. فكي ضغط الـZIP بالكامل، وافتحي فولدر `MENTRIX_AI_Phase1_Reproducibility_Handoff`.
2. اقفلي أي نسخة شغالة على Port 8000 لو هتفتحي الموقع.
3. دوسي مرتين على `VERIFY_PHASE1.bat`، أو PowerShell من داخل الفولدر:
   ```powershell
   py -m pip install -r requirements.txt
   py REPRODUCE_PHASE1.py
   ```
4. النتيجة في `reports/phase1_verification.txt` و`reports/phase1_verification.json`.
5. لو عايزة الموقع: `py -m uvicorn app:app --reload` ثم `http://127.0.0.1:8000/research`.

## المخرجات اللي بتثبتها هذه النسخة
- ملفات `grader.py`, `grader_v2.py`, `questions.json` مطابقة لـSHA256 المسجل.
- 15 اختبار API/Engine + 5 اختبار Research من الحزمة الحالية.
- 29 حالة **جديدة صناعية توضيحية** من `research/data/curated_demo_cases.csv` قابلة للمقارنة بـStrict/V1/V2.
- 500 مدخل مشوّه **جديد** لاختبار غياب الـUnhandled Exceptions فقط، ليس إثبات أمان أو Accuracy.
- الأرقام القديمة الخاصة بـ123/127 Case **موجودة في ملخصات**، لكن لم تستعد ملفات الاختبار الأصلية بعد.

## ليس منجزًا بعد
- ملفات `stress_cases.csv`, `synthetic_cases.csv`, `test_grader.py`, `test_v2.py` الأصلية.
- إعادة تنفيذ النتائج القديمة على جهاز آخر وبالملفات الأصلية.
- اعتماد الـTA والمشرف الحقيقي لسياسات التصحيح.
- تقييم مستقل على إجابات طلاب أو خط يد حقيقي.

## رفعها على GitHub
افتحي `docs/GITHUB_HANDOFF_GUIDE_AR.md`، واتّبعي الخطوات حسب إذا كان عندك repo محلي بالفعل. استخدمي **Private Repository** طول ما شكل البيانات والسياسات لسه بيتراجعوا. ما ترفعيش صور أو أسماء أو درجات طلاب حقيقية.

## ما الذي يمكن وضعه Done؟
- `Current Research Pack Reproducible on one environment` بعد نجاح تشغيل الـScript.
- Phase 1 إجمالًا: **Pending original evidence + independent reproduction + formal TA signoff**.
- Phase 3: **Prototype, NOT human validated**.
