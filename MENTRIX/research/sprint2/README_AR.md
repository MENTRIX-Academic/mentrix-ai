# MENTRIX | Sprint 02 — تشغيل أول Benchmark على Kaggle ASAP-SAS

## ما الذي تم؟
- أضفنا برنامج مقارنة **ستة Baselines** على بيانات ASAP-SAS المصححة بشريًا، مع الحفاظ على جميع ملفات Sprint 01 والموقع والتجارب التاريخية كما هي.
- الداتا **غير مرفقة** داخل ZIP. لم نحمّلها أو نُنشئ نتائج حقيقية لأن Kaggle يتطلب تسجيل الدخول والموافقة على شروط المسابقة.
- أجرينا **Unit Tests بأمثلة مصطنعة لتأكيد سلامة الكود فقط**، وهي ليست Benchmark على Kaggle.
- عند وضع ملف Kaggle الحقيقي، يشغّل البرنامج الدراسة، ويحفظ metrics وpredictions وMarkdown report تلقائيًا.

## خطوة أولى — الحصول على البيانات بشكل قانوني
1. افتحي https://www.kaggle.com/competitions/asap-sas/data وسجّلي دخولك، ووافقي على **Competition Rules**.
2. نزّلي ملف `train.tsv` (أو فكّي ملف ZIP اللي فيه `train.tsv`).
3. حطّيه داخل المشروع في:
   `MENTRIX_UNIFIED_CORRECT_SITE/research/sprint1/data/asap/train.tsv`
4. ثبتي الاعتمادات من PowerShell في فولدر المشروع:

```powershell
py -m pip install -r research/sprint1/requirements.txt
```

5. اضغطي مرتين على **`RUN_SPRINT2_REAL_BENCHMARK.bat`**.

لو عندك Kaggle CLI متثبت ومعاه صلاحيات التحميل، بدل التنزيل اليدوي ممكن تضغطي `DOWNLOAD_AND_RUN_SPRINT2.bat`. لازم تقبلي القواعد بنفسك؛ البرنامج مش هيتجاوزها.

> لا ترسلي Kaggle API token أو ملف `kaggle.json` لشخص أو ترفعيه داخل ZIP. بيانات الطلاب الحقيقية تفضل محلية وتحتاج موافقات مناسبة.

## نتائج التشغيل
بعد نجاح التشغيل هتلاقي في `research/sprint2/results/`:

- `asap_s02_report.md` — جدول مقارنات وملاحظات لشرحها للتيم.
- `asap_s02_metrics.json` — MAE / raw MAE / QWK / exact match / within-one لكل موديل ولكل سؤال مع عدد السجلات والـSHA256.
- `asap_s02_test_predictions.csv` — توقعات الاختبار مع رصد أخطاء التصحيح (بدون نصوص إجابات الطلاب).

مهم: أول مرة هتجربي تشغيل الملف من غير `train.tsv`، هيظهر `DATA_NOT_AVAILABLE`، وده **متوقع** مش عطل في الكود ولا دليل على نجاح التدريب.

## ما الذي نقارنه؟

| Method | يعني إيه؟ |
|---|---|
| mean | متوسط درجات تدريب السؤال، خط أساس مهم |
| tfidf_word_ridge | تعلّم Regression على TF-IDF كلمات وأزواج كلمات |
| tfidf_char_ridge | تعلّم Regression على TF-IDF حرفي |
| token_overlap_knn | أقرب إجابات مصححة عبر Jaccard overlap |
| tfidf_word_knn | أقرب إجابات مصححة باستخدام TF-IDF كلمات |
| tfidf_char_knn | أقرب إجابات مصححة باستخدام TF-IDF حروف |

**ملاحظة:** دول Baselines جديدة وليست نسخًا مطابقة لأكواد Token Overlap وRubric+NLI الواردة في Work Wrap up. عشان نعيد مقارنة طرق التقرير القديمة، لازم نكيّفها مع أسئلة ASAP والـRubrics الأصلية على **نفس Split**، وممنوع مقارنة الأرقام على Dataset مختلفة باعتبارها مقارنة عادلة.

## التقييم العادل
- كل سؤال له Model مستقل لأن مجال درجاته مختلف.
- تقسيم Train / Validation / Test مع تثبيت seed=42، وتجميع الإجابات النصية المتطابقة كي لا تظهر في أكثر من مجموعة لنفس السؤال.
- اختيار أفضل Baseline يكون من Validation فقط؛ الاختبار يعرض نتائج الطرق المحددة سلفًا بدون اختيار موديل بناءً عليه.
- MAE يتم حسابه على الدرجة **المقربة للعدد الصحيح** بعد ضبطها على مجال الدرجات في Train؛ ونحفظ `raw_mae` للتدقيق.
- لا توجد معرفات كتاب، ولا نضمن فصل الطلبة أو الإجابات شبه المتطابقة؛ دي حدود يجب ذكرها في التقرير.

## حدود الاستخدام
- ASAP-SAS تحتوي عادةً على إجابات أطول (~50 كلمة) من مطلوب MENTRIX في Short Answers (1–3 كلمات).
- **لم نثبت صلاحية التصحيح التلقائي** على إجابات MENTRIX، ولا حللنا بعد أخطاء الـOCR على IAM.
- الـConfidence، وTA Review Rate، وBatch Publish ما زالت موضوع اختبارات لاحقة، وليست ناتجة عن هذا السكربت.

## OCR — بعد Sprint 02
- استخدام IAM مع التأكد من حقوق الاستخدام البحثي وتطبيق Writer-Disjoint Split.
- قياس CER/WER على نسخ مكتوبة بشريًا مستقلة عن OCR.
- استخدام Pilot TrOCR E01 Original RGB كتجربة مجمّدة دون اختراع Ground Truth من التوقعات.
- بعد OCR Benchmark، نختبر OCR → Type-aware Grading End-to-End على أوراق كاملة.

## بدون أي تعديل للموقع
لم نغير Frontend أو Backend أو أي ملف من ملفات Sprint 01؛ فقط أضفنا أدوات وتجارب Sprint 02 ووثائق وسكربتين للتشغيل.
