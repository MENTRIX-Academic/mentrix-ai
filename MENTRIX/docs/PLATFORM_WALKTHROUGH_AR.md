# شرح نسخة MENTRIX Original V2 — دليل عملي للـAI Team Lead
**الحالة:** Local typed-answer demonstration — مش production.  
**ملفات الربط:** `static/app.js` → `app.py` → `adapter.py` → `grader_v2.py` + `grader.py` + `questions.json`.

## الشاشة بتعرض إيه؟
- **Live grading demo:** تجربة 4 أسئلة ظاهرة (MC01, SA02, MA03, E01) من 22 سؤالًا موجودًا في بنك الأسئلة.
- **Pipeline workflow:** رحلة الإجابة المكتوبة لحد اعتماد الـTA. مش رحلة OCR.
- **API documentation:** Swagger على `/docs` لتجربة الـRequests والـResponses.
- **Demo environment:** سيرفر محلي. مفيش استضافة عامة أو بيانات طلاب.
- **API-ready:** مسارات HTTP للتجربة، مش API production مضمونة أو مؤمنة.
- **Human-in-the-loop:** كل درجة لازم الـTA يؤكدها. بدون Login فعلي في النسخة التجريبية.
- **Quiz types 04:** سؤال من كل نوع؛ الـEssay بيروح للمراجعة ومش بيتصحح بموديل فعلي هنا.
- **Approval policy 100%:** شرط مراجعة كل درجات، وليس 100% Accuracy.
- **Model training None:** قواعد ومكتبات، دون Fine-tuning أو تدريب جديد في الـDemo.
- **Question type Explicit:** نوع السؤال موجود في `questions.json`، مش متوقع من عدد كلمات الإجابة.

## من ضغط Grade إلى ظهور النتائج
1. Frontend يطلب `GET /api/v1/demo/quiz`، والـBackend يرجع السؤال والنوع والدرجة القصوى بدون إجابة نموذجية.
2. المستخدم يكتب الإجابات ويضغط زرار التصحيح.
3. JavaScript يبعت `POST /api/v1/demo/grade` وبداخله `question_id` و`answer` لكل سؤال.
4. FastAPI يتحقق إن IDs موجودة، وعدد الإجابات مناسب، ومافيش تكرار.
5. `adapter.py` يجيب تعريف السؤال، وينادي **الـV2 الأصلي** ويرتب نتيجة موحدة.
6. الـGrader يرجع `correct` أو `incorrect` أو `review`; الـAdapter يحوّل الأخيرة لـ`needs_review`.
7. النتيجة فيها `proposed_score`, `reason`, `method` و`confidence: null` (مفيش calibrated confidence).
8. الواجهة تعرض النتيجة. الـTA يكتب Final score واسم تجريبي ويضغط Approve.
9. سيرفر الـDemo يحفظ القرار في `ATTEMPTS` داخل RAM فقط؛ أي restart بيضيّعه.

## الحالات اللي أجربها
| سؤال | إجابة | المتوقع من V2 | ليه؟ |
|---|---|---|---|
| MC01 | `Answer: B` | `correct` / 1 | اختيار واحد واضح وصحيح |
| MC01 | `A` | `incorrect` / 0 | اختيار واحد خاطئ |
| MC01 | `A or B` | `needs_review` / null | أكثر من اختيار |
| SA02 | `frequency` | `correct` / 1 | Accepted answer |
| SA02 | `freq` | `needs_review` / null | اختصار غير معتمد صراحة |
| SA02 | `period` | `incorrect` / 0 | Known wrong contrast |
| MA03 | `2 Hz` | `correct` / 1 | قيمة ووحدة صحيحة |
| MA03 | `2.000000001 Hz` | `needs_review` / null | تحتاج سياسة دقة/تقريب |
| E01 | أي إجابة وصفية | `needs_review` / null | Essay engine مش متوصل في الديمو |

## الـAPIs الموجودة فعلًا
- `GET /health` — حالة السيرفر
- `GET /api/v1/demo/quiz` — الأربع أسئلة المعروضة (مع `?all=true` يرجع كل البنك دون answer keys)
- `POST /api/v1/demo/grade` — تصحيح تلقائي مقترح باستخدام V2
- `POST /api/v1/demo/compare` — مقارنة Strict, V1, V2 على نفس الإجابة
- `GET /api/v1/demo/attempts/{attempt_id}` — استرجاع محاولة طالما السيرفر شغال
- `POST /api/v1/demo/attempts/{attempt_id}/items/{question_id}/approve` — محاكاة اعتماد الـTA

**Compare example:**
```json
{"question_id":"SA02","answer":"freq"}
```
الناتج المتوقع: V1 يرفض، V2 يحوّل لمراجعة.

## ملفات المشروع
- `static/index.html`: شكل الصفحة.
- `static/styles.css`: الألوان والتنسيق والـResponsive UI.
- `static/app.js`: الـFrontend بيستخدم `fetch` ويرسم النتايج.
- `app.py`: الـFastAPI endpoints والتحقق المبدئي وحفظ المحاولات في RAM.
- `adapter.py`: يربط الـAPI بكود تصحيح V1/V2 ويحوّل النتيجة لهيكل JSON موحد.
- `questions.json`: الأسئلة والمفاتيح والـAliases ونوع كل سؤال؛ ملف Backend فقط.
- `grader.py`: قواعد Strict وV1 والـMath Parser.
- `grader_v2.py`: القواعد الأحدث المعتمدة على V1 + Conservative Review Policy.
- `tests/test_integrated.py`: Integration tests للـEngine والـAPI.
- `docs/AI_TRACK_ROADMAP.md`: الـ7 phases بعد التحديث.

## التشغيل
من جوه فولدر البرنامج فكّي الضغط بالكامل؛ اقفلي أي سيرفر قديم بنفس البورت بـ`Ctrl+C`، بعدين شغّلي `START_V2_DEMO.bat` أو:
```powershell
py -m pip install -r requirements.txt
py -m uvicorn app:app --reload
```
بعد كده: `http://127.0.0.1:8000`؛ والـSwagger على `http://127.0.0.1:8000/docs`، والـRoadmap على `http://127.0.0.1:8000/roadmap`.

## تنبيهات قبل الدمج مع الفرونت الحقيقي
- لا OCR، ولا رفع صور، ولا Math OCR، ولا تدريب جديد، ولا Essay model متوصل، ولا Chatbot في الديمو.
- مفيش Authentication، أو حساب TA حقيقي، أو Database، أو Audit log دائم، أو حماية مناسبة لبيانات الطلاب.
- كلمة «live» معناها request حقيقي على سيرفر محلي، مش إنه deployed ولا Validated Accuracy.
- Frontend الحالي بيتقدّم من نفس السيرفر (same origin). لو React شغال على بورت مختلف، لازم Dev Proxy أو CORS محدود، مش مفتوح للجميع.
- لا تستخدمي بيانات طلاب حقيقية ولا تنشري السيرفر على الإنترنت.
