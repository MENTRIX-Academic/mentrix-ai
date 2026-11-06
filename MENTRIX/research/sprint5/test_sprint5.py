import csv
import json
from pathlib import Path
import pytest
from research.sprint5.audit_and_gate import run, policy_choice, predictions_on_frozen_split
from research.sprint5.ocr_runner import validate_manifest
from research.sprint5.render_report import render


def test_frozen_s03_reproduces_without_using_test_for_validation(tmp_path):
    report=run(out=tmp_path)
    assert report['frozen_test_predictions_reproduced']
    assert report['test_n']==129 and report['validation_n']==125
    assert report['s03_validation_selected_test_scores']['errors']==54
    assert report['s03_validation_selected_test_scores']['dangerous_full_credit']==26
    assert report['research_gate']['production_approval_enabled'] is False
    assert report['research_gate']['status']=='DISABLED_NO_VALIDATED_RULE'
    assert json.loads((tmp_path/'s05_reproducibility_and_gate.json').read_text())['test_n']==129


def test_validation_gate_stays_disabled_when_all_models_agree_wrong():
    votes={str(i):{'pred':{f'model_{m}':2 for m in range(7)},'gold':0} for i in range(100)}
    winner,candidates,_=policy_choice(votes)
    assert winner is None
    assert not any(v['eligible'] for v in candidates.values())


def make_manifest(p,rows):
    with p.open('w',newline='',encoding='utf-8') as f:
        w=csv.DictWriter(f,fieldnames=['sample_id','writer_code','split','image_path','ground_truth','verified_by'])
        w.writeheader();w.writerows(rows)


def test_ocr_manifest_requires_independently_verified_gt_and_safe_path(tmp_path):
    image_dir=tmp_path/'images';image_dir.mkdir()
    (image_dir/'a.png').write_bytes(b'fake image bytes - validate only does not open image')
    m=tmp_path/'manifest.csv'
    example={'sample_id':'a','writer_code':'W001','split':'test','image_path':'a.png','ground_truth':'hello','verified_by':'reviewer'}
    make_manifest(m,[example])
    assert len(validate_manifest(m,image_dir))==1
    make_manifest(m,[{**example,'verified_by':''}])
    with pytest.raises(ValueError,match='human-verified'):validate_manifest(m,image_dir)
    make_manifest(m,[{**example,'image_path':'../secrets.png'}])
    with pytest.raises(ValueError,match='unsafe'):validate_manifest(m,image_dir)


def test_ocr_manifest_rejects_writer_overlap(tmp_path):
    image_dir=tmp_path/'images';image_dir.mkdir()
    for name in ('a.png','b.png'):(image_dir/name).write_bytes(b'x')
    rows=[{'sample_id':str(i),'writer_code':'W003','split':split,'image_path':filename,
           'ground_truth':'test','verified_by':'human'} for i,split,filename in ((1,'train','a.png'),(2,'test','b.png'))]
    m=tmp_path/'manifest.csv';make_manifest(m,rows)
    with pytest.raises(ValueError,match='Writer leakage'):validate_manifest(m,image_dir)


def test_render_report_does_not_publish_student_answer_text(tmp_path):
    run(out=tmp_path)
    report_path=render(out=tmp_path)
    html=report_path.read_text(encoding='utf-8')
    assert 'Sprint 05' in html and '129' in html
    assert 'no answers' not in html.lower()
    assert 's05_private_ocr_predictions_LOCAL_ONLY' not in html


def test_mock_30_students_are_fictional_and_unique(tmp_path):
    from research.sprint5.mock_data_factory import build
    summary=build(out=tmp_path)
    assert summary['students']==30 and summary['sessions']==12
    assert summary['attendance_rows']==360
    payload=json.loads((tmp_path/'s05_mock_backend_data.json').read_text())
    assert len(set(row['student_id'] for row in payload['students']))==30
    assert all(row['synthetic'] and not row['login_enabled'] for row in payload['students'])
    assert all('pin' not in row for row in payload['students'])
