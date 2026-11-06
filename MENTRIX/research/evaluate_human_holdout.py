"""Optional human holdout evaluator. No genuine labeled data is shipped.
Only accepts independent TA labels in a frozen holdout; do not use same data for tuning.
"""
from pathlib import Path
import sys,csv,json,collections
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT))
from adapter import QUESTIONS,grade

def main(path):
    with Path(path).open(encoding='utf-8-sig',newline='') as f: rows=list(csv.DictReader(f))
    if not rows:raise ValueError('No labelled rows. Template intentionally blank.')
    fields=['question_id','student_answer','writer_id','split','label_source','human_decision','human_score','reviewer_id','source_quiz_version']
    for i,r in enumerate(rows,2):
        missing=[k for k in fields if not (r.get(k) or '').strip()]
        if missing:raise ValueError(f'Row {i}: missing {missing}')
        if r['split'].strip().lower()!='holdout':raise ValueError(f'Row {i}: only frozen holdout rows accepted')
        if r['label_source'].strip()!='TA_INDEPENDENT':raise ValueError(f'Row {i}: source must be TA_INDEPENDENT')
        if r['human_decision'] not in ('correct','incorrect','review'):raise ValueError(f'Row {i}: unknown decision')
        if r['question_id'] not in QUESTIONS:raise ValueError(f'Row {i}: unknown question')
    result=[]
    for r in rows:
        out=grade(QUESTIONS[r['question_id']],r['student_answer'],'v2')
        human='needs_review' if r['human_decision']=='review' else r['human_decision']
        result.append({'question_id':r['question_id'],'question_type':QUESTIONS[r['question_id']]['type'],
          'predicted':out['decision'],'human_decision':human,'auto':out['decision']!='needs_review',
          'unsafe_auto':out['decision']!='needs_review' and out['decision']!=human})
    report=[]
    for t in sorted({r['question_type'] for r in result}):
        part=[x for x in result if x['question_type']==t];aut=[x for x in part if x['auto']]
        report.append({'type':t,'n':len(part),'auto_coverage':round(len(aut)/len(part),3),
           'unsafe_automatic_decisions':sum(x['unsafe_auto'] for x in part),
           'auto_agreement':round(sum(x['predicted']==x['human_decision'] for x in aut)/len(aut),3) if aut else None,
           'caution':'Only independent TA decision labels, not OCR and not score MAE'})
    print(json.dumps({'evaluation_status':'HUMAN_HOLDOUT_ONLY_IF_PROVENANCE_VERIFIED','rows':len(result),'metrics':report},indent=2))
if __name__=='__main__':
    if len(sys.argv)!=2:raise SystemExit('Usage: py research/evaluate_human_holdout.py PATH_TO_INDEPENDENT_LABELLED_CSV')
    main(sys.argv[1])
