# MENTRIX — Sprint 04 | Error Analysis + Real MiniLM/NLI

## الحالة الفعلية

- **مُنجز ومُشغّل:** تحليل أخطاء الـ7 Baselines من Sprint 03 على نفس 129 إجابة؛ مقارنة أخطاء 0/1/2 وحالات منح الدرجة الكاملة بالخطأ؛ وتجهيز ملف مراجعة بشرية.
- **جاهز للتشغيل على جهاز المستخدم فقط:** MiniLM وNLI الحقيقيان. ملفات النماذج غير مدمجة بالـZIP لأن أول تشغيل ينزلها من Hugging Face. لن نعرض نتائجها إلا بعد التشغيل الحقيقي.
- **غير مُنفذ:** Rubric+NLI على ASAG؛ لأن الملف فيه Grade إجمالية فقط (0/1/2) وليس Rubric معتمدة لكل سؤال. لا يصح اختراع Rubric أو تسميتها تجربة فعلية.
- **غير مُنفذ:** OCR / handwriting. ASAG إجابات مكتوبة كنصوص، ومختلفة عن 1–3 كلمات في MENTRIX.

## أسهل طريقة على Windows

1. فكّي Sprint04 ZIP في فولدر جديد مستقل (بدون Replace).
2. افتحي `OPEN_SPRINT04_REPORT.bat` — تقرير تحليل الأخطاء جاهز وبيشتغل بدون Python.
3. للتأكد من كود التحليل: شغّلي `RUN_SPRINT04_ERROR_ANALYSIS.bat` (يستخدم numpy/scikit-learn من Sprint 03).
4. لو مستعدة لتنزيل وتشغيل نماذج فعلية: شغّلي `INSTALL_SPRINT04_MODELS_ONCE.bat` أول مرة فقط (يتطلب إنترنت وقد يحمل ملفات كبيرة).
5. على جهاز CPU قديم، شغّلي `RUN_SPRINT04_MINILM_ONLY.bat` أولًا. بعد التأكد من نجاحه شغّلي `RUN_SPRINT04_MODELS.bat` ليعمل MiniLM+NLI (أبطأ وأكبر).
6. افتحي `OPEN_SPRINT04_REPORT.bat` مرة ثانية، وسيرصد التقرير النتائج الجديدة **إذا تم تشغيلها بالفعل**.

### لو ظهر خطأ

- `No module named sentence_transformers`: شغّلي ملف تثبيت النماذج.
- Download/connection error: يحتاج الإنترنت للوصول لـ Hugging Face أول مرة؛ النتائج القديمة تفضل موجودة.
- Windows لا يفتح BAT: افتحي PowerShell من نفس فولدر المشروع، ونفّذي `py -3 -m research.sprint4.error_analysis` أو `py -3 -m research.sprint4.model_benchmark --skip-nli`.
- RAM/CPU بطيء: ابدئي MiniLM Only، وخفضي batch-size باستخدام `py -3 -m research.sprint4.model_benchmark --batch-size 2`.

## القواعد البحثية

- كل الطرق تستخدم الـ **frozen Sprint03 split**، والملف الأصلي يُتحقق منه باستخدام SHA-256.
- تدريب Ridge/KNN الخاص بكل سؤال على **Train فقط**، اختيار أفضل طريقة لكل سؤال من Validation فقط، وحساب Test مرة واحدة للمقارنة.
- لا يوجد Fine-tuning للنماذج في Sprint 04. الإشارة إلى NLI هي General Natural Language Inference، **وليست فهمًا مضمونًا لصحة الإجابة علميًا**.
- يوجد مثال بحثي على Policy لاختيار درجات واضحة، لكن لا يتم نشر أي درجات؛ ويستخدم شرط Wilson lower 95% محافظًا على Validation فقط، وقد لا يقبل أي إجابة.
- عند تحليل `s04_human_review_template_LOCAL_ONLY.csv`، تصنيف Contradiction/Paraphrase/Incomplete/Off-topic/Label issue يتم **بشريًا فقط**.
- ملف CSV للمراجعة يتضمن إجابات فعلية؛ لا ترفعيه إلى GitHub عامة ولا تعرضيه في صفحات عامة؛ التقرير HTML لا يتضمن النصوص.
- النموذج الصالح للـV1 يتطلب Independent 1–3 words dataset وRubrics معتمدة وقياس السلامة قبل تمكين auto-publish.

## أسماء النماذج

- MiniLM: `sentence-transformers/all-MiniLM-L6-v2` — sentence encoder، وليس grader في حد ذاته.
- NLI: `cross-encoder/nli-MiniLM2-L6-H768` — ثلاث فئات `contradiction, entailment, neutral`، ونتأكد من ترتيب الفئات.
- MiniLM reference / MiniLM KNN / NLI reference / MiniLM+NLI reference: **محاولات بحثية مُعايرة على Train**، لكنها **ليست** Rubric+NLI التاريخية لأن الـRubrics غير موجودة.
- الموديل الأكبر البديل للاختبار: `cross-encoder/nli-deberta-v3-small` باستخدام الخيار `--nli-model` إن توفرت موارد الجهاز.

## الملفات

- `s04_error_analysis.json`: أرقام التحليل المجمدة على Sprint03.
- `s04_error_analysis_report.html`: التقرير الآمن للعرض، بدون نصوص الإجابات.
- `s04_human_review_template_LOCAL_ONLY.csv`: عينة ذات أولوية للمراجعة البشرية، تتضمن نصوص البيانات الأصلية.
- `s04_transformer_test_predictions.csv` و`s04_transformer_results.json`: **تُنشأ فقط بعد تشغيل النماذج الحقيقية**.
- `research/sprint3/results/`: لا نعدّل الملفات الأصلية إطلاقًا.

### Sources

- DigiKlausur ASAG: https://github.com/DigiKlausur/ASAG-Dataset
- MiniLM: https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2
- NLI: https://huggingface.co/cross-encoder/nli-MiniLM2-L6-H768
- Sentence Transformers NLI documentation: https://sbert.net/docs/cross_encoder/pretrained_models.html
