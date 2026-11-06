"""MENTRIX integrated LOCAL PILOT. No public/production deployment.

Persistent SQLite demo workflows: mock courses/students, rotating QR, student PIN,
full-paper ingestion, deterministic/TA-review grading, batch publication, analytics.
Original research scripts and historical results remain separate and unchanged.
"""
from __future__ import annotations
import base64, hashlib, hmac, io, json, os, re, secrets, sqlite3, time
from contextlib import contextmanager
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from urllib.parse import quote
from uuid import uuid4
from fastapi import APIRouter, File, Form, HTTPException, Request, Response, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel, Field

ROOT=Path(__file__).resolve().parent
PRIVATE=ROOT/'local_private_data'
PRIVATE.mkdir(parents=True,exist_ok=True)
DB=PRIVATE/'mentrix_unified_v1.sqlite3'
UPLOADS=PRIVATE/'paper_uploads'
UPLOADS.mkdir(exist_ok=True)
router=APIRouter(tags=['MENTRIX Integrated V1'])
STUDENT_COOKIE='mentrix_student_demo'
PIN_ITERATIONS=210_000

@contextmanager
def conn():
    db=sqlite3.connect(DB, timeout=20)
    db.row_factory=sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback();raise
    finally: db.close()

def utc(): return int(time.time())
def hashed_pin(pin:str):
    salt=secrets.token_bytes(16)
    return 'pbkdf2_sha256$%d$%s$%s'%(PIN_ITERATIONS,salt.hex(),hashlib.pbkdf2_hmac('sha256',pin.encode(),salt,PIN_ITERATIONS).hex())
def check_pin(pin:str,encoded:str):
    try:
        _,iterations,salt,expected=encoded.split('$')
        result=hashlib.pbkdf2_hmac('sha256',pin.encode(),bytes.fromhex(salt),int(iterations))
        return hmac.compare_digest(result,bytes.fromhex(expected))
    except (ValueError,TypeError,AttributeError):return False

def init_db():
    with conn() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS courses(id TEXT PRIMARY KEY,title TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS sections(id TEXT PRIMARY KEY,course_id TEXT NOT NULL REFERENCES courses(id),room TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS students(id TEXT PRIMARY KEY,name TEXT NOT NULL,section_id TEXT NOT NULL REFERENCES sections(id),pin_hash TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS student_sessions(token_hash TEXT PRIMARY KEY,student_id TEXT NOT NULL REFERENCES students(id),expires_at INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS attendance_sessions(id TEXT PRIMARY KEY,section_id TEXT NOT NULL REFERENCES sections(id),topic TEXT NOT NULL,room TEXT NOT NULL,started_at INTEGER NOT NULL,ends_at INTEGER NOT NULL,closed_at INTEGER,qr_secret TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS checkins(session_id TEXT NOT NULL REFERENCES attendance_sessions(id),student_id TEXT NOT NULL REFERENCES students(id),status TEXT NOT NULL CHECK(status IN ('present','absent','excused','needs_check')),method TEXT NOT NULL,marked_at INTEGER NOT NULL,PRIMARY KEY(session_id,student_id));
        CREATE TABLE IF NOT EXISTS quizzes(id TEXT PRIMARY KEY,course_id TEXT NOT NULL REFERENCES courses(id),title TEXT NOT NULL,approved INTEGER NOT NULL DEFAULT 0,approval_note TEXT NOT NULL DEFAULT '');
        CREATE TABLE IF NOT EXISTS questions(id TEXT PRIMARY KEY,quiz_id TEXT NOT NULL REFERENCES quizzes(id),position INTEGER NOT NULL,kind TEXT NOT NULL CHECK(kind IN ('mcq','short','math','essay')),prompt TEXT NOT NULL,answer_key TEXT NOT NULL,allowed_answers TEXT NOT NULL DEFAULT '[]',rubric TEXT NOT NULL,max_score REAL NOT NULL CHECK(max_score>0));
        CREATE TABLE IF NOT EXISTS materials(id TEXT PRIMARY KEY,course_id TEXT NOT NULL REFERENCES courses(id),filename TEXT NOT NULL,content_text TEXT NOT NULL,uploaded_at INTEGER NOT NULL);
        CREATE TABLE IF NOT EXISTS papers(id TEXT PRIMARY KEY,quiz_id TEXT NOT NULL REFERENCES quizzes(id),student_id TEXT NOT NULL REFERENCES students(id),original_filename TEXT NOT NULL,source_kind TEXT NOT NULL,extracted_text TEXT NOT NULL,transcript_verified INTEGER NOT NULL DEFAULT 0,status TEXT NOT NULL DEFAULT 'needs_transcript',created_at INTEGER NOT NULL,published_at INTEGER);
        CREATE TABLE IF NOT EXISTS grades(paper_id TEXT NOT NULL REFERENCES papers(id),question_id TEXT NOT NULL REFERENCES questions(id),answer_text TEXT NOT NULL,proposed_score REAL,final_score REAL,status TEXT NOT NULL,reason TEXT NOT NULL,reviewer TEXT,review_note TEXT,PRIMARY KEY(paper_id,question_id));
        CREATE TABLE IF NOT EXISTS audit(id INTEGER PRIMARY KEY AUTOINCREMENT,event TEXT NOT NULL,entity_id TEXT NOT NULL,details TEXT NOT NULL,created_at INTEGER NOT NULL);
        ''')
        if db.execute('SELECT COUNT(*) FROM courses').fetchone()[0]:return
        courses=[('AI101','Artificial Intelligence'),('CG201','Computer Graphics')]
        db.executemany('INSERT INTO courses VALUES (?,?)',courses)
        db.executemany('INSERT INTO sections VALUES(?,?,?)',[('AI-SEC01','AI101','Lab 3'),('CG-SEC01','CG201','Lab 5')])
        # 30 names are explicitly synthetic; no real student data used.
        for i in range(1,31):
            db.execute('INSERT INTO students VALUES(?,?,?,?)',(f'ST{i:03}',f'Demo Student {i:02}', 'AI-SEC01', hashed_pin(f'{740000+i:06}')))
        db.execute('INSERT INTO quizzes VALUES(?,?,?,?,?)',('AI-QUIZ01','AI101','AI Fundamentals — Demo Quiz',1,'DEMO-APPROVED ONLY: fictional key/rubric, not institution-certified'))
        q=[
          ('Q1','mcq','Which type of learning uses labeled training examples?','B',['B'],'Exact selected option: B',1),
          ('Q2','short','What does CPU stand for?','central processing unit',['central processing unit'],'Exact 1–3 words only. Alternative wording requires TA review.',2),
          ('Q3','math','Calculate 2 + 3.','5',['5'],'Exact numeric equivalent; algebraic expressions require TA review.',2),
          ('Q4','essay','Explain supervised vs unsupervised learning.','',[],'2 marks supervised explanation; 2 marks unsupervised explanation; 1 mark comparison. TA-scored only.',5),
        ]
        for pos,(qid,kind,prompt,key,allowed,rubric,max_score) in enumerate(q,1):
            db.execute('INSERT INTO questions VALUES(?,?,?,?,?,?,?,?,?)',(qid,'AI-QUIZ01',pos,kind,prompt,key,json.dumps(allowed),rubric,max_score))
        db.execute('INSERT INTO audit(event,entity_id,details,created_at) VALUES (?,?,?,?)',('demo_seed','all','30 synthetic students, two courses, one sample quiz',utc()))
init_db()

def staff_required(request:Request):
    from staff_security import valid
    if not valid(request):raise HTTPException(401,'TA/Admin sign-in required')

def student_identity(request:Request):
    token=request.cookies.get(STUDENT_COOKIE,'')
    if not token:return None
    with conn() as db:
        row=db.execute('SELECT student_id FROM student_sessions WHERE token_hash=? AND expires_at>?',(hashlib.sha256(token.encode()).hexdigest(),utc())).fetchone()
    return row['student_id'] if row else None

def safe_id(raw):
    if not re.fullmatch(r'[A-Za-z0-9_-]{2,40}',raw):raise HTTPException(422,'Invalid ID')
    return raw

def audit(db,event,entity,details):
    db.execute('INSERT INTO audit(event,entity_id,details,created_at) VALUES(?,?,?,?)',(event,entity,json.dumps(details,ensure_ascii=False),utc()))

def signed_qr(s):
    slot=utc()//30
    tag=hmac.new(s['qr_secret'].encode(),f"{s['id']}:{slot}".encode(),hashlib.sha256).hexdigest()[:24]
    return f'{slot}.{tag}'

def verify_qr(s,token):
    try:
        slot_s,sig=token.split('.')
        slot=int(slot_s)
    except (ValueError,AttributeError):return False
    if slot not in (utc()//30,utc()//30-1):return False
    expected=hmac.new(s['qr_secret'].encode(),f"{s['id']}:{slot}".encode(),hashlib.sha256).hexdigest()[:24]
    return hmac.compare_digest(sig,expected)

class StudentLogin(BaseModel):
    student_id:str=Field(min_length=3,max_length=40)
    pin:str=Field(min_length=6,max_length=32)

@router.post('/api/student/login')
def student_login(body:StudentLogin,response:Response):
    sid=safe_id(body.student_id.upper())
    with conn() as db:
        st=db.execute('SELECT * FROM students WHERE id=?',(sid,)).fetchone()
        if not st or not check_pin(body.pin,st['pin_hash']):raise HTTPException(401,'Invalid Student ID or PIN')
        token=secrets.token_urlsafe(32)
        db.execute('INSERT INTO student_sessions VALUES (?,?,?)',(hashlib.sha256(token.encode()).hexdigest(),sid,utc()+3600))
    response.set_cookie(STUDENT_COOKIE,token,httponly=True,samesite='lax',secure=False,max_age=3600,path='/')
    return {'student_id':sid,'name':st['name'],'section_id':st['section_id']}

@router.get('/api/student/session')
def student_session(request:Request):
    student_id=student_identity(request)
    return {'authenticated':bool(student_id),'student_id':student_id}

@router.post('/api/student/logout')
def student_logout(request:Request,response:Response):
    token=request.cookies.get(STUDENT_COOKIE,'')
    if token:
        with conn() as db:db.execute('DELETE FROM student_sessions WHERE token_hash=?',(hashlib.sha256(token.encode()).hexdigest(),))
    response.delete_cookie(STUDENT_COOKIE,path='/')
    return {'authenticated':False}

class Checkin(BaseModel):
    session_id:str
    token:str

@router.post('/api/student/checkin')
def checkin(body:Checkin,request:Request):
    student_id=student_identity(request)
    if not student_id:raise HTTPException(401,'Sign in with Student ID + PIN first')
    with conn() as db:
        s=db.execute('SELECT * FROM attendance_sessions WHERE id=?',(body.session_id,)).fetchone()
        student=db.execute('SELECT * FROM students WHERE id=?',(student_id,)).fetchone()
        if not s:raise HTTPException(404,'Session not found')
        if student['section_id']!=s['section_id']:raise HTTPException(403,'Student is not enrolled in this section')
        if s['closed_at'] is not None or utc()>s['ends_at']:raise HTTPException(409,'Attendance window is closed')
        if not verify_qr(s,body.token):raise HTTPException(422,'Expired or invalid QR; scan the current code')
        old=db.execute('SELECT status FROM checkins WHERE session_id=? AND student_id=?',(s['id'],student_id)).fetchone()
        if old:return {'registered':True,'status':old['status'],'already_registered':True}
        db.execute('INSERT INTO checkins VALUES(?,?,?,?,?)',(s['id'],student_id,'present','rotating_qr',utc()))
        audit(db,'qr_checkin',s['id'],{'student_id':student_id})
    return {'registered':True,'student_id':student_id,'status':'present','already_registered':False}

class OpenAttendance(BaseModel):
    section_id:str
    topic:str=Field(min_length=1,max_length=120)
    room:str=Field(min_length=1,max_length=80)
    duration_minutes:int=Field(default=5,ge=1,le=60)

@router.get('/api/workspace/dashboard')
def dashboard(request:Request):
    staff_required(request)
    with conn() as db:
        stats={k:db.execute(f'SELECT COUNT(*) FROM {t}').fetchone()[0] for k,t in [('students','students'),('sections','sections'),('sessions','attendance_sessions'),('quizzes','quizzes'),('papers','papers')]}
        stats['checked_in']=db.execute("SELECT COUNT(*) FROM checkins WHERE status IN ('present','needs_check')").fetchone()[0]
        stats['absent']=db.execute("SELECT COUNT(*) FROM checkins WHERE status='absent'").fetchone()[0]
        stats['needs_review']=db.execute("SELECT COUNT(*) FROM grades WHERE status='pending_ta'").fetchone()[0]
        stats['published_papers']=db.execute("SELECT COUNT(*) FROM papers WHERE status='published'").fetchone()[0]
    return {'stats':stats,'demo':True,'student_records':'synthetic'}

@router.get('/api/workspace/courses')
def courses(request:Request):
    staff_required(request)
    with conn() as db:
        return {'courses':[dict(x) for x in db.execute('SELECT * FROM courses ORDER BY id')],
                'sections':[dict(x) for x in db.execute('SELECT * FROM sections ORDER BY id')]}

@router.get('/api/workspace/students')
def workspace_students(request:Request,section_id:str='AI-SEC01'):
    staff_required(request)
    with conn() as db:
        return {'students':[dict(x) for x in db.execute('SELECT id,name,section_id FROM students WHERE section_id=? ORDER BY id',(section_id,))]}

@router.post('/api/workspace/attendance/open')
def open_attendance(body:OpenAttendance,request:Request):
    staff_required(request)
    with conn() as db:
        sec=db.execute('SELECT * FROM sections WHERE id=?',(body.section_id,)).fetchone()
        if not sec:raise HTTPException(404,'Unknown section')
        sid='AT-'+uuid4().hex[:10].upper();now=utc()
        db.execute('INSERT INTO attendance_sessions VALUES(?,?,?,?,?,?,?,?)',(sid,body.section_id,body.topic,body.room,now,now+60*body.duration_minutes,None,secrets.token_hex(32)))
        audit(db,'attendance_open',sid,{'section_id':body.section_id,'duration_minutes':body.duration_minutes})
    return {'session_id':sid,'section_id':body.section_id,'ends_at':now+60*body.duration_minutes,'status':'open'}

@router.get('/api/workspace/attendance/sessions')
def attendance_sessions(request:Request):
    staff_required(request)
    with conn() as db:
        data=[]
        for r in db.execute('SELECT s.*,c.title AS course_title FROM attendance_sessions s JOIN sections x ON x.id=s.section_id JOIN courses c ON c.id=x.course_id ORDER BY started_at DESC LIMIT 50'):
            d=dict(r);d.pop('qr_secret');d['status']='closed' if d['closed_at'] is not None else ('expired' if utc()>d['ends_at'] else 'open');data.append(d)
        return {'sessions':data}

@router.get('/api/workspace/attendance/{session_id}/qr')
def attendance_qr(session_id:str,request:Request):
    staff_required(request)
    with conn() as db:s=db.execute('SELECT * FROM attendance_sessions WHERE id=?',(session_id,)).fetchone()
    if not s:raise HTTPException(404,'Session not found')
    if s['closed_at'] is not None or utc()>s['ends_at']:raise HTTPException(409,'Session closed/expired')
    token=signed_qr(s)
    base=os.getenv('MENTRIX_BASE_URL','http://127.0.0.1:8765').rstrip('/')
    url=f'{base}/checkin?session={quote(s["id"])}&token={quote(token)}'
    try:
        import qrcode
        img=qrcode.make(url)
        b=io.BytesIO();img.save(b,format='PNG');image='data:image/png;base64,'+base64.b64encode(b.getvalue()).decode()
    except ImportError:
        image=None
    return {'session_id':s['id'],'url':url,'qr_image':image,'refresh_seconds':30,'expires_at':s['ends_at'],
            'notice':'Loopback QR works only on this computer. For phone scanning use a secured reachable HTTPS base URL.'}

@router.get('/api/workspace/attendance/{session_id}/register')
def attendance_register(session_id:str,request:Request):
    staff_required(request)
    with conn() as db:
        ses=db.execute('SELECT * FROM attendance_sessions WHERE id=?',(session_id,)).fetchone()
        if not ses:raise HTTPException(404,'Session not found')
        rows=[dict(r) for r in db.execute('''SELECT st.id,st.name,ck.status,ck.method FROM students st LEFT JOIN checkins ck ON ck.student_id=st.id AND ck.session_id=? WHERE st.section_id=? ORDER BY st.id''',(session_id,ses['section_id']))]
        return {'session_id':session_id,'register':rows,'counts':{'present':sum(r['status']=='present' for r in rows),'needs_check':sum(r['status']=='needs_check' for r in rows),'absent':sum(r['status']=='absent' for r in rows),'unmarked':sum(r['status'] is None for r in rows)},'unmarked_means':'unknown until TA closes'}

@router.post('/api/workspace/attendance/{session_id}/random-check')
def random_check(session_id:str,request:Request):
    staff_required(request)
    with conn() as db:
        ses=db.execute('SELECT * FROM attendance_sessions WHERE id=?',(session_id,)).fetchone()
        if not ses:raise HTTPException(404,'Session not found')
        if ses['closed_at'] is not None:raise HTTPException(409,'Closed session')
        items=[r['student_id'] for r in db.execute("SELECT student_id FROM checkins WHERE session_id=? AND status='present'",(session_id,))]
        chosen=secrets.SystemRandom().sample(items,k=min(3,len(items)))
        for sid in chosen:db.execute("UPDATE checkins SET status='needs_check' WHERE session_id=? AND student_id=?",(session_id,sid))
        audit(db,'random_check',session_id,{'student_ids':chosen})
    return {'selected_students':chosen,'note':'TA must visually verify these students and mark present/absent'}

class Mark(BaseModel):
    student_id:str
    status:str=Field(pattern='^(present|absent|excused)$')

@router.post('/api/workspace/attendance/{session_id}/mark')
def staff_mark(session_id:str,body:Mark,request:Request):
    staff_required(request)
    with conn() as db:
        ses=db.execute('SELECT * FROM attendance_sessions WHERE id=?',(session_id,)).fetchone()
        st=db.execute('SELECT * FROM students WHERE id=?',(body.student_id,)).fetchone()
        if not ses or not st:raise HTTPException(404,'Unknown student/session')
        if ses['closed_at'] is not None:raise HTTPException(409,'Closed session; unlock requires admin workflow')
        if st['section_id']!=ses['section_id']:raise HTTPException(409,'Student/section mismatch')
        db.execute('INSERT INTO checkins VALUES (?,?,?,?,?) ON CONFLICT(session_id,student_id) DO UPDATE SET status=excluded.status,method=excluded.method,marked_at=excluded.marked_at',(session_id,body.student_id,body.status,'ta_verified',utc()))
        audit(db,'attendance_manual',session_id,{'student_id':body.student_id,'status':body.status})
    return {'saved':True,'status':body.status}

@router.post('/api/workspace/attendance/{session_id}/close')
def close_attendance(session_id:str,request:Request):
    staff_required(request)
    with conn() as db:
        ses=db.execute('SELECT * FROM attendance_sessions WHERE id=?',(session_id,)).fetchone()
        if not ses:raise HTTPException(404,'Session not found')
        if ses['closed_at'] is not None:raise HTTPException(409,'Already closed')
        pending=db.execute("SELECT COUNT(*) FROM checkins WHERE session_id=? AND status='needs_check'",(session_id,)).fetchone()[0]
        if pending:raise HTTPException(409,f'Complete {pending} random verification(s) first')
        students=db.execute('SELECT id FROM students WHERE section_id=?',(ses['section_id'],)).fetchall()
        absent=0
        for r in students:
            result=db.execute("INSERT OR IGNORE INTO checkins VALUES (?,?,?,?,?)",(session_id,r['id'],'absent','finalize_missing_after_ta_close',utc()))
            absent+=result.rowcount
        db.execute('UPDATE attendance_sessions SET closed_at=? WHERE id=?',(utc(),session_id))
        audit(db,'attendance_close',session_id,{'newly_marked_absent':absent})
    return {'closed':True,'newly_marked_absent':absent,'policy':'TA explicitly finalizes missing check-ins'}

# ---- Approved mock quiz bank + whole-paper ingestion + exception-only review ----
@router.get('/api/workspace/quizzes')
def quizzes(request:Request):
    staff_required(request)
    with conn() as db:
        return {'quizzes':[dict(x) for x in db.execute('SELECT * FROM quizzes ORDER BY title')]}

def fetch_questions(db,quiz_id):
    return [dict(x) for x in db.execute('SELECT * FROM questions WHERE quiz_id=? ORDER BY position',(quiz_id,))]

@router.get('/api/workspace/quizzes/{quiz_id}')
def quiz_detail(quiz_id:str,request:Request):
    staff_required(request)
    with conn() as db:
        quiz=db.execute('SELECT * FROM quizzes WHERE id=?',(quiz_id,)).fetchone()
        if not quiz:raise HTTPException(404,'Unknown quiz')
        return {'quiz':dict(quiz),'questions':fetch_questions(db,quiz_id),
                'notice':'Approved flag for seeded quiz is DEMO ONLY, not official TA approval.'}

class NewQuestion(BaseModel):
    id:str=Field(min_length=2,max_length=40)
    kind:str=Field(pattern='^(mcq|short|math|essay)$')
    prompt:str=Field(min_length=3,max_length=2000)
    answer_key:str=Field(default='',max_length=500)
    allowed_answers:list[str]=Field(default_factory=list,max_length=30)
    rubric:str=Field(min_length=5,max_length=3000)
    max_score:float=Field(gt=0,le=100)
class NewQuiz(BaseModel):
    quiz_id:str
    course_id:str
    title:str=Field(min_length=4,max_length=120)
    questions:list[NewQuestion]=Field(min_length=1,max_length=40)

@router.post('/api/workspace/quizzes')
def create_quiz(body:NewQuiz,request:Request):
    staff_required(request)
    qid=safe_id(body.quiz_id)
    if len({q.id for q in body.questions})!=len(body.questions):raise HTTPException(422,'Duplicate question IDs')
    with conn() as db:
        if not db.execute('SELECT id FROM courses WHERE id=?',(body.course_id,)).fetchone():raise HTTPException(404,'Course not found')
        if db.execute('SELECT id FROM quizzes WHERE id=?',(qid,)).fetchone():raise HTTPException(409,'Quiz ID already used')
        db.execute('INSERT INTO quizzes VALUES(?,?,?,?,?)',(qid,body.course_id,body.title,0,'Awaiting explicit staff approval'))
        for pos,q in enumerate(body.questions,1):
            db.execute('INSERT INTO questions VALUES(?,?,?,?,?,?,?,?,?)',(safe_id(q.id),qid,pos,q.kind,q.prompt,q.answer_key,json.dumps(q.allowed_answers),q.rubric,q.max_score))
        audit(db,'quiz_create',qid,{'questions':len(body.questions)})
    return {'quiz_id':qid,'approved':False}

class QuizApprove(BaseModel):
    approval_note:str=Field(min_length=10,max_length=400)

@router.post('/api/workspace/quizzes/{quiz_id}/approve')
def approve_quiz(quiz_id:str,body:QuizApprove,request:Request):
    staff_required(request)
    with conn() as db:
        if not db.execute('SELECT id FROM quizzes WHERE id=?',(quiz_id,)).fetchone():raise HTTPException(404,'Quiz not found')
        db.execute('UPDATE quizzes SET approved=1,approval_note=? WHERE id=?',(body.approval_note,quiz_id))
        audit(db,'quiz_approved',quiz_id,{'note':body.approval_note})
    return {'approved':True,'quiz_id':quiz_id}

@router.post('/api/workspace/materials/{course_id}')
async def material_upload(course_id:str,request:Request,file:UploadFile=File(...)):
    staff_required(request)
    raw=await file.read(3_000_001)
    if len(raw)>3_000_000:raise HTTPException(413,'Material max 3 MB')
    fname=Path(file.filename or '').name
    if not fname.lower().endswith(('.txt','.pdf')):raise HTTPException(422,'Only PDF/TXT course materials')
    try:
        if fname.lower().endswith('.txt'):data=raw.decode('utf-8-sig')
        else:
            import fitz
            with fitz.open(stream=raw,filetype='pdf') as doc:
                if len(doc)>40:raise HTTPException(422,'Max 40 material pages')
                data='\n'.join(page.get_text() for page in doc)
    except (UnicodeDecodeError,ImportError,ValueError,RuntimeError) as exc:
        raise HTTPException(422,'Material cannot be read: '+str(exc)[:100]) from exc
    with conn() as db:
        if not db.execute('SELECT id FROM courses WHERE id=?',(course_id,)).fetchone():raise HTTPException(404,'Course not found')
        mid='MAT-'+uuid4().hex[:10]
        db.execute('INSERT INTO materials VALUES(?,?,?,?,?)',(mid,course_id,fname,data[:300_000],utc()))
        audit(db,'material_upload',mid,{'course_id':course_id,'filename':fname})
    return {'material_id':mid,'characters_extracted':len(data),'notice':'Course material is stored locally for TA reference; NOT independently a grading ground truth.'}

@router.get('/api/workspace/materials/{course_id}')
def list_materials(course_id:str,request:Request):
    staff_required(request)
    with conn() as db:return {'materials':[dict(x) for x in db.execute('SELECT id,course_id,filename,LENGTH(content_text) AS characters,uploaded_at FROM materials WHERE course_id=?',(course_id,))]}


def ocr_page_image(image):
    try:
        import pytesseract
        return pytesseract.image_to_string(image,lang='eng',config='--psm 6')
    except Exception:
        return ''

def extract_paper(raw:bytes,filename:str):
    filename=Path(filename).name[:120]
    if raw.startswith(b'%PDF-'):
        try:
            import fitz
            with fitz.open(stream=raw,filetype='pdf') as doc:
                if len(doc)>8:raise HTTPException(422,'Full-paper limit 8 pages')
                if not doc:raise HTTPException(422,'Empty PDF')
                out=[];ocr_pages=0
                for page in doc:
                    txt=page.get_text().strip()
                    if len(txt)<15:
                        pix=page.get_pixmap(matrix=fitz.Matrix(1.8,1.8),alpha=False)
                        from PIL import Image
                        txt=ocr_page_image(Image.open(io.BytesIO(pix.tobytes('png'))))
                        ocr_pages+=1
                    out.append(txt)
                return '\n\n'.join(out),'pdf_text_plus_tesseract' if ocr_pages else 'pdf_embedded_text'
        except (RuntimeError,ValueError,ImportError) as exc:
            raise HTTPException(422,'Cannot read PDF: '+str(exc)[:100]) from exc
    if raw[:3]==b'\xff\xd8\xff' or raw.startswith(b'\x89PNG\r\n\x1a\n') or raw[:4]==b'RIFF':
        try:
            from PIL import Image,ImageOps
            with Image.open(io.BytesIO(raw)) as image:
                if image.width*image.height>18_000_000:raise HTTPException(422,'Image too large')
                if image.width<100 or image.height<100:raise HTTPException(422,'Image too small')
                image=ImageOps.exif_transpose(image).convert('RGB')
                return ocr_page_image(image),'tesseract_image_draft'
        except (OSError,ValueError) as exc:
            raise HTTPException(422,'Invalid image: '+str(exc)[:100]) from exc
    raise HTTPException(422,'Only valid PDF, PNG, JPG or WEBP files are accepted')

@router.post('/api/workspace/papers/upload')
async def paper_upload(request:Request,quiz_id:str=Form(...),student_id:str=Form(...),file:UploadFile=File(...)):
    staff_required(request)
    raw=await file.read(10_000_001)
    if not raw:raise HTTPException(422,'Empty file')
    if len(raw)>10_000_000:raise HTTPException(413,'Paper max 10 MB')
    with conn() as db:
        quiz=db.execute('SELECT * FROM quizzes WHERE id=?',(quiz_id,)).fetchone()
        st=db.execute('SELECT * FROM students WHERE id=?',(student_id,)).fetchone()
        if not quiz or not st:raise HTTPException(404,'Quiz/student not found')
        if not quiz['approved']:raise HTTPException(409,'Question bank must be staff approved before grading')
        section=db.execute('SELECT course_id FROM sections WHERE id=?',(st['section_id'],)).fetchone()
        if section['course_id']!=quiz['course_id']:raise HTTPException(409,'Student not enrolled in course')
    text,method=extract_paper(raw,file.filename or '')
    pid='P-'+uuid4().hex[:12].upper()
    ext='.pdf' if raw.startswith(b'%PDF-') else '.png' if raw.startswith(b'\x89PNG') else '.jpg' if raw[:3]==b'\xff\xd8\xff' else '.webp'
    (UPLOADS/(pid+ext)).write_bytes(raw)
    with conn() as db:
        db.execute('INSERT INTO papers VALUES(?,?,?,?,?,?,0,?,?,NULL)',(pid,quiz_id,student_id,Path(file.filename or 'paper').name[:120],method,text,'needs_transcript',utc()))
        audit(db,'paper_upload',pid,{'method':method,'quiz_id':quiz_id,'student_id':student_id})
    return {'paper_id':pid,'extracted_text':text,'extraction_method':method,'status':'needs_transcript',
            'warning':'OCR draft is NOT verified; staff must check all words against the image. Image handwriting may be missed.'}

@router.get('/api/workspace/papers')
def list_papers(request:Request):
    staff_required(request)
    with conn() as db:
        return {'papers':[dict(r) for r in db.execute('''SELECT p.id,p.quiz_id,p.student_id,p.original_filename,p.status,p.created_at,p.published_at,
            (SELECT COUNT(*) FROM grades g WHERE g.paper_id=p.id AND g.status='pending_ta') AS pending_count
            FROM papers p ORDER BY created_at DESC LIMIT 100''')]}

@router.get('/api/workspace/papers/{paper_id}')
def paper_detail(paper_id:str,request:Request):
    staff_required(request)
    with conn() as db:
        paper=db.execute('SELECT * FROM papers WHERE id=?',(paper_id,)).fetchone()
        if not paper:raise HTTPException(404,'Paper not found')
        grades=[dict(x) for x in db.execute('''SELECT g.*,q.prompt,q.kind,q.max_score,q.rubric FROM grades g JOIN questions q ON q.id=g.question_id WHERE g.paper_id=? ORDER BY q.position''',(paper_id,))]
        return {'paper':dict(paper),'grades':grades,'questions':fetch_questions(db,paper['quiz_id'])}

@router.get('/api/workspace/papers/{paper_id}/original')
def paper_original(paper_id:str,request:Request):
    staff_required(request)
    files=[p for p in UPLOADS.glob(paper_id+'.*') if p.is_file()]
    if not files:raise HTTPException(404,'File not found')
    media={'pdf':'application/pdf','png':'image/png','jpg':'image/jpeg','webp':'image/webp'}.get(files[0].suffix[1:],'application/octet-stream')
    return FileResponse(files[0],media_type=media,headers={'X-Content-Type-Options':'nosniff','Content-Disposition':'inline'})

# A full-paper parser is a convenience for clearly labeled Q1: ... Q2: ... documents.
# Anything ambiguous stays in TA review; extraction text is NEVER silently accepted.
def parse_labeled_answers(text:str):
    labels=list(re.finditer(r'(?im)^\s*(Q\s*\d{1,4})\s*[:\)\-\.]\s*',text))
    results={}
    for i,m in enumerate(labels):
        key=m.group(1).replace(' ','').upper()
        end=labels[i+1].start() if i+1<len(labels) else len(text)
        if key in results:results[key]=''  # ambiguous repeated label
        else: results[key]=text[m.end():end].strip()
    return results

def normalized(t):return re.sub(r'\s+',' ',t.strip().lower().strip(' .,:;!?'))

def grade_rule(q,answer):
    n=normalized(answer);kind=q['kind'];key=normalized(q['answer_key'])
    if not n:return (None,'pending_ta','No answer detected; staff checks original paper')
    if kind=='mcq':
        if re.fullmatch('[abcd]',n):return (q['max_score'] if n==key else 0.,'auto_scored','Deterministic MCQ key match')
        return (None,'pending_ta','Ambiguous MCQ selection')
    if kind=='short':
        accepted=[normalized(x) for x in json.loads(q['allowed_answers'])]
        if n in accepted and 1<=len(n.split())<=3:return (q['max_score'],'auto_scored','Exact TA-approved short-answer match')
        return (None,'pending_ta','Short-answer paraphrase/incorrect/length needs rubric review')
    if kind=='math':
        try:
            if not re.fullmatch(r'[+-]?\d+(?:\.\d+)?',n):raise InvalidOperation()
            if Decimal(n)==Decimal(key):return (q['max_score'],'auto_scored','Exact numeric equivalence')
        except (InvalidOperation,ValueError):pass
        return (None,'pending_ta','Math expression/incorrect needs TA equivalence review')
    return (None,'pending_ta','Essay needs rubric-based human grading; unvalidated AI disabled')

class ConfirmTranscript(BaseModel):
    corrected_text:str=Field(max_length=20000)
    answers:dict[str,str]=Field(default_factory=dict)
    verified:bool

@router.post('/api/workspace/papers/{paper_id}/verify-and-grade')
def paper_verify(paper_id:str,body:ConfirmTranscript,request:Request):
    staff_required(request)
    if not body.verified:raise HTTPException(422,'Staff must verify text against the paper')
    with conn() as db:
        paper=db.execute('SELECT * FROM papers WHERE id=?',(paper_id,)).fetchone()
        if not paper:raise HTTPException(404,'Paper not found')
        if paper['published_at'] is not None:raise HTTPException(409,'Published paper cannot be edited')
        questions=fetch_questions(db,paper['quiz_id'])
        parsed=parse_labeled_answers(body.corrected_text)
        provided={str(k).upper():str(v)[:4000] for k,v in body.answers.items()}
        entries=[]
        for q in questions:
            ans=provided.get(q['id'],parsed.get(q['id'],''))
            proposed,status,reason=grade_rule(q,ans)
            db.execute('''INSERT INTO grades(paper_id,question_id,answer_text,proposed_score,final_score,status,reason,reviewer,review_note)
                VALUES (?,?,?,?,?,?,?,NULL,NULL)
                ON CONFLICT(paper_id,question_id) DO UPDATE SET answer_text=excluded.answer_text,proposed_score=excluded.proposed_score,
                final_score=excluded.final_score,status=excluded.status,reason=excluded.reason,reviewer=NULL,review_note=NULL''',
                (paper_id,q['id'],ans,proposed,proposed if status=='auto_scored' else None,status,reason))
            entries.append({'question_id':q['id'],'status':status,'proposed_score':proposed,'reason':reason})
        db.execute('UPDATE papers SET extracted_text=?,transcript_verified=1,status=? WHERE id=?',(body.corrected_text,'graded',paper_id))
        audit(db,'paper_verified',paper_id,{'manual_review_count':sum(x['status']=='pending_ta' for x in entries)})
    return {'paper_id':paper_id,'grades':entries,'batch_publish_ready':all(e['status']=='auto_scored' for e in entries)}

class ReviewGrade(BaseModel):
    final_score:float=Field(ge=0)
    reviewer:str=Field(min_length=2,max_length=80)
    note:str=Field(min_length=3,max_length=1500)

@router.post('/api/workspace/papers/{paper_id}/grades/{question_id}/review')
def review_grade(paper_id:str,question_id:str,body:ReviewGrade,request:Request):
    staff_required(request)
    with conn() as db:
        paper=db.execute('SELECT * FROM papers WHERE id=?',(paper_id,)).fetchone()
        row=db.execute('SELECT g.status,q.max_score FROM grades g JOIN questions q ON q.id=g.question_id WHERE g.paper_id=? AND q.id=?',(paper_id,question_id)).fetchone()
        if not paper or not row:raise HTTPException(404,'Paper/question not found')
        if paper['published_at']:raise HTTPException(409,'Already published')
        if body.final_score>row['max_score']:raise HTTPException(422,'Exceeds question maximum')
        db.execute('UPDATE grades SET status=?,final_score=?,reviewer=?,review_note=? WHERE paper_id=? AND question_id=?',('reviewed',body.final_score,body.reviewer,body.note,paper_id,question_id))
        audit(db,'grade_review',paper_id,{'question_id':question_id,'final_score':body.final_score,'reviewer':body.reviewer})
    return {'reviewed':True,'question_id':question_id,'final_score':body.final_score}

class BatchPublish(BaseModel):
    paper_ids:list[str]=Field(min_length=1,max_length=100)

@router.post('/api/workspace/papers/publish-batch')
def publish_batch(body:BatchPublish,request:Request):
    staff_required(request)
    if len(set(body.paper_ids))!=len(body.paper_ids):raise HTTPException(422,'Duplicate papers')
    with conn() as db:
        for pid in body.paper_ids:
            paper=db.execute('SELECT * FROM papers WHERE id=?',(pid,)).fetchone()
            if not paper or not paper['transcript_verified'] or paper['published_at'] is not None:raise HTTPException(409,f'Paper {pid} is missing, unverified, or already published')
            expected=db.execute('SELECT COUNT(*) FROM questions WHERE quiz_id=?',(paper['quiz_id'],)).fetchone()[0]
            row=db.execute('SELECT COUNT(*) AS n,SUM(CASE WHEN final_score IS NULL OR status NOT IN (\'reviewed\',\'auto_scored\') THEN 1 ELSE 0 END) AS pending FROM grades WHERE paper_id=?',(pid,)).fetchone()
            if row['n']!=expected or row['pending']:raise HTTPException(409,f'Paper {pid} has unresolved grades')
        for pid in body.paper_ids:
            db.execute("UPDATE papers SET published_at=?,status='published' WHERE id=?",(utc(),pid))
            audit(db,'paper_published',pid,{'approved_by':'authenticated_staff'})
    return {'published':len(body.paper_ids),'paper_ids':body.paper_ids}

# ---- Data-backed assistant: allowlisted intents, parameterized SQL, no invented values ----
class Ask(BaseModel):
    message:str=Field(min_length=2,max_length=1200)

@router.post('/api/workspace/assistant/ask')
def assistant_ask(body:Ask,request:Request):
    staff_required(request)
    text=body.message.strip();q=text.lower()
    sid_match=re.search(r'\bST\d{3}\b',text,re.I)
    section_match=re.search(r'\b(?:AI-SEC\d{2}|CG-SEC\d{2})\b',text,re.I)
    if sid_match:
        sid=sid_match.group(0).upper()
        with conn() as db:
            student=db.execute('SELECT id,name,section_id FROM students WHERE id=?',(sid,)).fetchone()
            if not student:return {'answer':f'No student found for {sid}.','source':'students','rows':[]}
            rec=[dict(x) for x in db.execute('''SELECT ck.status,ats.topic,ats.started_at,ats.id as session_id FROM attendance_sessions ats
              LEFT JOIN checkins ck ON ck.session_id=ats.id AND ck.student_id=? WHERE ats.section_id=? ORDER BY ats.started_at DESC''',(sid,student['section_id']))]
            counts={key:sum(r['status']==key for r in rec) for key in ('present','absent','excused','needs_check')}
            counts['unmarked']=sum(r['status'] is None for r in rec)
            if any(w in q for w in ['latest','last session','آخر','اخر','حضر اخر']):
                if not rec:return {'answer':f'{sid} has no attendance sessions recorded.','source':'attendance_sessions','rows':[]}
                latest=rec[0];stat=latest['status'] or 'unknown'
                return {'answer':f'{sid} latest session {latest["session_id"]}: {stat}.','source':'checkins LEFT JOIN attendance_sessions','rows':[latest]}
            return {'answer':f'{sid}: {counts["present"]} present, {counts["absent"]} absent, {counts["excused"]} excused, {counts["needs_check"]} pending random checks, {counts["unmarked"]} unmarked.',
                    'source':'checkins LEFT JOIN attendance_sessions','rows':[{'student_id':sid,**counts}]}
    if any(w in q for w in ['quiz','quizzes','grade','score','assessment','كويز','درجات','نتائج','تصحيح']):
        with conn() as db:
            rows=[dict(r) for r in db.execute('''SELECT q.title,q.id AS quiz_id,COUNT(p.id) AS submitted,
             SUM(CASE WHEN p.status='published' THEN 1 ELSE 0 END) AS published
             FROM quizzes q LEFT JOIN papers p ON p.quiz_id=q.id GROUP BY q.id ORDER BY q.id''')]
        return {'answer':'Quiz submission and publication counts from local database.','source':'quizzes LEFT JOIN papers','rows':rows}
    with conn() as db:
        if section_match:
            sec=section_match.group(0).upper()
            rows=[dict(r) for r in db.execute('''SELECT a.id AS session_id,a.topic,a.started_at,
              SUM(CASE WHEN c.status IN ('present','needs_check') THEN 1 ELSE 0 END) AS checked_in,
              SUM(CASE WHEN c.status='absent' THEN 1 ELSE 0 END) AS absent,
              COUNT(c.student_id) AS marked FROM attendance_sessions a LEFT JOIN checkins c ON c.session_id=a.id
              WHERE a.section_id=? GROUP BY a.id ORDER BY a.started_at DESC LIMIT 15''',(sec,))]
            if not rows:return {'answer':f'No sessions found for {sec}.','source':'attendance_sessions','rows':[]}
            return {'answer':f'{sec}: {len(rows)} most recent attendance sessions. Missing marks are not absences.','source':'attendance_sessions + checkins','rows':rows}
        summary=[dict(r) for r in db.execute('''SELECT a.section_id,COUNT(DISTINCT a.id) AS sessions,
              COUNT(c.student_id) AS marked,
              SUM(CASE WHEN c.status IN ('present','needs_check') THEN 1 ELSE 0 END) AS checked_in,
              SUM(CASE WHEN c.status='absent' THEN 1 ELSE 0 END) AS absent,
              SUM(CASE WHEN c.status='excused' THEN 1 ELSE 0 END) AS excused
              FROM attendance_sessions a LEFT JOIN checkins c ON c.session_id=a.id GROUP BY a.section_id ORDER BY a.section_id''')]
    if any(w in q for w in ['attendance','absent','present','session','غاب','غايب','غائب','حضر','حضور','غياب','سكشن','احصائ']):
        return {'answer':'Attendance summary from recorded sessions. Counts exclude unmarked/unknown cases.','source':'attendance_sessions + checkins','rows':summary}
    return {'answer':'I can query actual mock attendance and quiz records. Try: "How many times was ST001 absent?", "Attendance in AI-SEC01", "Compare attendance by section", or "Quiz submissions". I will not invent missing data.',
            'source':'intent_router','rows':[]}

@router.get('/api/workspace/experiments')
def experiments(request:Request):
    staff_required(request)
    s03=json.loads((ROOT/'research/sprint3/results/asag_s03_metrics.json').read_text(encoding='utf-8'))
    s05=json.loads((ROOT/'research/sprint5/results/s05_reproducibility_and_gate.json').read_text(encoding='utf-8'))
    methods=[]
    for name,metrics in s05['method_test_scores'].items():
        methods.append({'method':name,'mae':metrics['mae'],'qwk':metrics['qwk'],'exact':metrics['exact'],'test_n':metrics['n'],'status':'executed on ASAG'})
    methods.sort(key=lambda x:x['mae'])
    model_result=ROOT/'research/sprint4/results/s04_transformer_results.json'
    s06_path=ROOT/'research/sprint6/results/test/test_metrics.json'
    s06=json.loads(s06_path.read_text(encoding='utf-8')) if s06_path.exists() else None
    return {
      'sprint06_ocr_status':s06['status'] if s06 else 'NO_REAL_OCR_RESULTS_YET',
      'sprint06_ocr_result':s06 if s06 and s06.get('model_executed') else None,
      'dataset':s03['dataset'],'frozen_seed':s03['seed'],'test_n':s05['test_n'],
      'methods':methods,'s03_selected':s05['s03_validation_selected_test_scores'],
      'research_gate':s05['research_gate'],
      'transformers_status':'results file present - check provenance' if model_result.exists() else 'NOT RUN - weights unavailable in bundled package',
      'ocr_status':('S06 real held-out IAM test results exist; verify the provenance and metrics file' if s06 and s06.get('model_executed') else 'NOT RE-EVALUATED - requires verified IAM images + independent ground truth'),
      'research_reports':['ASAG Sprint03','Error Analysis Sprint04','Audit Sprint05'],
      'warning':'ASAG is typed, typically longer answers, 0–2 human marks. Not validation for 1–3 word or scanned handwritten quiz responses.'}

@router.get('/api/workspace/experiments/report/{sprint}')
def experiment_report(sprint:int,request:Request):
    staff_required(request)
    files={3:ROOT/'research/sprint3/results/asag_s03_report.html',
           4:ROOT/'research/sprint4/results/s04_error_analysis_report.html',
           5:ROOT/'research/sprint5/results/s05_unified_research_report.html',
           6:ROOT/'docs/MENTRIX_ALL_PHASES_SPRINT06_REPORT_AR.html'}
    path=files.get(sprint)
    if path is None or not path.is_file():raise HTTPException(404,'Unknown report')
    return FileResponse(path,media_type='text/html')

@router.get('/api/workspace/audit')
def audit_history(request:Request):
    staff_required(request)
    from staff_security import role
    if role(request)!='admin':raise HTTPException(403,'Admin-only audit log')
    with conn() as db:
        return {'events':[dict(x) for x in db.execute('SELECT * FROM audit ORDER BY id DESC LIMIT 50')]}

@router.get('/checkin',include_in_schema=False)
def checkin_page():return FileResponse(ROOT/'static/student_checkin.html',headers={'Cache-Control':'no-store'})


def seed_demo_history():
    """Demo-only: deterministic completed sessions, never interpreted as real students."""
    with conn() as db:
        if db.execute('SELECT COUNT(*) FROM attendance_sessions').fetchone()[0]:return
        from datetime import timedelta
        today=datetime.fromtimestamp(utc(),timezone.utc).date()
        for k in range(12,0,-1):
            day=today-timedelta(days=k)
            began=int(datetime(day.year,day.month,day.day,10,0,tzinfo=timezone.utc).timestamp())
            sess=f'DEMO-AT{k:02}'
            db.execute('INSERT INTO attendance_sessions VALUES(?,?,?,?,?,?,?,?)',(sess,'AI-SEC01',f'Demo AI Section {13-k}','Lab 3',began,began+300,began+360,secrets.token_hex(32)))
            for i in range(1,31):
                outcome=(i*7+k*11)%20
                status='present' if outcome<15 else 'absent' if outcome<19 else 'excused'
                db.execute('INSERT INTO checkins VALUES(?,?,?,?,?)',(sess,f'ST{i:03}',status,'synthetic_history',began+120))
        audit(db,'demo_history_seed','all',{'sessions':12,'attendance_marks':360,'synthetic':True})

seed_demo_history()

# ---- Spreadsheet-friendly exports of finalized local mock records ----
def csv_response(rows,columns,filename):
    import csv
    from fastapi.responses import Response as FastResponse
    data=io.StringIO(newline='')
    writer=csv.writer(data)
    writer.writerow(columns)
    for row in rows:
        # Prevent Excel formula injection for untrusted text values.
        writer.writerow([("'"+str(v) if isinstance(v,str) and v[:1] in '=+-@' else v) for v in row])
    return FastResponse(content='\ufeff'+data.getvalue(),media_type='text/csv; charset=utf-8',headers={'Content-Disposition':f'attachment; filename="{filename}"'})

@router.get('/api/workspace/exports/grades.csv')
def grades_csv(request:Request):
    staff_required(request)
    with conn() as db:
        rows=[tuple(r) for r in db.execute('''SELECT p.id,p.quiz_id,p.student_id,g.question_id,g.answer_text,g.final_score,q.max_score,p.published_at
              FROM papers p JOIN grades g ON g.paper_id=p.id JOIN questions q ON q.id=g.question_id
              WHERE p.status='published' ORDER BY p.published_at,p.id,q.position''')]
    return csv_response(rows,['paper_id','quiz_id','student_id','question_id','answer_text','final_score','max_score','published_at'],'mentrix_published_grades.csv')

@router.get('/api/workspace/exports/attendance.csv')
def attendance_csv(request:Request):
    staff_required(request)
    with conn() as db:
        rows=[tuple(r) for r in db.execute('''SELECT s.id,s.section_id,s.topic,st.id,st.name,c.status,c.method,s.closed_at
              FROM attendance_sessions s JOIN students st ON st.section_id=s.section_id
              LEFT JOIN checkins c ON c.session_id=s.id AND c.student_id=st.id
              ORDER BY s.started_at DESC,st.id''')]
    return csv_response(rows,['session_id','section_id','topic','student_id','student_name','status','method','closed_at'],'mentrix_attendance.csv')
