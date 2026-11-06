import os
os.environ['MENTRIX_STAFF_PIN']='test12345'
"""Reproducible tests; model inference mocked, no trained OCR accuracy asserted."""
from io import BytesIO
from pathlib import Path
import tempfile, unittest
from unittest.mock import patch
from PIL import Image, ImageDraw
from fastapi.testclient import TestClient
from app import app
import ocr_integration as ocr
from ocr_quality import enhanced_line, suggest_boundaries, line_quality


def picture():
    img=Image.new('RGB',(620,280),'white')
    dr=ImageDraw.Draw(img)
    dr.rectangle((20,32,500,45),fill='black')
    dr.rectangle((20,172,500,185),fill='black')
    b=BytesIO();img.save(b,format='PNG');return b.getvalue()

class V3Tests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.old=(ocr.PRIVATE,ocr.DB)
        ocr.PRIVATE=Path(self.tmp.name);ocr.DB=ocr.PRIVATE/'test.db';ocr.init_db()
        self.c=TestClient(app); self.c.post('/api/auth/login',json={'pin':'test12345'})
    def tearDown(self):
        self.c.close();ocr.PRIVATE,ocr.DB=self.old;self.tmp.cleanup()
    def test_suggest_and_compare_and_sqlite(self):
        result=self.c.post('/api/v1/ocr/suggest-lines',files={'image':('test.png',picture(),'image/png')})
        self.assertEqual(result.status_code,200,result.text)
        bounds=result.json()['boundaries'];self.assertEqual(bounds[0],0);self.assertEqual(bounds[-1],280)
        self.assertGreaterEqual(len(bounds),3)
        with patch.object(ocr,'run_trocr',side_effect=[['Signal one','Wave two'],['Signal 1','Wave 2']]) as mock:
            response=self.c.post('/api/v1/ocr/transcribe',data={'question_id':'E01','writer_code':'W123',
                'boundaries':'[0,120,280]','comparison_mode':'compare'},files={'image':('test.png',picture(),'image/png')})
        self.assertEqual(response.status_code,201,response.text)
        self.assertEqual(mock.call_count,2)
        d=response.json();self.assertEqual(len(d['candidates']),2)
        self.assertEqual(d['candidates'][0]['autocontrast'],'Signal 1')
        self.assertEqual(d['ocr_prediction'],'Signal one\nWave two')
        self.assertEqual(len(d['quality']),2)
        loaded=self.c.get('/api/v1/ocr/reviews/'+d['id']).json()
        self.assertEqual(loaded['candidates'],d['candidates'])
        self.assertIsNone(loaded['final_score'])
        self.assertEqual(self.c.post('/api/v1/ocr/reviews/'+d['id']+'/approve',json={
            'reviewer':'TA','final_score':4}).status_code,409)
    def test_no_model_needed_for_chatbot(self):
        r=self.c.post('/api/v1/chatbot/ask',json={'message':'يعني ايه CER و WER؟'})
        self.assertEqual(r.status_code,200)
        self.assertIn('WER',r.json()['answer']);self.assertTrue(r.json()['sources'])
        r=self.c.post('/api/v1/chatbot/ask',json={'message':'هات بيانات ودرجات طالب'})
        self.assertEqual(r.status_code,200);self.assertFalse(r.json()['grounded'])
        self.assertNotIn('correct_letter',str(r.json()))
        self.assertEqual(self.c.post('/api/v1/chatbot/ask',json={'message':'hi','engine':'external_api'}).status_code,422)
        self.assertEqual(self.c.get('/chatbot',follow_redirects=False).status_code,307)
    def test_ollama_requires_server_not_silent_fake(self):
        with patch('chatbot_integration.ollama_answer',side_effect=OSError('not installed')):
            response=self.c.post('/api/v1/chatbot/ask',json={'message':'اشرح sine wave','engine':'ollama'})
        self.assertEqual(response.status_code,503)
    def test_quality_routines_preserve_original(self):
        img=Image.new('RGB',(100,60),(250,248,247))
        self.assertEqual(img.getpixel((0,0)),(250,248,247))
        self.assertEqual(enhanced_line(img).mode,'RGB')
        self.assertIn('flags',line_quality(img))
        self.assertEqual(img.getpixel((0,0)),(250,248,247))

if __name__=='__main__':unittest.main()
