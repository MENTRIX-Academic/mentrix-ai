# Creating a TA-approved quiz in MENTRIX

Open **Quiz Grading → Approved question bank & materials → Create and approve another quiz**.

1. Enter JSON with a *unique* quiz ID and question IDs (IDs are global in this demo).
2. Click **Create draft quiz**. The quiz is NOT approved yet.
3. Confirm the question text, accepted exact answers, max marks and rubric with the TA.
4. Fill Quiz ID and a meaningful note, then click **Approve question bank**.
5. Choose the quiz when uploading a full answer sheet.

```json
{
  "quiz_id": "AI-QUIZ02",
  "course_id": "AI101",
  "title": "Intro to AI Quiz 2",
  "questions": [
    {
      "id": "Q201", "kind": "mcq", "prompt": "Select supervised learning",
      "answer_key": "A", "allowed_answers": ["A"],
      "rubric": "1 mark for option A", "max_score": 1
    },
    {
      "id": "Q202", "kind": "short", "prompt": "Expand the acronym CPU",
      "answer_key": "central processing unit", "allowed_answers": ["central processing unit"],
      "rubric": "2 marks for exact three-word expansion", "max_score": 2
    },
    {
      "id": "Q203", "kind": "essay", "prompt": "Explain overfitting",
      "answer_key": "", "allowed_answers": [],
      "rubric": "One mark for definition, one for example", "max_score": 2
    }
  ]
}
```

**Grading policy:** only exact MCQ, listed correct short answers with 1-3 words, and exactly matching numeric responses can receive provisional automated scores. Nonmatches, free-form mathematics and essays go to the TA review queue; no automated essay rating model is claimed.

**Handwritten papers:** the OCR draft may be wrong; staff must compare every answer to the original. The app never treats a raw OCR prediction as verified ground truth. Labels `Q1:` etc help parse PDF text, but individual fields can always be corrected manually.
