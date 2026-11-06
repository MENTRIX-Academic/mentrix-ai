"""Sprint 07: engineering tests for image layout, staff image review and reruns.

NO handwriting benchmark is claimed: the text here is synthetic / OCR stubbed.
"""
import io
import json
from pathlib import Path

import pytest
from PIL import Image, ImageDraw, ImageFont
from research.sprint6.handwriting_layout import smart_line_candidates
from research.sprint6.full_sheet import transcribe_full_sheet, line_candidates


def sample_ruled_page(rotation=0):
    img=Image.new('RGB',(900,650),'white')
    draw=ImageDraw.Draw(img)
    font=None
    for path in ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',
                 'C:/Windows/Fonts/arial.ttf', 'DejaVuSans.ttf'):
        try:
            font=ImageFont.truetype(path,32)
            break
        except (OSError,ValueError):pass
    if font is None:
        try:font=ImageFont.load_default(size=32)
        except TypeError:font=ImageFont.load_default()
    for i,text in enumerate(('Q1: answer one','Q2: another answer',
                              'Q3: one more answer','Q4: final line')):
        y=70+i*130
        draw.line((5,y+45,895,y+45),fill=(120,165,210),width=2)
        draw.text((60,y),text,fill=(15,20,25),font=font)
    if rotation:img=img.rotate(rotation,resample=Image.Resampling.BICUBIC,
                               expand=False,fillcolor=(255,255,255))
    data=io.BytesIO();img.save(data,format='PNG')
    return data.getvalue()


@pytest.mark.parametrize('degrees',[0,2.5,-3.5,5])
def test_smart_detection_with_skew_and_ruled_lines(degrees):
    with Image.open(io.BytesIO(sample_ruled_page(degrees))) as img:
        rows,meta=smart_line_candidates(img)
    assert len(rows)==4, (degrees,meta,[r.bbox for r in rows])
    assert [r.bbox[1] for r in rows]==sorted(r.bbox[1] for r in rows)
    assert all(r.image.width>150 and r.image.height>20 for r in rows)
    assert abs(meta['angle_degrees']+degrees)<=1.5
    assert meta['requires_review']


def test_blank_page_returns_zero_lines_no_hallucination():
    img=Image.new('RGB',(850,1000),'white')
    rows,meta=smart_line_candidates(img)
    assert rows==[]
    assert meta['reason']=='no_stable_ink'
    assert line_candidates(img)[0]==[]


def test_explicit_legacy_mode_still_supported():
    with Image.open(io.BytesIO(sample_ruled_page())) as img:
        rows,meta=line_candidates(img,'legacy')
    assert len(rows)>=4 and meta['method']=='legacy_row_projection'


def test_ocr_second_pass_is_labeled_and_stays_unverified():
    sequence=iter(['','Q1: example','Q2: note','Q3: alpha','Q4: bravo'])
    draft=transcribe_full_sheet(sample_ruled_page(),'scan.png',lambda im:next(sequence),
                                valid_question_ids=['Q1','Q2','Q3','Q4'],retry_unclear=True)
    assert draft['extra_pass_attempts']==1
    assert draft['lines'][0]['first_pass_text']==''
    assert draft['lines'][0]['alternatives'][0]['text']=='Q1: example'
    assert draft['question_answers']['Q1']=='example'
    assert draft['transcription_verified'] is False
    assert draft['grading_performed'] is False


def test_api_visual_review_images_and_manual_box_rerun(tmp_path,monkeypatch):
    from fastapi.testclient import TestClient
    import integrated_workflow as iw
    import handwriting_routes as hw
    import app
    monkeypatch.setattr(iw,'DB',tmp_path/'test.sqlite3')
    monkeypatch.setattr(iw,'UPLOADS',tmp_path/'uploads')
    iw.UPLOADS.mkdir()
    monkeypatch.setattr(hw,'UPLOADS',iw.UPLOADS)
    monkeypatch.setenv('MENTRIX_STAFF_PIN','testing-secret-123')
    iw.init_db()
    img=sample_ruled_page()
    with TestClient(app.app) as client:
        assert client.post('/api/auth/login',json={'pin':'testing-secret-123'}).status_code==200
        res=client.post('/api/workspace/papers/upload',
           data={'quiz_id':'AI-QUIZ01','student_id':'ST001'},
           files={'file':('photo.png',img,'image/png')})
        assert res.status_code==200,res.text
        pid=res.json()['paper_id']
        outputs=iter(['Q1: one','Q2: two','Q3: three','Q4: four'])
        monkeypatch.setattr(hw,'get_recognizer',lambda name:lambda crop:next(outputs))
        r=client.post(f'/api/workspace/papers/{pid}/handwriting-draft',
                      json={'line_detection':'smart','pipeline':'E01_base_rgb'})
        assert r.status_code==200,r.text
        draft=r.json()
        assert draft['line_detection']=='smart'
        assert draft['question_coverage']['matched']==4
        assert len(draft['lines'])==4
        assert len(draft['page_image_urls'])==1
        assert client.get(draft['page_image_urls'][0]).content[:4]==b'\x89PNG'
        assert client.get(draft['lines'][0]['crop_url']).content[:4]==b'\x89PNG'
        denied=client.get(f'/api/workspace/papers/{pid}/handwriting-line/100')
        assert denied.status_code==404
        saved=client.get(f'/api/workspace/papers/{pid}/handwriting-draft').json()
        assert saved['lines'][0]['crop_url']==draft['lines'][0]['crop_url']
        # Second run: selected rectangle supplied in original-page coordinates.
        monkeypatch.setattr(hw,'get_recognizer',lambda name:lambda crop:'my answer')
        manual=[{'question_id':'Q1','page':0,'x0':40,'y0':40,'x1':500,'y1':125}]
        rr=client.post(f'/api/workspace/papers/{pid}/handwriting-draft',json={
            'line_detection':'smart','regions':manual})
        assert rr.status_code==200,rr.text
        result=rr.json()
        assert result['manual_regions']==manual
        assert result['question_answers']['Q1']=='my answer'
        assert result['grading_performed'] is False
        assert result['transcription_verified'] is False
        assert len(result['lines'])==1
        assert client.get(f'/api/workspace/papers/{pid}/handwriting-line/1').status_code==404
        record=client.get(f'/api/workspace/papers/{pid}').json()
        assert record['paper']['transcript_verified']==0 and record['grades']==[]
