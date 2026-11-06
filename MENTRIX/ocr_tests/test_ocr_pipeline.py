import os
os.environ['MENTRIX_STAFF_PIN']='test12345'
"""Offline route tests. OCR prediction is mocked; no claim about trained accuracy."""
import io
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image
from fastapi.testclient import TestClient
import ocr_integration as module
from app import app


def picture():
    b = io.BytesIO()
    Image.new("RGB", (220, 100), "white").save(b, "PNG")
    return b.getvalue()


class EndToEndPilotTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory()
        self.root=Path(self.tmp.name)
        self.old_db=module.DB
        self.old_private=module.PRIVATE
        module.PRIVATE=self.root
        module.DB=self.root/"pilot.sqlite3"
        module.init_db()
        self.client=TestClient(app); self.client.post('/api/auth/login',json={'pin':'test12345'})

    def tearDown(self):
        self.client.close()
        module.DB=self.old_db
        module.PRIVATE=self.old_private
        self.tmp.cleanup()

    def upload(self,q='E01',bound='[0,50,100]'):
        with patch.object(module,'run_trocr',side_effect=lambda lines: ['When viewed as a function' if i==0 else 'of time a continuous signal' for i in range(len(lines))]):
            return self.client.post('/api/v1/ocr/transcribe',data={
                'question_id':q,'writer_code':'W008','boundaries':bound},
                files={'image':('handwriting.png',picture(),'image/png')})

    def test_essay_image_ocr_verify_ta_sqlite(self):
        response=self.upload()
        self.assertEqual(response.status_code,201,response.text)
        d=response.json()
        self.assertEqual(d['line_count'],2)
        self.assertIn('When viewed',d['ocr_prediction'])
        identifier=d['id']
        self.assertEqual(self.client.get('/api/v1/ocr/reviews/'+identifier+'/image').status_code,200)
        self.assertEqual(self.client.post(f'/api/v1/ocr/reviews/{identifier}/approve',json={'reviewer':'TA 1','final_score':4}).status_code,409)
        result=self.client.post(f'/api/v1/ocr/reviews/{identifier}/verify',json={
            'corrected_text':'A continuous signal has values at every time; discrete at specific times.',
            'verified':True})
        self.assertEqual(result.status_code,200,result.text)
        self.assertEqual(result.json()['decision'],'needs_review')
        self.assertIsNone(result.json()['proposed_score'])
        self.assertIsNone(result.json()['final_score'])
        bad=self.client.post(f'/api/v1/ocr/reviews/{identifier}/approve',json={'reviewer':'TA 1','final_score':100})
        self.assertEqual(bad.status_code,422)
        result=self.client.post(f'/api/v1/ocr/reviews/{identifier}/approve',json={
            'reviewer':'TA 1','final_score':4,'comment':'Checked against rubric.'})
        self.assertEqual(result.status_code,200,result.text)
        self.assertEqual(result.json()['final_score'],4)
        self.assertEqual(result.json()['status'],'approved')
        self.assertEqual(self.client.post(f'/api/v1/ocr/reviews/{identifier}/approve',json={'reviewer':'TA 1','final_score':3}).status_code,409)
        self.assertEqual(self.client.get('/api/v1/ocr/reviews').json()['reviews'][0]['final_score'],4)
        with module.connection() as db:
            count=db.execute('SELECT COUNT(*) FROM ocr_reviews').fetchone()[0]
        self.assertEqual(count,1)

    def test_rule_based_mcq_only_after_verified_transcription(self):
        resp=self.upload(q='MC01',bound='[0,100]')
        self.assertEqual(resp.status_code,201,resp.text)
        id=resp.json()['id']
        r=self.client.post(f'/api/v1/ocr/reviews/{id}/verify',json={'corrected_text':'B','verified':True})
        self.assertEqual(r.status_code,200,r.text)
        self.assertIsNotNone(r.json()['proposed_score'])
        self.assertEqual(r.json()['final_score'],1)

    def test_validate_bounds_and_ids(self):
        self.assertEqual(self.upload(bound='[0,60,50,100]').status_code,422)
        self.assertEqual(self.upload(q='E99').status_code,422)
        self.assertEqual(self.upload(bound='[0,35,100]').status_code,201)

    def test_routes(self):
        self.assertIn(self.client.get('/ocr',follow_redirects=False).status_code,(302,307))
        self.assertTrue(self.client.get('/api/v1/ocr/config').json()['persists_local_sqlite'])
        self.assertEqual(self.client.get('/').status_code,200)
        self.assertEqual(self.client.get('/api/v1/demo/quiz').status_code,200)

if __name__=='__main__': unittest.main()
