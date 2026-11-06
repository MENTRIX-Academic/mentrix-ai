"""Smoke/integration tests use synthetic printed text and fake recognition only.
These tests never claim real handwriting model quality or a CER/WER result.
"""
import csv
import io
import json
from pathlib import Path
import pytest
from PIL import Image, ImageDraw, ImageFont
from research.sprint6.benchmark import PIPELINES, load_manifest, corpus_scores, benchmark
from research.sprint6.prepare_iam import build
from research.sprint6.full_sheet import (bbox_iou, render_pages, transcribe_full_sheet,
                                          evaluate_full_sheet, suggest_line_boxes)

def _font():
    p='/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'
    return ImageFont.truetype(p,24) if Path(p).exists() else ImageFont.load_default()

def sheet(texts=('Q1: B','Q2: central processing unit','Q3: 5','Q4: My answer is long')):
    image=Image.new('RGB',(800,520),'white')
    d=ImageDraw.Draw(image)
    for i,t in enumerate(texts):d.text((55,50+i*100),t,font=_font(),fill='black')
    b=io.BytesIO();image.save(b,format='PNG');return b.getvalue()

def test_text_metrics_are_micro_averaged():
    m=corpus_scores([{'ground_truth':'hello world','prediction':'hello word'},
                     {'ground_truth':'A','prediction':'A'}])
    assert m['n']==2 and m['char_errors']==1 and m['word_errors']==1
    assert m['reference_chars']==12 and m['reference_words']==3


def test_synthetic_line_detection():
    with Image.open(io.BytesIO(sheet())) as img:
        boxes=suggest_line_boxes(img)
        assert len(boxes)==4,boxes
        assert boxes==sorted(boxes,key=lambda x:x[1])


def test_manual_full_sheet_and_independent_evaluation():
    pages=render_pages(sheet(),'paper.png')
    assert len(pages)==1
    regions=[{'page':0,'question_id':f'Q{i+1}', 'x0':30,'y0':40+i*100,'x1':750,'y1':95+i*100} for i in range(4)]
    texts=iter(['B','central processing unit','5','My answer is long'])
    draft=transcribe_full_sheet(sheet(),'paper.png',lambda image: next(texts),valid_question_ids=['Q1','Q2','Q3','Q4'],regions=regions)
    assert draft['status']=='UNVERIFIED_OCR_DRAFT'
    assert draft['question_answers']['Q2']=='central processing unit'
    assert draft['grading_performed'] is False
    truth={'questions':{q:{'transcription':answer} for q,answer in draft['question_answers'].items()},
           'regions':[{'page':0,'question_id':r['question_id'],'bbox':rbox} for r,rbox in []]}
    truth.pop('regions')
    result=evaluate_full_sheet(draft,truth)
    assert result['ocr_metrics']['cer']==0
    assert result['question_segmentation']['recall']==1
    assert result['spatial_question_regions']['status']=='NOT_EVALUATED'


def test_automatic_question_label_detection():
    texts=iter(['Q1: B','Q2: unit','Q3: 5','Q4: supervised learning'])
    draft=transcribe_full_sheet(sheet(),'paper.png',lambda im:next(texts),
                                valid_question_ids=['Q1','Q2','Q3','Q4'])
    assert len(draft['lines'])==4
    assert draft['question_coverage']['matched']==4
    assert draft['question_answers']['Q1']=='B'


def test_single_crop_unassigned_ocr_is_visible_and_not_graded():
    # Regression: one IAM-style handwritten crop has no Q1/Q2 label.
    # Previously UI extracted_text was EMPTY despite model text being recognized.
    draft=transcribe_full_sheet(sheet(('test handwriting',)),'crop.png',
                                lambda image:'supervised learning',
                                valid_question_ids=['Q1','Q2','Q3','Q4'])
    assert draft['question_coverage']['matched']==0
    assert draft['extracted_text']=='supervised learning'
    assert draft['raw_ocr_text']=='supervised learning'
    assert draft['unassigned_lines'][0]['text']=='supervised learning'
    assert draft['line_stats']['nonempty']==1
    assert draft['question_answers']=={}
    assert draft['grading_performed'] is False


def test_mixed_recognized_and_unassigned_lines_stay_in_raw_preview():
    # The top line is not mapped; only the second line has an explicit Q1 label.
    demo=sheet(('some title','Q1: B'))
    texts=iter(['some title','Q1: B'])
    draft=transcribe_full_sheet(demo,'paper.png',lambda image:next(texts),
                                valid_question_ids=['Q1'])
    assert draft['question_answers']=={'Q1':'B'}
    assert draft['extracted_text']=='Q1: B'
    assert draft['raw_ocr_text']=='some title\nQ1: B'
    assert draft['unassigned_lines'][0]['text']=='some title'


def test_when_model_output_is_empty_we_report_an_actual_blank():
    draft=transcribe_full_sheet(sheet(('Q1: anything',)),'paper.png',
                                lambda image:'',valid_question_ids=['Q1'])
    assert draft['extracted_text']==''
    assert draft['line_stats']['detected']>=1
    assert any('No readable text' in s for s in draft['warnings'])


def test_detect_missing_question_and_no_grading():
    texts=iter(['Unknown opening','Q2: explanation','Q3: 5','Q4: words'])
    draft=transcribe_full_sheet(sheet(),'paper.png',lambda im:next(texts),
                                valid_question_ids=['Q1','Q2','Q3','Q4'])
    assert draft['question_coverage']['matched']==3
    assert 'Q1' in ' '.join(draft['warnings'])
    assert draft['grading_performed'] is False


def test_invalid_manual_bbox_rejected():
    with pytest.raises(ValueError,match='outside page'):
        transcribe_full_sheet(sheet(),'p.png',lambda im:'B',valid_question_ids=['Q1'],
                              regions=[{'page':0,'question_id':'Q1','x0':0,'y0':0,'x1':5000,'y1':99}])


def test_iou():
    assert bbox_iou([0,0,100,100],[0,0,100,100])==1
    assert bbox_iou([0,0,10,10],[20,20,30,30])==0


def test_manifest_validation_writer_leak(tmp_path):
    (tmp_path/'x.png').write_bytes(sheet())
    manifest=tmp_path/'manifest.csv'
    fields=['sample_id','writer_code','split','image_path','ground_truth','verified_by']
    with manifest.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        w.writerow(dict(sample_id='a',writer_code='W1',split='train',image_path='x.png',ground_truth='hello',verified_by='H'))
        w.writerow(dict(sample_id='b',writer_code='W1',split='test',image_path='x.png',ground_truth='world',verified_by='H'))
    with pytest.raises(ValueError,match='Writer leakage'):load_manifest(manifest,tmp_path)


def test_mock_comparison_paired_same_lines_and_not_ocr_evidence(tmp_path):
    (tmp_path/'x.png').write_bytes(sheet())
    manifest=tmp_path/'manifest.csv'
    fields=['sample_id','writer_code','split','image_path','ground_truth','verified_by']
    with manifest.open('w',newline='') as f:
        w=csv.DictWriter(f,fieldnames=fields);w.writeheader()
        w.writerow(dict(sample_id='sample1',writer_code='writer1',split='validation',image_path='x.png',ground_truth='one',verified_by='R'))
    out=tmp_path/'results'/'validation'
    report=benchmark(manifest,tmp_path,out,recognizer_factory=lambda mid: (lambda img:'one'),
                     pipeline_names=list(PIPELINES))
    assert report['status']=='ENGINEERING_MOCK_ONLY'
    assert report['model_executed'] is False
    assert all(m['cer']==0 for m in report['pipeline_scores'].values())
    assert not (tmp_path/'results'/'selected_from_validation.json').exists()
    preds=list(csv.DictReader((out/'validation_predictions_LOCAL_ONLY.csv').open(encoding='utf-8-sig')))
    assert len(preds)==4 and len({r['sample_id'] for r in preds})==1


def test_iam_importer_requires_writer_independent_splits(tmp_path):
    base=tmp_path
    imgs=base/'images';xm=base/'xml';xm.mkdir()
    idnames=['a01-000u-00','b01-000u-00','c01-000u-00']
    for i,sid in enumerate(idnames):
        form=sid.rsplit('-',1)[0]
        (xm/f'{form}.xml').write_text(f'<form id="{form}" writer-id="W{i}" />')
        target=imgs/sid[:3]/form;target.mkdir(parents=True)
        (target/(sid+'.png')).write_bytes(sheet())
    lines=base/'lines.txt';lines.write_text('\n'.join(f'{sid} ok 154 10 20 30 40 AT Sample|text' for sid in idnames))
    split={}
    for sid,sp in zip(idnames,['train','validation','test']):
        p=base/(sp+'.txt');p.write_text(sid+'\n');split[sp]=p
    out=base/'prepared.csv'
    info=build(lines,xm,imgs,split,out)
    assert info['count']==3 and info['writer_count']==3
    assert len(load_manifest(out,imgs))==3


def test_api_handwriting_route_real_integration_but_mock_recognizer(tmp_path,monkeypatch):
    """Checks FastAPI upload -> handwriting draft -> staff verification -> grades.
    Recognizer is a stub; there is NO actual model evaluation in this test.
    """
    import os
    from fastapi.testclient import TestClient
    import integrated_workflow as iw
    import handwriting_routes as hw
    monkeypatch.setattr(iw,'DB',tmp_path/'workspace_test.sqlite3')
    monkeypatch.setattr(iw,'UPLOADS',tmp_path/'uploads')
    iw.UPLOADS.mkdir(parents=True)
    monkeypatch.setattr(hw,'UPLOADS',iw.UPLOADS)
    monkeypatch.setenv('MENTRIX_STAFF_PIN','test-pin-123')
    iw.init_db()
    import app
    with TestClient(app.app) as client:
        denied=client.get('/api/workspace/handwriting/config')
        assert denied.status_code==401
        assert client.post('/api/auth/login',json={'pin':'test-pin-123'}).status_code==200
        assert client.get('/api/workspace/handwriting/config').status_code==200
        uploaded=client.post('/api/workspace/papers/upload',data={'quiz_id':'AI-QUIZ01','student_id':'ST001'},
                             files={'file':('fake_printed_fixture.png',sheet(),'image/png')})
        assert uploaded.status_code==200, uploaded.text
        pid=uploaded.json()['paper_id']
        # The experimental predictor recognizes an artificial, controlled line sequence.
        texts=iter(['Q1: B','Q2: central processing unit','Q3: 5','Q4: essay answer'])
        monkeypatch.setattr(hw,'get_recognizer',lambda model_id:lambda image:next(texts))
        response=client.post(f'/api/workspace/papers/{pid}/handwriting-draft',json={'pipeline':'E01_base_rgb'})
        assert response.status_code==200,response.text
        result=response.json()
        assert result['status']=='UNVERIFIED_OCR_DRAFT'
        assert result['question_coverage']['matched']==4
        assert len(result['overlay_urls'])==1
        overlay=client.get(result['overlay_urls'][0])
        assert overlay.status_code==200 and overlay.content.startswith(b'\x89PNG')
        current=client.get(f'/api/workspace/papers/{pid}').json()
        assert current['paper']['transcript_verified']==0 and current['grades']==[]
        verified=client.post(f'/api/workspace/papers/{pid}/verify-and-grade',json={
            'corrected_text':'Q1: B\nQ2: central processing unit\nQ3: 5\nQ4: essay answer',
            'verified':True,'answers':{'Q1':'B','Q2':'central processing unit','Q3':'5','Q4':'essay answer'}})
        assert verified.status_code==200,verified.text
        grades=verified.json()['grades']
        assert len(grades)==4
        assert sum(g['status']=='auto_scored' for g in grades)==3
        assert next(g for g in grades if g['question_id']=='Q4')['status']=='pending_ta'


def test_api_unlabeled_single_crop_shows_raw_ocr_after_reload(tmp_path,monkeypatch):
    # End-to-end route/DB regression for the user's p01_region_01.jpg case.
    # A stubbed recognizer proves presentation/data handling only, NOT model accuracy.
    from fastapi.testclient import TestClient
    import integrated_workflow as iw
    import handwriting_routes as hw
    monkeypatch.setattr(iw,'DB',tmp_path/'workspace_fix_test.sqlite3')
    monkeypatch.setattr(iw,'UPLOADS',tmp_path/'uploads')
    iw.UPLOADS.mkdir(parents=True)
    monkeypatch.setattr(hw,'UPLOADS',iw.UPLOADS)
    monkeypatch.setenv('MENTRIX_STAFF_PIN','fix-test-pin')
    iw.init_db()
    import app
    with TestClient(app.app) as client:
        assert client.post('/api/auth/login',json={'pin':'fix-test-pin'}).status_code==200
        uploaded=client.post('/api/workspace/papers/upload',
            data={'quiz_id':'AI-QUIZ01','student_id':'ST001'},
            files={'file':('p01_region_01.jpg',sheet(('handwritten note',)),'image/png')})
        assert uploaded.status_code==200, uploaded.text
        pid=uploaded.json()['paper_id']
        monkeypatch.setattr(hw,'get_recognizer',lambda _:lambda image:'a handwritten sentence')
        response=client.post(f'/api/workspace/papers/{pid}/handwriting-draft',
                             json={'pipeline':'E01_base_rgb'})
        assert response.status_code==200,response.text
        draft=response.json()
        assert draft['raw_ocr_text']=='a handwritten sentence'
        assert draft['extracted_text']=='a handwritten sentence'
        assert draft['question_coverage']=={'matched':0,'expected':4}
        assert draft['question_answers']=={}
        saved=client.get(f'/api/workspace/papers/{pid}').json()
        assert saved['paper']['extracted_text']=='a handwritten sentence'
        assert saved['paper']['transcript_verified']==0
        assert saved['grades']==[]
        persisted=client.get(f'/api/workspace/papers/{pid}/handwriting-draft').json()
        assert persisted['raw_ocr_text']=='a handwritten sentence'
        assert persisted['unassigned_lines'][0]['text']=='a handwritten sentence'


def test_oracle_vs_draft_grading_are_evaluated_separately():
    from research.sprint6.full_sheet import evaluate_full_sheet
    bank={'Q1':{'kind':'mcq','answer_key':'B','allowed_answers':['B'],'max_score':1},
          'Q2':{'kind':'short','answer_key':'central processing unit','allowed_answers':['central processing unit'],'max_score':2}}
    truth={'questions':{'Q1':{'transcription':'B','gold_grade':1},
                        'Q2':{'transcription':'central processing unit','gold_grade':2}}}
    draft={'question_answers':{'Q1':'A','Q2':'central processing unit'},'lines':[]}
    r=evaluate_full_sheet(draft,truth,bank)
    assert r['ocr_metrics']['cer']>0
    assert r['grading_diagnostics']['verified_text_oracle']['correct_auto_grades']==2
    assert r['grading_diagnostics']['unverified_ocr_draft']['unsafe_auto_grades']==1
    assert 'Q1' in r['grading_diagnostics']['ocr_changed_scoring_decision_question_ids']
