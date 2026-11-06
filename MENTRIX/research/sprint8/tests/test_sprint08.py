"""Tests use synthetic line boxes, text and fake OCR. Never real handwriting claims."""
import csv,io,json
from pathlib import Path
import pytest
from PIL import Image
from research.sprint8.line_evaluation import evaluate_lines
from research.sprint8.ground_truth_template import create_template
from research.sprint8.error_analysis import analyze
from research.sprint8.preflight import report as preflight
from research.sprint6.benchmark import PIPELINES,benchmark,load_manifest

def _line(page,box,txt,qid='Q1',verifier=None):
    ans=dict(page=page,bbox=box,raw_text=txt,text=txt,question_id=qid)
    if verifier is not None:
        ans['verified_by']=verifier
        ans['transcription']=txt
    return ans

def test_one_to_one_line_matching_and_ocr_are_separate():
    draft={'lines':[_line(0,[0,0,100,30],'hello world'),
                    _line(0,[0,40,100,70],'WRONG','Q9'),
                    _line(0,[200,200,220,220],'random')]}
    truth={'lines':[_line(0,[0,0,100,30],'hello word',verifier='reviewer_A'),
                    _line(0,[0,40,100,70],'WRONG',verifier='reviewer_A'),
                    _line(0,[0,80,100,110],'absent',verifier='reviewer_B')]}
    score=evaluate_lines(draft,truth)
    d=score['line_detection']
    assert (d['true_positives'],d['false_positives'],d['false_negatives'])==(2,1,1)
    assert d['precision']==d['recall']==pytest.approx(2/3,abs=1e-6)
    assert score['recognition_on_matched_lines']['char_errors']==1
    assert score['question_mapping_on_matched_lines']['exact_id_matches']==1
    assert score['unmatched_human_line_indices']==[2]

def test_line_detection_never_matches_one_prediction_twice():
    predicted={'lines':[_line(0,[0,0,100,30],'hi')]}
    truth={'lines':[_line(0,[0,0,100,30],'hi',verifier='A'),
                    _line(0,[0,0,100,30],'hi',verifier='A')]}
    scored=evaluate_lines(predicted,truth)
    assert scored['line_detection']['true_positives']==1
    assert scored['line_detection']['false_negatives']==1

def test_no_false_ocr_metric_when_no_boxes_match():
    result=evaluate_lines({'lines':[_line(0,[500,500,600,600],'hello')]},
                          {'lines':[_line(0,[0,0,100,40],'hello',verifier='A')]})
    assert result['recognition_on_matched_lines'] is None
    assert result['line_detection']['recall']==0

def test_require_independent_line_verification_and_text():
    with pytest.raises(ValueError,match='verified_by'):
        evaluate_lines({'lines':[]},{'lines':[dict(_line(0,[0,0,1,1],'x'),transcription='x')]})
    with pytest.raises(ValueError,match='independent transcription'):
        evaluate_lines({'lines':[]},{'lines':[dict(page=0,bbox=[0,0,10,10],question_id='Q1',transcription='',verified_by='A')]})
    assert evaluate_lines({'lines':[]},{})['status']=='NOT_EVALUATED'

def test_blank_gt_template_does_not_copy_model_prediction():
    draft={'status':'UNVERIFIED_OCR_DRAFT', 'lines':[_line(0,[0,0,100,30],'OCR hallucination')],
           'question_answers':{'Q1':'OCR hallucination'}}
    template=create_template(draft)
    serialized=json.dumps(template)
    assert 'OCR hallucination' not in serialized
    assert template['lines'][0]['verified_by']==''
    assert template['annotation_status']=='BLANK_NOT_GROUND_TRUTH'

def test_mock_rejected_by_scientific_analysis():
    with pytest.raises(ValueError,match='REAL OCR'):
        analyze([],{'status':'ENGINEERING_MOCK_ONLY'})

def test_real_validation_analysis_requires_exact_sample_pairs():
    scores={n:{'cer':.1,'wer':.2} for n in PIPELINES}
    m={'status':'REAL_OCR_MODELS_EXECUTED','model_executed':True,'partial_run':False,
       'split':'validation','pipeline_scores':scores}
    records=[{'pipeline':n,'sample_id':'s1','writer_code':'W1','ground_truth':'cat','prediction':'cat','split':'validation'}
             for n in PIPELINES]
    out=analyze(records,m)
    assert out['writer_count']==1 and out['line_count']==1
    assert out['by_writer']['E01_base_rgb']['W1']['cer']==0
    with pytest.raises(ValueError,match='same sample_ids'):
        analyze(records[:-1],m)
    with pytest.raises(ValueError,match='validation only'):
        analyze(records,{**m,'split':'test'})

def test_preflight_rejects_missing_splits(tmp_path):
    im=Image.new('RGB',(100,40),'white');im.save(tmp_path/'x.png')
    f=tmp_path/'m.csv'
    with f.open('w',newline='') as fp:
        w=csv.DictWriter(fp,fieldnames=['sample_id','writer_code','split','image_path','ground_truth','verified_by'])
        w.writeheader();w.writerow(dict(sample_id='x',writer_code='A',split='validation',image_path='x.png',ground_truth='cat',verified_by='IAM'))
    with pytest.raises(ValueError,match='train/validation/test'):
        preflight(f,tmp_path)

def test_dataset_path_leak_across_splits(tmp_path):
    Image.new('RGB',(100,40),'white').save(tmp_path/'x.png')
    f=tmp_path/'m.csv'
    with f.open('w',newline='') as fp:
        w=csv.DictWriter(fp,fieldnames=['sample_id','writer_code','split','image_path','ground_truth','verified_by'])
        w.writeheader()
        for i,(split,writer) in enumerate([('validation','A'),('test','B')]):
            w.writerow(dict(sample_id=str(i),writer_code=writer,split=split,image_path='x.png',ground_truth='cat',verified_by='IAM'))
    with pytest.raises(ValueError,match='Image path leakage'):
        load_manifest(f,tmp_path)

def test_frozen_test_reuse_blocked_before_inference(tmp_path):
    out=tmp_path/'test';out.mkdir()
    (out/'test_metrics.json').write_text('{}')
    with pytest.raises(ValueError,match='already evaluated'):
        benchmark(tmp_path/'nonexistent.csv',tmp_path,out,split='test',pipeline_names=['E01_base_rgb'])

def test_full_sheet_evaluation_exposes_independent_line_metrics():
    from research.sprint6.full_sheet import evaluate_full_sheet
    draft={'lines':[_line(0,[20,20,200,50],'answer','Q1')],
           'question_answers':{'Q1':'answer'}}
    truth={'questions':{'Q1':{'transcription':'answer'}},
           'lines':[_line(0,[20,20,200,50],'answer','Q1',verifier='independent-annotator')]}
    result=evaluate_full_sheet(draft,truth)
    assert result['ocr_metrics']['cer']==0
    assert result['independent_line_evaluation']['line_detection']['f1']==1
    assert result['independent_line_evaluation']['question_mapping_on_matched_lines']['exact_match_rate']==1
    assert result['grading_diagnostics']['status']=='NOT_EVALUATED'


def test_frozen_test_requires_complete_real_validation_evidence(tmp_path):
    from research.sprint6.benchmark import dataset_content_hash,sha256
    for name in ['v','t']:
        Image.new('RGB',(120,45),'white' if name=='v' else 'gray').save(tmp_path/f'{name}.png')
    manifest=tmp_path/'m.csv'
    with manifest.open('w',newline='') as fp:
        w=csv.DictWriter(fp,fieldnames=['sample_id','writer_code','split','image_path','ground_truth','verified_by'])
        w.writeheader()
        for sid,writer,split in [('v','A','validation'),('t','B','test')]:
            w.writerow(dict(sample_id=sid,writer_code=writer,split=split,image_path=f'{sid}.png',ground_truth='cat',verified_by='IAM'))
    rows=load_manifest(manifest,tmp_path)
    resultdir=tmp_path/'results';(resultdir/'validation').mkdir(parents=True)
    selection={'validation_manifest_sha256':sha256(manifest),
               'dataset_content_sha256':dataset_content_hash(rows),'selected_pipeline':'E01_base_rgb'}
    (resultdir/'selected_from_validation.json').write_text(json.dumps(selection))
    with pytest.raises(ValueError,match='Missing full real-model validation'):
        benchmark(manifest,tmp_path,resultdir/'test',split='test',pipeline_names=['E01_base_rgb'])
    scores={n:{'cer':.2,'wer':.4} for n in PIPELINES}
    scores['E03_small_rgb']={'cer':.1,'wer':.3}
    val={'status':'REAL_OCR_MODELS_EXECUTED','model_executed':True,'partial_run':False,
         'split':'validation','pipeline_scores':scores,'manifest_sha256':sha256(manifest),
         'dataset_content_sha256':dataset_content_hash(rows)}
    (resultdir/'validation'/'validation_metrics.json').write_text(json.dumps(val))
    with pytest.raises(ValueError,match='differs from genuine validation winner'):
        benchmark(manifest,tmp_path,resultdir/'test',split='test',pipeline_names=['E01_base_rgb'])
