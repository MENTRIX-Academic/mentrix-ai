"""MENTRIX unified local pilot: OCR, grading, attendance, data-grounded chatbot.
Local staff PIN session is not a substitute for secure production identity management.
Never expose on a public host or store sensitive real student records without additional controls.
"""
from __future__ import annotations
from pathlib import Path
from uuid import uuid4
from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from adapter import QUESTIONS, SAMPLE_IDS, VERSION, public_quiz, grade
from grading_policy import evaluate
from ocr_integration import router as ocr_router
from attendance_integration import router as attendance_router
from staff_security import router as security_router, valid as staff_valid
from chatbot_integration import router as chatbot_router
from integrated_workflow import router as workflow_router
from handwriting_routes import router as handwriting_router

BUILD_ID='mentrix-integrated-v1-sprint07-handwriting-review-20261104'
app=FastAPI(title='MENTRIX Unified Teaching Assistant',version='0.5.0',
     description='Local OCR + deterministic grading + SQLite attendance + grounded TA chatbot. Essay AI scoring and production authentication NOT implemented.')
STATIC=Path(__file__).resolve().parent/'static'
app.include_router(ocr_router)
app.include_router(chatbot_router)
app.include_router(attendance_router)
app.include_router(security_router)
app.include_router(workflow_router)
app.include_router(handwriting_router)

@app.middleware('http')
async def staff_gate(request:Request,call_next):
    path=request.url.path
    if path.startswith('/api/') and not path.startswith('/api/auth/') and not path.startswith('/api/student/') and not staff_valid(request):
        return JSONResponse({'detail':'Staff sign-in required'},status_code=401)
    return await call_next(request)

app.mount('/static',StaticFiles(directory=STATIC),name='static')
ATTEMPTS={}
class AnswerItem(BaseModel):
    question_id:str=Field(min_length=1,max_length=50)
    answer:str=Field(max_length=2500)
class GradeRequest(BaseModel):
    answers:list[AnswerItem]=Field(min_length=1,max_length=30)
class CompareRequest(BaseModel):
    question_id:str
    answer:str=Field(max_length=2500)
class ApprovalRequest(BaseModel):
    reviewer:str=Field(min_length=2,max_length=80)
    final_score:float=Field(ge=0)
    comment:str=Field(default='',max_length=500)

@app.get('/',include_in_schema=False)
def index():return FileResponse(STATIC/'index.html', headers={'Cache-Control':'no-store, max-age=0','X-MENTRIX-Build':BUILD_ID})
@app.get('/ocr',include_in_schema=False)
def ocr_page():return RedirectResponse('/#grading')
@app.get('/chatbot',include_in_schema=False)
def chatbot_page():return RedirectResponse('/#assistant')
@app.get('/roadmap',include_in_schema=False)
def roadmap():raise HTTPException(404, 'Roadmap was removed from the unified interface')
@app.get('/research',include_in_schema=False)
def research():return RedirectResponse('/#overview')
@app.get('/version',include_in_schema=False)
def version():return {'name':'MENTRIX INTEGRATED','build':BUILD_ID,'main_url':'http://127.0.0.1:8765/','has_legacy_demo_ui':False}
@app.get('/health')
def health():return {'build':BUILD_ID,'status':'ok','mode':'local-research-only','grader_version':VERSION,'ocr':True,'chatbot':'grounded_local_analytics_plus_legacy_optional_ollama','training':False,'essay_grading_model':False,'ocr_storage':'local SQLite','attendance':'SQLite rotating-QR student-ID-PIN demo + TA checks','graded_essays':'human-reviewed-only'}
@app.get('/api/v1/demo/quiz')
def get_quiz(all:bool=False):
    return {'quiz_id':'communication-technology-lecture-02','data_provenance':'original-question-bank-assumed-TA-approved-not-verified','questions':public_quiz(full=all)}
@app.post('/api/v1/demo/compare')
def compare(req:CompareRequest):
    q=QUESTIONS.get(req.question_id)
    if q is None:raise HTTPException(404,'Unknown question ID')
    return {'question_id':req.question_id,'type':q['type'],'answer':req.answer,
      'comparisons':{v:grade(q,req.answer,v) for v in ('strict','v1','v2')},
      'disclaimer':'Author-designed prototype outputs, not validated student accuracy'}
@app.post('/api/v1/demo/grade',status_code=201)
def submit(req:GradeRequest):
    ids=[item.question_id for item in req.answers]
    if len(ids)!=len(set(ids)):raise HTTPException(422,'Duplicate question IDs')
    bad=[qid for qid in ids if qid not in QUESTIONS]
    if bad:raise HTTPException(422,f'Unknown questions: {bad}')
    rows=[]
    for item in req.answers:
        q=QUESTIONS[item.question_id]
        result=evaluate(q,item.answer)
        auto=result["auto_scoring_eligible"]
        rows.append({'question_id':q['question_id'],'question_type':q['type'],
             'max_score':q['max_score'],'submitted_answer':item.answer,
             **result,'final_score':result['proposed_score'] if auto else None,
             'approval_status':'auto_scored' if auto else 'pending_ta',
             'reviewer':'MENTRIX_V2_AUTO_POLICY' if auto else None,'review_comment':None})
    aid=str(uuid4())
    ATTEMPTS[aid]={'attempt_id':aid,'grader_version':VERSION,'source':'local-provisional-scoring' , 'results':rows}
    return ATTEMPTS[aid]
@app.get('/api/v1/demo/attempts/{attempt_id}')
def get_attempt(attempt_id:str):
    if attempt_id not in ATTEMPTS:raise HTTPException(404,'Attempt not found')
    return ATTEMPTS[attempt_id]
@app.post('/api/v1/demo/attempts/{attempt_id}/items/{question_id}/approve')
def approve(attempt_id:str,question_id:str,req:ApprovalRequest):
    attempt=ATTEMPTS.get(attempt_id)
    if attempt is None:raise HTTPException(404,'Attempt not found')
    row=next((r for r in attempt['results'] if r['question_id']==question_id),None)
    if row is None:raise HTTPException(404,'Question missing from attempt')
    if req.final_score>row['max_score']:raise HTTPException(422,'Final score exceeds maximum')
    if row['approval_status']=='approved':raise HTTPException(409,'Already manually approved')
    row.update(final_score=req.final_score, approval_status='approved',reviewer=req.reviewer,review_comment=req.comment)
    return {'attempt_id':attempt_id,'question_id':question_id,'approval_status':'approved','final_score':req.final_score}

# Stable public-facing routes for the unified workspace. Old /demo paths are retained
# for historical scripts, but are not advertised in the new interface.
@app.get('/api/v1/grading/questions')
def grading_questions(all:bool=False):
    return get_quiz(all=all)

@app.post('/api/v1/grading/evaluate',status_code=201)
def grading_evaluate(req:GradeRequest):
    return submit(req)

@app.get('/api/v1/grading/attempts/{attempt_id}')
def grading_attempt(attempt_id:str):
    return get_attempt(attempt_id)

@app.post('/api/v1/grading/attempts/{attempt_id}/items/{question_id}/approve')
def grading_override(attempt_id:str,question_id:str,req:ApprovalRequest):
    return approve(attempt_id,question_id,req)
