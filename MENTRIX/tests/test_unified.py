"""Staff auth + deterministic attendance + safe grading + mock OCR tests (no real model accuracy claim)."""
import io,os,tempfile,unittest
from pathlib import Path
from unittest.mock import patch
os.environ['MENTRIX_STAFF_PIN']='test12345'
from PIL import Image
from fastapi.testclient import TestClient
from app import app
import attendance_integration as att
import ocr_integration as ocr

class UnifiedTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.old_att=att.DB;self.old_private=ocr.PRIVATE;self.old_ocr=ocr.DB
        att.DB=Path(self.temp.name)/'attendance.sqlite3';att.initialize()
        ocr.PRIVATE=Path(self.temp.name);ocr.DB=Path(self.temp.name)/'ocr.sqlite3';ocr.init_db()
        self.c=TestClient(app)
    def tearDown(self):
        self.c.close();att.DB=self.old_att;ocr.PRIVATE=self.old_private;ocr.DB=self.old_ocr
        self.temp.cleanup()
    def login(self):
        r=self.c.post('/api/auth/login',json={'pin':'test12345'})
        self.assertEqual(r.status_code,200,r.text)
    def test_protected_records_and_login(self):
        self.assertEqual(self.c.get('/api/v1/attendance/students').status_code,401)
        self.assertEqual(self.c.get('/api/v1/ocr/reviews').status_code,401)
        self.assertEqual(self.c.post('/api/auth/login',json={'pin':'wrongpin'}).status_code,401)
        self.login()
        self.assertEqual(self.c.get('/api/v1/attendance/students').status_code,200)
        self.c.post('/api/auth/logout')
        self.assertEqual(self.c.get('/api/v1/attendance/students').status_code,401)
    def test_attendance_chat_only_recorded(self):
        self.login()
        self.assertEqual(self.c.post('/api/v1/attendance/students',json={'student_code':'ST001','student_name':'Sample','section_code':'SEC-A'}).status_code,200)
        self.c.post('/api/v1/attendance/students',json={'student_code':'ST002','section_code':'SEC-A'})
        sid=self.c.post('/api/v1/attendance/sessions',json={'section_code':'SEC-A','session_date':'2026-11-03'}).json()['id']
        # Nobody absent until explicitly marked.
        r=self.c.post('/api/v1/chatbot/ask',json={'message':'ST002 غاب كام مرة؟'})
        self.assertIn('غاب 0 مرة',r.json()['answer'])
        self.assertIn('لسه 1',r.json()['answer'])
        r=self.c.post('/api/v1/attendance/mark',json={'session_id':sid,'student_code':'ST002','status':'absent'})
        self.assertEqual(r.status_code,200,r.text)
        r=self.c.post('/api/v1/chatbot/ask',json={'message':'ST002 غاب كام مرة؟','engine':'ollama'})
        self.assertEqual(r.status_code,200);self.assertEqual(r.json()['engine'],'database')
        self.assertIn('غاب 1 مرة',r.json()['answer'])
        self.assertIn('ST002',self.c.post('/api/v1/chatbot/ask',json={'message':'مين غاب في SEC-A؟'}).json()['answer'])
        self.assertIn('لم يتم تسجيل',self.c.post('/api/v1/chatbot/ask',json={'message':'ST001 حضر يوم 2026-11-03؟'}).json()['answer'])
        reg=self.c.get(f'/api/v1/attendance/register/{sid}').json()['register']
        self.assertEqual(sum(x['status'] is None for x in reg),1)
    def test_csv_import_and_bad_data_not_applied(self):
        self.login()
        raw=b'student_code,student_name,section_code\nST001,Test,SEC-A\nST002,Test 2,SEC-A\n'
        r=self.c.post('/api/v1/attendance/import-students',files={'file':('students.csv',raw,'text/csv')})
        self.assertEqual(r.status_code,200,r.text)
        bad=b'session_date,section_code,student_code,status\n2026-11-03,SEC-A,ST001,absent\n2026-11-03,SEC-A,ST999,present\n'
        self.assertEqual(self.c.post('/api/v1/attendance/import-attendance',files={'file':('bad.csv',bad,'text/csv')}).status_code,422)
        self.assertEqual(self.c.get('/api/v1/attendance/summary').json()['sessions'],0)
        good=b'session_date,section_code,student_code,status\n2026-11-03,SEC-A,ST001,absent\n'
        r=self.c.post('/api/v1/attendance/import-attendance',files={'file':('attendance.csv',good,'text/csv')})
        self.assertEqual(r.status_code,200,r.text)
        self.assertEqual(self.c.get('/api/v1/attendance/summary').json()['absences_recorded'],1)
        self.assertEqual(self.c.get('/api/v1/attendance/student/ST002').json()['counts']['not_recorded'],1)
    def test_grading_policy_automatic_and_manual(self):
        self.login()
        r=self.c.post('/api/v1/grading/evaluate',json={'answers':[
            {'question_id':'MC01','answer':'B'},
            {'question_id':'SA02','answer':'freq'},
            {'question_id':'MA03','answer':'2 Hz'},
            {'question_id':'E01','answer':'Continuous signals ...'}]})
        self.assertEqual(r.status_code,201,r.text)
        rows={x['question_id']:x for x in r.json()['results']}
        self.assertEqual(rows['MC01']['approval_status'],'auto_scored')
        self.assertEqual(rows['MA03']['approval_status'],'auto_scored')
        self.assertEqual(rows['SA02']['approval_status'],'pending_ta')
        self.assertEqual(rows['E01']['approval_status'],'pending_ta')
        self.assertIsNone(rows['E01']['final_score'])
        aid=r.json()['attempt_id']
        res=self.c.post(f'/api/v1/grading/attempts/{aid}/items/MC01/approve',json={'reviewer':'TA override','final_score':0,'comment':'Audited'})
        self.assertEqual(res.status_code,200)
        self.assertEqual(res.json()['final_score'],0)
    def test_ocr_padded_mode_and_verified_auto(self):
        self.login()
        image=io.BytesIO();Image.new('RGB',(400,120),'white').save(image,'PNG')
        with patch.object(ocr,'run_trocr',side_effect=[['B'],['B']]) as runner:
            r=self.c.post('/api/v1/ocr/transcribe',data={'question_id':'MC01','writer_code':'W010','boundaries':'[0,120]','comparison_mode':'padded_compare'},files={'image':('line.png',image.getvalue(),'image/png')})
        self.assertEqual(r.status_code,201,r.text)
        self.assertEqual(runner.call_count,2)
        self.assertEqual(r.json()['candidates'][0]['padded'],'B')
        self.assertIsNone(r.json()['final_score'])
        review_id=r.json()['id']
        corrected=self.c.post(f'/api/v1/ocr/reviews/{review_id}/verify',json={'corrected_text':'B','verified':True})
        self.assertEqual(corrected.status_code,200,corrected.text)
        self.assertEqual(corrected.json()['status'],'auto_scored')
        self.assertEqual(corrected.json()['final_score'],1)

if __name__=='__main__':unittest.main()
