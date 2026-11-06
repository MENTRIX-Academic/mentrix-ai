# تسليم GitHub — خطوات عملية للـAI Team Lead

## 1) اختاري مكان الملفات
لو عندكم GitHub Repo فيه شغل بالفعل، **ما تعمليش Git init ولا ترفعي ZIP فوق المشروع عشوائيًا**. الأفضل فرع جديد ونسخ الملفات إلى فولدر واضح مثل `ai-grading/` ثم تعديل مسارات التشغيل لو النسخة اتنقلت من جذرها. خلي الحزمة كوحدة مستقلة مؤقتًا.

لو دي أول نسخة داخل Repo خاص بالـAI، ممكن ترفعي الملفات في الجذر كما هي، لأن `app.py` و`adapter.py` محتاجين الملفات النسبية جنب بعض.

## 2) باستخدام Git من Windows — لو عندك الريبو على اللابتوب بالفعل
1. افتحي Repo Folder في VS Code أو PowerShell.
2. شغّلي:
   ```powershell
   git status
   git checkout -b feat/ai-phase1-reproducibility
   ```
3. انسخي **محتويات** فولدر الحزمة إلى المكان المتفق عليه داخل الريبو بدون `.git`، ولا تنسخي ملفات الطلاب الحقيقية.
4. افتحي PowerShell من نفس فولدر الحزمة، شغّلي `py REPRODUCE_PHASE1.py` واحفظي الـOutputs.
5. ارجعي إلى جذر الـGit Repo:
   ```powershell
   git status
   git add .
   git commit -m "Add AI grading v1/v2 reproducible research handoff"
   git push -u origin feat/ai-phase1-reproducibility
   ```
6. افتحي Pull Request: حطي Summary + Tests + Known limitations + Link للقرار المطلوب من الـTA.

**راجعي ناتج `git status` و`git diff --cached --stat` قبل الـCommit** عشان تتأكدي إنك مش بترفعي أي ملف حساس.

## 3) عنوان ومحتوى الـPull Request المقترح
**Title:** `AI: establish reproducible typed-grading research baseline (Strict/V1/V2)`

**Description:**
- Scope: original typed answer grading code + local FastAPI demo + current curated experiment.
- Verification: source SHA256 checks; 20 current unit tests; 29 assistant-authored illustrative cases; new malformed-input crash smoke.
- NOT claimed: original 123-case rerun, human accuracy, OCR, trained models, production API security.
- Missing: original stress input CSVs/test files, independent reproduction, TA policy sign-off, human-labelled holdout.

## 4) تقسيم المهام بين التيم
- **AI Lead:** PR description + manifest + decisions and boundaries.
- **Research Owner:** recover original stress/synthetic CSVs and test scripts, independently reproduce.
- **Grading Owner:** v1/v2 checks and pending issue triage.
- **Backend:** design the production API/auth/persistence; mock API is not deployed.
- **TA/Supervisor:** approve scoring policies and rubric before trusted evaluation.

## 5) GitHub Actions
Workflow at `.github/workflows/ai-reproducibility.yml` runs current reproducibility checks on Python 3.11 and 3.13. CI passing means **current software checks pass**, NOT that real grading has been validated.

## 6) خصوصية
Use a private repo for any drafts that may later contain student-related materials. `questions.json` contains synthetic/demo answer keys: not exposed by public quiz endpoint, but it IS present in repository source. NEVER include protected production answer keys or student content in public code.
