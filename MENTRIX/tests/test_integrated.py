import os
os.environ['MENTRIX_STAFF_PIN']='test12345'
import sys,unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from adapter import QUESTIONS, public_quiz, grade
from fastapi.testclient import TestClient
from app import app,ATTEMPTS

class EngineTests(unittest.TestCase):
    def test_real_bank_loaded(self):
        self.assertIn('MC01', QUESTIONS)
        self.assertIn('SA02', QUESTIONS)
        self.assertIn('MA03', QUESTIONS)
        self.assertIn('E01', QUESTIONS)
    def test_no_keys_exposed(self):
        self.assertNotIn('correct_letter',str(public_quiz(full=True)))
        self.assertNotIn('canonical_expression',str(public_quiz(full=True)))
    def test_mcq_v2(self):
        self.assertEqual(grade(QUESTIONS['MC01'],'Answer: B')['decision'],'correct')
    def test_short_unknown_v2_reviews(self):
        self.assertEqual(grade(QUESTIONS['SA02'],'freq')['decision'],'needs_review')
        self.assertIsNone(grade(QUESTIONS['SA02'],'freq')['proposed_score'])
    def test_math_v2(self):
        self.assertEqual(grade(QUESTIONS['MA03'],'2 Hz')['decision'],'correct')
    def test_essay_not_claimed(self):
        self.assertEqual(grade(QUESTIONS['E01'],'An essay')['decision'],'needs_review')
    def test_v1_v2_comparison(self):
        self.assertEqual(grade(QUESTIONS['SA02'],'freq','v1')['decision'],'incorrect')
        self.assertEqual(grade(QUESTIONS['SA02'],'freq','v2')['decision'],'needs_review')
class ApiTests(unittest.TestCase):
    def setUp(self):ATTEMPTS.clear();self.c=TestClient(app); self.c.post('/api/auth/login',json={'pin':'test12345'})
    def test_research_route(self):
        r=self.c.get('/research')
        self.assertIn(r.status_code,(200,307))
    def test_roadmap_route(self):
        r=self.c.get('/roadmap')
        self.assertEqual(r.status_code,404)
    def test_health(self):
        self.assertEqual(self.c.get('/health').json()['ocr'],True)  # OCR router intentionally added
    def test_quiz_and_full(self):
        self.assertEqual(len(self.c.get('/api/v1/demo/quiz').json()['questions']),4)
        self.assertEqual(len(self.c.get('/api/v1/demo/quiz?all=true').json()['questions']),22)
    def test_grade_flow(self):
        p=self.c.post('/api/v1/demo/grade',json={'answers':[{'question_id':'MC01','answer':'B'},{'question_id':'SA02','answer':'freq'}]})
        self.assertEqual(p.status_code,201)
        res=p.json();self.assertEqual(res['results'][0]['decision'],'correct')
        self.assertEqual(res['results'][1]['decision'],'needs_review')
        self.assertIsNone(res['results'][1]['proposed_score'])
        aid=res['attempt_id']
        approve=self.c.post(f'/api/v1/demo/attempts/{aid}/items/MC01/approve',json={'reviewer':'Demo TA','final_score':1})
        self.assertEqual(approve.status_code,200)
        self.assertEqual(self.c.post(f'/api/v1/demo/attempts/{aid}/items/MC01/approve',json={'reviewer':'Demo TA','final_score':1}).status_code,409)
    def test_compare(self):
        p=self.c.post('/api/v1/demo/compare',json={'question_id':'SA02','answer':'freq'})
        self.assertEqual(p.status_code,200)
        self.assertEqual(p.json()['comparisons']['v2']['decision'],'needs_review')
    def test_duplicate(self):
        p=self.c.post('/api/v1/demo/grade',json={'answers':[{'question_id':'MC01','answer':'B'},{'question_id':'MC01','answer':'A'}]})
        self.assertEqual(p.status_code,422)
    def test_approval_bounds(self):
        p=self.c.post('/api/v1/demo/grade',json={'answers':[{'question_id':'E01','answer':'x'}]})
        aid=p.json()['attempt_id']
        p=self.c.post(f'/api/v1/demo/attempts/{aid}/items/E01/approve',json={'reviewer':'Demo TA','final_score':100})
        self.assertEqual(p.status_code,422)

if __name__=='__main__':unittest.main()
