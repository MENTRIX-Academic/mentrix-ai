"""Reproducible demonstration audit. NOT a held-out scientific evaluation."""
from pathlib import Path
import csv,json,sys,time,collections,hashlib,platform,datetime
BASE=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(BASE))
from adapter import QUESTIONS,grade
IN=BASE/'research/data/curated_demo_cases.csv'
OUT=BASE/'research/results'

def audit():
    OUT.mkdir(exist_ok=True,parents=True)
    rows=[]
    with IN.open(newline='',encoding='utf-8-sig') as f: cases=list(csv.DictReader(f))
    for c in cases:
        q=QUESTIONS[c['question_id']]
        line={k:c[k] for k in ['case_id','question_id','student_answer','purpose','author_designed_policy_v2','provenance']}
        line['question_type']=q['type']
        for version in ('strict','v1','v2'):
            t0=time.perf_counter()
            result=grade(q,c['student_answer'],version)
            line[f'{version}_decision']=result['decision']
            line[f'{version}_score']=result['proposed_score']
            line[f'{version}_method']=result['method']
            line[f'{version}_reason']=result['reason']
            line[f'{version}_elapsed_ms']=round((time.perf_counter()-t0)*1000,4)
        line['changed_v1_to_v2']=str(line['v1_decision']!=line['v2_decision'])
        line['v2_matches_illustrative_policy']=str(line['v2_decision']=={'review':'needs_review'}.get(c['author_designed_policy_v2'],c['author_designed_policy_v2']))
        rows.append(line)
    with (OUT/'observed_comparison.csv').open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0].keys());w.writeheader();w.writerows(rows)
    groups=[]
    for typ in sorted({r['question_type'] for r in rows}):
        arr=[r for r in rows if r['question_type']==typ]
        groups.append({'type':typ,'cases':len(arr),'v1_to_v2_changed':sum(r['changed_v1_to_v2']=='True' for r in arr),
            'v1_review_cases':sum(r['v1_decision']=='needs_review' for r in arr),
            'v2_review_cases':sum(r['v2_decision']=='needs_review' for r in arr),
            'v2_design_checks_matched':sum(r['v2_matches_illustrative_policy']=='True' for r in arr)})
    metadata={'evaluation_type':'CURATED_ASSISTANT_AUTHORED_DESIGN_CASES_NOT_UNSEEN_TEST_NOT_STUDENT_ACCURACY',
      'original_source_sha256':{p:hashlib.sha256((BASE/p).read_bytes()).hexdigest() for p in ['grader.py','grader_v2.py','questions.json']},
      'python_version':platform.python_version(),'datetime_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
      'total_cases':len(rows),'changed_decisions':sum(r['changed_v1_to_v2']=='True' for r in rows),
      'grouped':groups,
      'missing_for_complete_scientific_phase3':['Actual independent TA/educator ground truth','Real-student/writer-disjoint held-out data','Resolved descriptive rubric grading and model rerun','OCR / real scan evaluation']}
    (OUT/'observed_summary.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Cases:',len(rows),'Changed decisions:',metadata['changed_decisions'])
    for g in groups:print(g)
    print('Wrote research/results/observed_comparison.csv & observed_summary.json')
    return rows,metadata
if __name__=='__main__':audit()
