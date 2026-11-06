"""Sprint 04 — audit previously frozen Sprint03 test predictions, no refitting, no OCR.

Use error labels that are supported by scores only. Contradiction/paraphrase require a
human review; never infer either from grade disagreement.
"""
from __future__ import annotations
import argparse, csv, json, hashlib, math
from pathlib import Path
from collections import defaultdict, Counter
import numpy as np
from sklearn.metrics import cohen_kappa_score, confusion_matrix
from research.sprint3.asag_benchmark import ROOT, read_asag, filehash

S03 = ROOT/'research'/'sprint3'/'results'
S04 = ROOT/'research'/'sprint4'/'results'
DATA = ROOT/'research'/'sprint3'/'data'/'asag_dataset.csv'


def load_csv(path):
    with open(path, encoding='utf-8-sig', newline='') as f:
        return list(csv.DictReader(f))


def scores(gold, predicted):
    g, p = np.asarray(gold, dtype=int), np.asarray(predicted, dtype=int)
    if not len(g):
        raise ValueError('Cannot score zero rows')
    qwk = None
    if len(set(g)|set(p)) > 1:
        val = cohen_kappa_score(g,p, labels=[0,1,2], weights='quadratic')
        if np.isfinite(val): qwk = round(float(val), 5)
    return {'n':len(g),'mae':round(float(np.mean(abs(g-p))),5),
            'exact':round(float(np.mean(g==p)),5), 'qwk':qwk,
            'errors':int(np.sum(g!=p)),
            'dangerous_full_credit':int(np.sum((p==2)&(g<2))),
            'missed_full_credit':int(np.sum((g==2)&(p<2))),
            'two_point_errors':int(np.sum(abs(g-p)==2)),
            'confusion_gold_rows_pred_cols':confusion_matrix(g,p,labels=[0,1,2]).tolist()}


def frozen_inputs(s03=S03, dataset=DATA):
    s03 = Path(s03); dataset=Path(dataset)
    manifest=json.loads((s03/'asag_s03_metrics.json').read_text(encoding='utf-8'))
    if filehash(dataset) != manifest['dataset']['source_file_sha256']:
        raise ValueError('ASAG source hash differs from Sprint03. STOP: cannot claim same test set.')
    rows, nonblank, blanks = read_asag(dataset)
    ids={r['sample_id']:r for r in rows}
    split_rows=load_csv(s03/'asag_s03_splits.csv')
    split_map={r['sample_id']:r['split'] for r in split_rows}
    if len(split_map)!=len(nonblank) or len(split_rows)!=len(nonblank):
        raise ValueError('Split manifest is not complete or sample IDs duplicate')
    if set(split_map)!={r['sample_id'] for r in nonblank}:
        raise ValueError('Split manifest does not match nonblank ASAG rows')
    preds=load_csv(s03/'asag_s03_test_predictions.csv')
    methods=set(manifest['method_summary'])
    test_ids={i for i,part in split_map.items() if part=='test'}
    seen=set()
    for rec in preds:
        key=(rec['method'],rec['sample_id'])
        if key in seen or rec['method'] not in methods or rec['sample_id'] not in test_ids:
            raise ValueError('Duplicate/unknown or non-test prediction encountered')
        seen.add(key)
        row=ids[rec['sample_id']]
        if int(rec['gold_score'])!=row['human_score'] or rec['prompt_id']!=row['prompt_id']:
            raise ValueError('Prediction row does not agree with ASAG human grade or prompt')
    if seen!={(method,sample) for method in methods for sample in test_ids}:
        raise ValueError('Missing predictions for one or more methods/test samples')
    return manifest, ids, split_map, preds, sorted(test_ids,key=int)


def analyze(s03=S03, dataset=DATA, output=S04, max_review=45):
    manifest,ids,parts,preds,test_ids=frozen_inputs(s03,dataset)
    bymethod=defaultdict(list)
    for r in preds: bymethod[r['method']].append(r)
    per_method={}
    for name, rr in sorted(bymethod.items()):
        per_method[name]=scores([int(r['gold_score']) for r in rr],[int(r['predicted_score']) for r in rr])
        # verify we reproduced the same rounded integer MAE published in Sprint03.
        old=manifest['method_summary'][name]['micro_test_mae']
        if not math.isclose(per_method[name]['mae'], old, abs_tol=0.000015):
            raise ValueError('Frozen results do not reproduce Sprint03 MAE: '+name)
    selected = [r for r in preds if str(r['selected_on_validation']).lower()=='true']
    if len(selected)!=len(test_ids) or len({r['sample_id'] for r in selected})!=len(test_ids):
        raise ValueError('Exactly one validation-selected prediction per held-out sample is required')
    selected.sort(key=lambda r:int(r['sample_id']))
    selected_metric=scores([int(r['gold_score']) for r in selected],[int(r['predicted_score']) for r in selected])
    disagreement=defaultdict(list)
    for r in preds: disagreement[r['sample_id']].append(r)
    candidates=[]
    for r in selected:
        id_=r['sample_id']; allpred={int(p['predicted_score']) for p in disagreement[id_]}
        error=abs(int(r['gold_score'])-int(r['predicted_score']))
        gold,pred=int(r['gold_score']),int(r['predicted_score'])
        error_type=('dangerous_full_credit' if pred==2 and gold<2 else
                    'missed_full_credit' if gold==2 and pred<2 else
                    'two_point_error' if error==2 else
                    'other_score_error' if error else 'correctly_scored')
        candidates.append({'sample_id':id_,'question_id':r['prompt_id'],'gold':gold,'pred':pred,
                           'selected_method':r['method'], 'abs_error':error,
                           'method_disagreement':len(allpred)>1,'range_of_method_scores':max(allpred)-min(allpred),
                           'error_class':error_type})
    # One record per question first, then safety-critical cases. Keep manual review blinded
    # to the machine's arbitrary heuristic error type: provide it only as triage metadata.
    rank={'dangerous_full_credit':0,'two_point_error':1,'missed_full_credit':2,'other_score_error':3,'correctly_scored':4}
    priority=sorted(candidates,key=lambda r:(rank[r['error_class']],-r['abs_error'],-r['range_of_method_scores'],int(r['sample_id'])))
    chosen=[]; used_questions=set()
    for item in priority:
        if item['question_id'] not in used_questions:
            chosen.append(item);used_questions.add(item['question_id'])
    chosen_ids={r['sample_id'] for r in chosen}
    for item in priority:
        if len(chosen)>=max_review: break
        if item['sample_id'] not in chosen_ids:
            chosen.append(item); chosen_ids.add(item['sample_id'])
    per_question=[]
    for q in sorted({r['question_id'] for r in candidates}, key=int):
        r=[x for x in candidates if x['question_id']==q]
        per_question.append({'question_id':q,'n':len(r),'mae':round(sum(x['abs_error'] for x in r)/len(r),5),
                             'errors':sum(bool(x['abs_error']) for x in r),
                             'dangerous_full_credit':sum(x['error_class']=='dangerous_full_credit' for x in r)})
    out=Path(output);out.mkdir(parents=True,exist_ok=True)
    review_fields=['sample_id','question_id','question','student_answer','reference_answer','human_score',
                   's03_predicted_score','s03_method','triage_reason','reviewer_verified_score',
                   'reviewer_error_category','reviewer_notes']
    with (out/'s04_human_review_template_LOCAL_ONLY.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=review_fields);writer.writeheader()
        for x in chosen:
            row=ids[x['sample_id']]
            writer.writerow({'sample_id':x['sample_id'],'question_id':x['question_id'],
                             'question':next(r['question'] for r in _source_questions(dataset) if str(r['sample_id'])==x['sample_id']),
                             'student_answer':row['answer_text'],'reference_answer':row['reference_text'],
                             'human_score':x['gold'],'s03_predicted_score':x['pred'],
                             's03_method':x['selected_method'],'triage_reason':x['error_class'],
                             'reviewer_verified_score':'','reviewer_error_category':'','reviewer_notes':''})
    report={'status':'EXECUTED_FROZEN_SPRINT03_ERROR_ANALYSIS',
            'dataset_hash':manifest['dataset']['source_file_sha256'],
            'frozen_sprint03_seed':manifest['seed'],
            'test_n':len(test_ids),'human_review_examples':len(chosen),
            'results_are_previous_lightweight_models_not_transformers':True,
            's03_all_methods':per_method,'s03_validation_selected':selected_metric,
            'per_question_validation_selected':per_question,
            'error_types':'Only score-based triage. Contradiction, paraphrase, and factual correctness require human annotation.',
            'limitations':['No embeddings or NLI executed by this script','Only score differences, not semantic diagnoses',
                           'No approved rubrics or criterion-level grades in ASAG','Data is long typed English, not MENTRIX 1–3 word or handwriting',
                           'Held-out test used only for final evaluation, never to choose a method or threshold'],
            'source':'ASAG dataset from DigiKlausur; student answers excluded from HTML and JSON.'}
    (out/'s04_error_analysis.json').write_text(json.dumps(report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    return report


def _source_questions(dataset):
    with open(dataset,encoding='utf-8-sig',newline='') as f:
        for idx,row in enumerate(csv.DictReader(f),1):
            yield {'sample_id':str(idx),'question':row['question']}


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--data',type=Path,default=DATA)
    p.add_argument('--s03',type=Path,default=S03)
    p.add_argument('--output',type=Path,default=S04)
    args=p.parse_args()
    report=analyze(args.s03,args.data,args.output)
    print('SPRINT04 ERROR ANALYSIS COMPLETED: frozen S03 test_n=',report['test_n'])
    print('Selected method metrics:',report['s03_validation_selected'])
    print('Human review file (LOCAL ONLY):',args.output/'s04_human_review_template_LOCAL_ONLY.csv')

if __name__=='__main__': main()
