# MENTRIX — OCR / Grading API Contract (Local Research Pilot)

Base URL: `http://127.0.0.1:8010`

## 1) سؤال واحد لكل صورة

`POST /api/v1/ocr/transcribe` — `multipart/form-data`

- `image` = ملف `PNG` أو `JPEG` أو `WEBP` (حتى 12 MB)
- `question_id` = أحد معرفات بنك الأسئلة (`E01`, `E02`, `MC01`, `SA02`, `MA03` وغيرها)
- `writer_code` = كود مجهول لا يحتوي بيانات شخصية
- `boundaries` = JSON array of **image row pixels**، يبدأ من `0` وينتهي عند ارتفاع الصورة، مثل `[0,100,210,320]` لتقسيم الصورة إلى 3 سطور (مع overlap 12px)

الاستجابة `201`: `id`, `ocr_prediction`, `line_predictions`, `line_count`, `status=awaiting_transcription`, `final_score=null`, `model`, `preprocessing`, `image_url`.

الموديل الحقيقي: `microsoft/trocr-base-handwritten`، CPU، Original RGB، صورة *سطر* لكل inference. **لا ينتج درجة** في هذه الخطوة.

## 2) اعتماد النص البشري

`POST /api/v1/ocr/reviews/{id}/verify` — JSON:

```json
{"corrected_text":"Student's writing transcribed exactly","verified":true}
```

الاستجابة: `status=pending_ta`, `decision`, `proposed_score`, `reason`. الأسئلة essay تؤدي دائمًا إلى `needs_review` و`proposed_score=null` لأنها بلا نموذج Essay مُعتمد. بقية أنواع الأسئلة تستخدم `grader_v2.py` الأصلي.

## 3) اعتماد الدرجة النهائي

`POST /api/v1/ocr/reviews/{id}/approve` — JSON:

```json
{"reviewer":"Demo TA","final_score":4.0,"comment":"Reviewed by TA against the rubric"}
```

يرفض الاعتماد قبل مراجعة النص، ويرفض الدرجة فوق `max_score`، ويرفض الاعتماد مرتين. **ملحوظة:** reviewer هنا Alias في Pilot، مش مصادقة رسمية أو RBAC.

## 4) استرجاع المراجعات

- `GET /api/v1/ocr/reviews` قائمة آخر 100 مراجعة محلية
- `GET /api/v1/ocr/reviews/{id}` تفاصيل مراجعة
- `GET /api/v1/ocr/reviews/{id}/image` صورة الإجابة المخزنة محليًا
- `GET /api/v1/ocr/config` معلومات النموذج وبنك الأسئلة
- `GET /docs` وثائق FastAPI التفاعلية

## الفصل البحثي

**Original Typed Demo**: `/` والإندبوينتات `/api/v1/demo/...` تستخدم تخزينًا مؤقتًا ولا تستدعي OCR.

**New OCR Workflow**: `/ocr` والإندبوينتات `/api/v1/ocr/...` تخزن مراجعاتها في SQLite وتحمّل TrOCR عند أول طلب تشغيل. التحسين اليدوي Segmentation V2 في الأبحاث منفصل؛ حدود الصور في الموقع يحددها المستخدم.

## Production TODO

Authentication, role-based permissions, secure data store, encryption, audit trail, consent, retention policy, validated essay model/rubric, automatic question detection, model confidence calibration, stress and deployment testing.
