"""Genuine end-to-end tests for the single MENTRIX workspace. No model weights claimed."""
import os, sys
from pathlib import Path
import pytest
import fitz
from fastapi.testclient import TestClient
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
import integrated_workflow as w
from app import app

@pytest.fixture()
def env(tmp_path,monkeypatch):
    monkeypatch.setattr(w,'DB',tmp_path/'workspace.sqlite3')
    monkeypatch.setattr(w,'UPLOADS',tmp_path/'uploads')
    w.UPLOADS.mkdir()
    w.init_db();w.seed_demo_history()
    monkeypatch.setenv('MENTRIX_STAFF_PIN','SecureDemoTA1')
    monkeypatch.setenv('MENTRIX_ADMIN_PIN','SecureAdmin2')
    with TestClient(app) as ta,TestClient(app) as st:
        assert ta.post('/api/auth/login',json={'pin':'SecureDemoTA1'}).status_code==200
        yield ta,st

def test_mock_data_and_access(env):
    ta,st=env
    assert st.get('/api/workspace/dashboard').status_code==401
    d=ta.get('/api/workspace/dashboard').json()['stats']
    assert (d['students'],d['sessions'],d['sections'])==(30,12,2)
    assert st.get('/api/student/session').json()['authenticated'] is False
    assert st.post('/api/student/login',json={'student_id':'ST001','pin':'wrongxx'}).status_code==401
    assert st.post('/api/student/login',json={'student_id':'ST001','pin':'740001'}).status_code==200
    assert st.get('/api/workspace/students').status_code==401
    assert ta.get('/api/workspace/audit').status_code==403

def test_qr_checkin_and_random_check_and_finalize(env):
    ta,st=env
    s=ta.post('/api/workspace/attendance/open',json={'section_id':'AI-SEC01','topic':'Demo section','room':'Lab 3','duration_minutes':5})
    assert s.status_code==200,s.text
    sid=s.json()['session_id']
    qr=ta.get(f'/api/workspace/attendance/{sid}/qr').json()
    assert qr['qr_image'] is None or qr['qr_image'].startswith('data:image/png;base64,')
    assert 'token=' in qr['url']
    token=qr['url'].split('token=')[1]
    assert st.post('/api/student/checkin',json={'session_id':sid,'token':token}).status_code==401
    assert st.post('/api/student/login',json={'student_id':'ST001','pin':'740001'}).status_code==200
    assert st.post('/api/student/checkin',json={'session_id':sid,'token':'incorrect'}).status_code==422
    r=st.post('/api/student/checkin',json={'session_id':sid,'token':token})
    assert r.status_code==200,r.text
    assert r.json()['registered']
    assert st.post('/api/student/checkin',json={'session_id':sid,'token':token}).json()['already_registered']
    sel=ta.post(f'/api/workspace/attendance/{sid}/random-check').json()['selected_students']
    assert sel==['ST001']
    assert ta.post(f'/api/workspace/attendance/{sid}/close').status_code==409
    assert ta.post(f'/api/workspace/attendance/{sid}/mark',json={'student_id':'ST001','status':'present'}).status_code==200
    end=ta.post(f'/api/workspace/attendance/{sid}/close')
    assert end.status_code==200 and end.json()['newly_marked_absent']==29
    reg=ta.get(f'/api/workspace/attendance/{sid}/register').json()['counts']
    assert reg['present']==1 and reg['absent']==29
    assert st.post('/api/student/checkin',json={'session_id':sid,'token':token}).status_code==409

def test_quiz_full_paper_review_and_publish(env):
    ta,_=env
    doc=fitz.open();p=doc.new_page();p.insert_text((70,80),'Q1: B\nQ2: central processing unit\nQ3: 5\nQ4: Supervised uses labels; unsupervised discovers patterns.',fontsize=12)
    pdf=doc.tobytes();doc.close()
    res=ta.post('/api/workspace/papers/upload',data={'quiz_id':'AI-QUIZ01','student_id':'ST001'},files={'file':('answer_sheet.pdf',pdf,'application/pdf')})
    assert res.status_code==200,res.text
    pid=res.json()['paper_id']
    assert 'Q1: B' in res.json()['extracted_text']
    assert ta.post('/api/workspace/papers/publish-batch',json={'paper_ids':[pid]}).status_code==409
    d=ta.post(f'/api/workspace/papers/{pid}/verify-and-grade',json={'corrected_text':res.json()['extracted_text'],'answers':{'Q1':'B','Q2':'central processing unit','Q3':'5','Q4':'Supervised uses labels.'},'verified':True})
    assert d.status_code==200,d.text
    grades={r['question_id']:r for r in d.json()['grades']}
    assert grades['Q1']['status']=='auto_scored'
    assert grades['Q2']['status']=='auto_scored'
    assert grades['Q3']['status']=='auto_scored'
    assert grades['Q4']['status']=='pending_ta'
    assert ta.post('/api/workspace/papers/publish-batch',json={'paper_ids':[pid]}).status_code==409
    rr=ta.post(f'/api/workspace/papers/{pid}/grades/Q4/review',json={'final_score':3,'reviewer':'Demo TA','note':'Rubric-based human decision'})
    assert rr.status_code==200,rr.text
    published=ta.post('/api/workspace/papers/publish-batch',json={'paper_ids':[pid]})
    assert published.status_code==200,published.text
    assert ta.get(f'/api/workspace/papers/{pid}').json()['paper']['status']=='published'
    assert ta.post(f'/api/workspace/papers/{pid}/grades/Q4/review',json={'final_score':5,'reviewer':'TA','note':'retry'}).status_code==409
    assert ta.get(f'/api/workspace/papers/{pid}/original').status_code==200

def test_short_paraphrase_not_automatically_failed(env):
    ta,_=env
    with w.conn() as db:
        q=db.execute('SELECT * FROM questions WHERE id=?',('Q2',)).fetchone()
        assert w.grade_rule(q,'CPU means central processor')[1]=='pending_ta'
        q=db.execute('SELECT * FROM questions WHERE id=?',('Q4',)).fetchone()
        assert w.grade_rule(q,'Great essay with keywords')[1]=='pending_ta'

def test_assistant_and_archive(env):
    ta,_=env
    for question in ['How many times was ST001 absent?','Attendance in AI-SEC01','Quiz submissions']:
        response=ta.post('/api/workspace/assistant/ask',json={'message':question})
        assert response.status_code==200 and response.json()['source']
    ex=ta.get('/api/workspace/experiments')
    assert ex.status_code==200 and ex.json()['test_n']==129
    assert len(ex.json()['methods'])==7
    assert ta.get('/api/workspace/experiments/report/3').status_code==200
