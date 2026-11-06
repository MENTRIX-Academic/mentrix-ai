"""Deterministic SQLite attendance for locally authorized TA. Never infer absent from missing records."""
from __future__ import annotations
import csv, io, re, sqlite3
from contextlib import contextmanager
from datetime import date
from pathlib import Path
from fastapi import APIRouter, HTTPException, UploadFile, File
from pydantic import BaseModel, Field

router=APIRouter(prefix='/api/v1/attendance',tags=['Attendance (local TA)'])
DB=Path(__file__).resolve().parent/'local_private_data'/'mentrix_attendance.sqlite3'
DB.parent.mkdir(parents=True,exist_ok=True)
VALID_STATUS={'present','absent','excused'}
CODE=re.compile(r'^[A-Za-z0-9_-]{2,32}$')
@contextmanager
def connect():
    db=sqlite3.connect(DB,timeout=15)
    db.row_factory=sqlite3.Row
    db.execute('PRAGMA foreign_keys=ON')
    try:
        yield db;db.commit()
    except Exception:
        db.rollback();raise
    finally:db.close()

def initialize():
    with connect() as db:
        db.executescript('''
        CREATE TABLE IF NOT EXISTS students(student_code TEXT PRIMARY KEY, student_name TEXT NOT NULL DEFAULT '', section_code TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS sessions(id INTEGER PRIMARY KEY AUTOINCREMENT, section_code TEXT NOT NULL, session_date TEXT NOT NULL, topic TEXT NOT NULL DEFAULT '', UNIQUE(section_code,session_date));
        CREATE TABLE IF NOT EXISTS attendance(session_id INTEGER NOT NULL REFERENCES sessions(id), student_code TEXT NOT NULL REFERENCES students(student_code),status TEXT NOT NULL CHECK(status IN ('present','absent','excused')), PRIMARY KEY(session_id,student_code));
        ''')
initialize()

def code_ok(s):
    if not CODE.fullmatch(s):raise HTTPException(422,'Codes must be 2–32 letters, numbers, underscore or hyphen')
    return s.upper()

def date_ok(s):
    try: return date.fromisoformat(s).isoformat()
    except ValueError:raise HTTPException(422,'Date format must be YYYY-MM-DD')

class StudentIn(BaseModel):
    student_code:str
    student_name:str=Field(default='',max_length=100)
    section_code:str
class SessionIn(BaseModel):
    section_code:str
    session_date:str
    topic:str=Field(default='',max_length=160)
class AttendanceIn(BaseModel):
    session_id:int=Field(ge=1)
    student_code:str
    status:str

@router.post('/students')
def add_student(row:StudentIn):
    sc=code_ok(row.student_code); sec=code_ok(row.section_code)
    with connect() as db:
        db.execute('INSERT INTO students(student_code,student_name,section_code) VALUES(?,?,?) ON CONFLICT(student_code) DO UPDATE SET student_name=excluded.student_name,section_code=excluded.section_code',(sc,row.student_name.strip(),sec))
    return {'student_code':sc,'section_code':sec,'saved':True}

@router.get('/students')
def students():
    with connect() as db:
        return {'students':[dict(r) for r in db.execute('SELECT * FROM students ORDER BY section_code,student_code LIMIT 1000')]}

@router.post('/sessions')
def add_session(row:SessionIn):
    sec=code_ok(row.section_code); day=date_ok(row.session_date)
    with connect() as db:
        db.execute('INSERT INTO sessions(section_code,session_date,topic) VALUES(?,?,?) ON CONFLICT(section_code,session_date) DO UPDATE SET topic=excluded.topic',(sec,day,row.topic.strip()))
        saved=db.execute('SELECT * FROM sessions WHERE section_code=? AND session_date=?',(sec,day)).fetchone()
    return dict(saved)

@router.get('/sessions')
def sessions():
    with connect() as db:
        return {'sessions':[dict(r) for r in db.execute('SELECT * FROM sessions ORDER BY session_date DESC,id DESC LIMIT 200')]}

@router.post('/mark')
def mark_attendance(row:AttendanceIn):
    sc=code_ok(row.student_code); status=row.status.lower()
    if status not in VALID_STATUS:raise HTTPException(422,'Use present, absent or excused')
    with connect() as db:
        s=db.execute('SELECT * FROM sessions WHERE id=?',(row.session_id,)).fetchone()
        student=db.execute('SELECT * FROM students WHERE student_code=?',(sc,)).fetchone()
        if not s or not student:raise HTTPException(404,'Student/session not found')
        if student['section_code']!=s['section_code']:raise HTTPException(409,'Student section does not match session section')
        db.execute('INSERT INTO attendance(session_id,student_code,status) VALUES(?,?,?) ON CONFLICT(session_id,student_code) DO UPDATE SET status=excluded.status',(row.session_id,sc,status))
    return {'student_code':sc,'session_id':row.session_id,'status':status}

@router.get('/register/{session_id}')
def register(session_id:int):
    with connect() as db:
        ses=db.execute('SELECT * FROM sessions WHERE id=?',(session_id,)).fetchone()
        if not ses:raise HTTPException(404,'Session not found')
        rows=db.execute('''SELECT s.student_code,s.student_name,s.section_code,a.status FROM students s LEFT JOIN attendance a ON a.student_code=s.student_code AND a.session_id=? WHERE s.section_code=? ORDER BY s.student_code''',(session_id,ses['section_code'])).fetchall()
    return {'session':dict(ses),'register':[dict(r) for r in rows], 'unmarked_meaning':'unknown — not absent'}

@router.get('/student/{student_code}')
def student_report(student_code:str):
    sc=code_ok(student_code)
    with connect() as db:
        st=db.execute('SELECT * FROM students WHERE student_code=?',(sc,)).fetchone()
        if not st:raise HTTPException(404,'Student not found')
        items=db.execute('''SELECT sess.id as session_id,sess.session_date,sess.section_code,sess.topic,a.status FROM sessions sess LEFT JOIN attendance a ON a.session_id=sess.id AND a.student_code=? WHERE sess.section_code=? ORDER BY sess.session_date DESC''',(sc,st['section_code'])).fetchall()
    entries=[dict(x) for x in items]
    return {'student':dict(st),'sessions':entries,'counts':{'present':sum(x['status']=='present' for x in entries), 'absent':sum(x['status']=='absent' for x in entries),'excused':sum(x['status']=='excused' for x in entries),'not_recorded':sum(x['status'] is None for x in entries)}, 'count_policy':'Only explicitly marked absent is counted as absence.'}

@router.get('/summary')
def summary():
    with connect() as db:
        students=db.execute('SELECT COUNT(*) FROM students').fetchone()[0]
        sessions=db.execute('SELECT COUNT(*) FROM sessions').fetchone()[0]
        absent=db.execute("SELECT COUNT(*) FROM attendance WHERE status='absent'").fetchone()[0]
        present=db.execute("SELECT COUNT(*) FROM attendance WHERE status='present'").fetchone()[0]
    return {'students':students,'sessions':sessions,'absences_recorded':absent,'present_recorded':present}

@router.post('/import-students')
async def import_students(file:UploadFile=File(...)):
    raw=await file.read(400_001)
    if len(raw)>400_000:raise HTTPException(413,'Max CSV 400 KB')
    try:
        text=raw.decode('utf-8-sig');rows=list(csv.DictReader(io.StringIO(text)))
        if not rows or len(rows)>1000:raise ValueError('CSV needs 1–1000 rows')
        processed=[]
        for row in rows:
            sc=code_ok((row.get('student_code') or '').strip());sec=code_ok((row.get('section_code') or '').strip())
            name=(row.get('student_name') or '').strip()
            if len(name)>100:raise ValueError('Name too long')
            processed.append((sc,name,sec))
        with connect() as db:
            for row in processed:
                db.execute('INSERT INTO students VALUES(?,?,?) ON CONFLICT(student_code) DO UPDATE SET student_name=excluded.student_name, section_code=excluded.section_code',row)
        return {'imported':len(processed)}
    except (UnicodeError, csv.Error,ValueError,TypeError,KeyError) as e:
        raise HTTPException(422,'CSV format: student_code,student_name,section_code. '+str(e)[:100]) from e

@router.post('/import-attendance')
async def import_attendance(file:UploadFile=File(...)):
    raw=await file.read(500_001)
    if len(raw)>500_000:raise HTTPException(413,'Max CSV 500 KB')
    try:
        rows=list(csv.DictReader(io.StringIO(raw.decode('utf-8-sig'))))
        if not rows or len(rows)>2000:raise ValueError('CSV needs 1–2000 rows')
        clean=[]
        for r in rows:
            day=date_ok((r.get('session_date') or '').strip())
            sec=code_ok((r.get('section_code') or '').strip())
            st=code_ok((r.get('student_code') or '').strip())
            status=(r.get('status') or '').strip().lower()
            if status not in VALID_STATUS:raise ValueError('Invalid attendance status: '+status)
            clean.append((day,sec,st,status))
        with connect() as db:
            for day,sec,st,status in clean:
                student=db.execute('SELECT section_code FROM students WHERE student_code=?',(st,)).fetchone()
                if not student or student['section_code']!=sec:raise ValueError('Unknown student/section mismatch '+st)
            for day,sec,st,status in clean:
                db.execute('INSERT OR IGNORE INTO sessions(section_code,session_date) VALUES(?,?)',(sec,day))
                sess=db.execute('SELECT id FROM sessions WHERE section_code=? AND session_date=?',(sec,day)).fetchone()
                db.execute('INSERT INTO attendance VALUES(?,?,?) ON CONFLICT(session_id,student_code) DO UPDATE SET status=excluded.status',(sess['id'],st,status))
        return {'imported':len(clean),'note':'Missing rows remain unknown, never inferred absent.'}
    except (UnicodeError, csv.Error,ValueError,TypeError,KeyError) as e:
        raise HTTPException(422,'CSV format: session_date,section_code,student_code,status. '+str(e)[:100]) from e

@router.delete('/mark/{session_id}/{student_code}')
def clear_mark(session_id:int,student_code:str):
    sc=code_ok(student_code)
    with connect() as db:
        db.execute('DELETE FROM attendance WHERE session_id=? AND student_code=?',(session_id,sc))
    return {'student_code':sc,'session_id':session_id,'status':None,'note':'Unmarked means unknown, not absent'}
