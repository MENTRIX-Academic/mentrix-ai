# خطة Fine-tuning اختيارية للـOCR (لم يتم تشغيل تدريب)

**الوضع:** المشروع يستخدم TrOCR مدربًا مسبقًا، وتمت تجربة 5 طرق Preprocessing وSegmentation V2؛ النتائج لا تكفي لاختيار موديل أو نسبة دقة عامة.

1. ابدئي بمراجعة Ground Truth الحالي ومنع تسريب الاختبار السابق إلى بيانات التدريب.
2. استخدمي IAM Handwriting Database الرسمي (مكوّن `lines`) عند توفر تصريح استخدام بحثي غير تجاري والتسجيل، أو Kaggle mirror بعد التحقق من الترخيص وسلامة التطابق بين الصورة وGround Truth.
3. جهزي CSV بالشكل `image_path,text,writer_code,split`، حيث `split` واحد من `train`, `validation`, `test`، و**لا يوجد Writer مشترك بين أي Split**.
4. ابدئي نموذجًا أصغر أو benchmark إضافيًا على GPU، ثم Fine-tune فقط بعد توفر بيانات كافية وميزانية حوسبة (التدريب على CPU للابتوب غير عملي غالبًا). قيّمي CER/WER على Test لم يُستخدم في الاختيار.
5. لا تعتبري نموذج IAM ملائمًا لخط الطلاب أو رموز الرياضيات تلقائيًا؛ بيانات المجال الجديد ضرورية للتحقق.

- قاعدة IAM الرسمية وشروط الاستخدام: https://fki.tic.heia-fr.ch/databases/download-the-iam-handwriting-database
- TrOCR base: https://huggingface.co/microsoft/trocr-base-handwritten
- وثائق TrOCR: https://huggingface.co/docs/transformers/model_doc/trocr

الأداة `validate_training_manifest.py` بتتحقق من التكرار/الصور وتقسيم الكتّاب قبل أي تدريب. **لا تحتوي الحزمة على تدريب منفذ أو موديل Fine-tuned.**

## سكريبت التدريب الاختياري

`finetune_trocr_gpu.py` مثال عملي للتدريب على GPU باستخدام بيانات line-level بمرجع بشري. هذا **لم يُشغّل** داخل المشروع، ولا يصح قبل تجهيز CSV موثوق وفصل الكتّاب والتأكد من الرخصة. قبل التشغيل:

```powershell
python training/validate_training_manifest.py path/to/manifest.csv
pip install -r training/requirements_optional_gpu.txt
python training/finetune_trocr_gpu.py --manifest path/to/manifest.csv --output experiment_model
```

السكريبت يحتاج `torch` نسخة CUDA مناسبة على جهاز GPU، وعمليًا يُفضل Colab GPU أو جهاز آخر؛ لا يُنصح بتدريب TrOCR-base على CPU القديم.
