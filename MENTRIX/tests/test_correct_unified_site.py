import os, unittest
from pathlib import Path
from fastapi.testclient import TestClient
os.environ['MENTRIX_STAFF_PIN']='samplepass22'
from app import app, BUILD_ID
BASE=Path(__file__).resolve().parents[1]
class CorrectWebsiteTests(unittest.TestCase):
 def test_home_is_new_and_not_old(self):
  c=TestClient(app);r=c.get('/');self.assertEqual(r.status_code,200);self.assertEqual(r.headers['X-MENTRIX-Build'],BUILD_ID)
  self.assertIn(b'AI TEACHING ASSISTANT',r.content);self.assertIn(b'AI Experiments',r.content);self.assertIn(b'Quiz Grading',r.content)
  self.assertNotIn(b'Live grading demo',r.content);self.assertNotIn(b'AI work roadmap',r.content);self.assertNotIn(b'Original V2 Lab',r.content)
  c.close()
 def test_signin_gates_questions(self):
  with TestClient(app) as c:
   self.assertEqual(c.get('/api/v1/grading/questions').status_code,401)
   self.assertEqual(c.get('/version').json()['build'],BUILD_ID)
   self.assertEqual(c.post('/api/auth/login',json={'pin':os.environ['MENTRIX_STAFF_PIN']}).status_code,200)
   self.assertEqual(c.get('/api/v1/grading/questions?all=true').status_code,200)
 def test_no_auto_legacy_demo(self):
  js=(BASE/'static'/'app.js').read_text(encoding='utf-8')
  self.assertIn('mentrix:authenticated',js)
  self.assertNotIn('Unable to load demo quiz',js)
  html=(BASE/'static'/'legacy_index.html').read_text(encoding='utf-8')
  self.assertNotIn('id="resetBtn"',html)
  self.assertIn('Check one answer',html)
if __name__=='__main__':unittest.main()
