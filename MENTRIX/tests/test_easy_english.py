import os,unittest
from pathlib import Path
from fastapi.testclient import TestClient
os.environ['MENTRIX_STAFF_PIN']='test12345'
from app import app
import attendance_integration as att
import tempfile
class EasyEnglishTests(unittest.TestCase):
    def test_english_interface(self):
        text=(Path(__file__).resolve().parents[1]/'static/index.html').read_text(encoding='utf-8')
        self.assertIn('lang="en"',text)
        self.assertIn('Attendance',text)
        self.assertIn('Quiz Grading',text)
        self.assertNotIn('الطلاب والحضور',text)
        self.assertIn('data-view="assistant"',text)
    def test_health_and_english_chat(self):
        with tempfile.TemporaryDirectory() as td:
            old=att.DB
            try:
                att.DB=Path(td)/'att.sqlite3';att.initialize()
                c=TestClient(app)
                assert c.post('/api/auth/login',json={'pin':'test12345'}).status_code==200
                assert c.post('/api/v1/attendance/students',json={'student_code':'ST002','section_code':'SEC-A'}).status_code==200
                sid=c.post('/api/v1/attendance/sessions',json={'section_code':'SEC-A','session_date':'2026-11-03'}).json()['id']
                r=c.post('/api/v1/chatbot/ask',json={'message':'How many times was ST002 absent?'})
                self.assertEqual(r.status_code,200)
                self.assertIn('0 recorded absence',r.json()['answer'])
                self.assertIn('1 session(s) without a mark',r.json()['answer'])
                c.post('/api/v1/attendance/mark',json={'session_id':sid,'student_code':'ST002','status':'absent'})
                r=c.post('/api/v1/chatbot/ask',json={'message':'How many times was ST002 absent?'})
                self.assertIn('1 recorded absence',r.json()['answer'])
                self.assertEqual(c.get('/health').json()['status'],'ok')
                c.close()
            finally:att.DB=old
if __name__=='__main__':unittest.main()
