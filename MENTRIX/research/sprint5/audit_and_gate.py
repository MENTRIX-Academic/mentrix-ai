"""Sprint05: exact frozen ASAG reproducibility + validation-only research review gate.

Runs local lightweight S03 baselines; no Transformer weights, OCR images, model
fine-tuning, rubric claim or production publishing. Test is never used to choose
methods/policies. Protected student text stays in the original local CSV.
"""
from __future__ import annotations
import argparse
import csv
import json
import math
from collections import defaultdict, Counter
from datetime import datetime, timezone
from pathlib import Path
import numpy as np
from sklearn.metrics import confusion_matrix
from research.sprint3.asag_benchmark import METHODS, predict_reference, _rounded
from research.sprint2.benchmark import model_factory, vectors
from research.sprint4.error_analysis import frozen_inputs, scores, ROOT, DATA, S03
from research.sprint4.model_benchmark import wilson_lower

OUT = ROOT / 'research' / 'sprint5' / 'results'


def predictions_on_frozen_split(dataset=DATA, s03=S03):
    """Re-run all seven S03 baselines on TRAIN for VALIDATION and TEST.

    Abort if any TEST result differs from historical S03 (reproducibility).
    """
    original, ids, parts, test_rows, test_ids = frozen_inputs(s03, dataset)
    by_q = defaultdict(lambda: defaultdict(list))
    for sample_id, part in parts.items():
        by_q[ids[sample_id]['prompt_id']][part].append(ids[sample_id])
    old_test={(r['sample_id'],r['method']):int(r['predicted_score']) for r in test_rows}
    val_by_id=defaultdict(dict); test_by_id=defaultdict(dict)
    for q, d in sorted(by_q.items(),key=lambda pair:int(pair[0])):
        train=d['train']; val=d['validation']; test=d['test']
        if min(map(len,(train,val,test)))<1: raise ValueError('Missing split for question '+q)
        for method in METHODS:
            y = [r['human_score'] for r in train]
            if method=='reference_jaccard_ridge':
                v_raw=predict_reference(train,val)
                t_raw=predict_reference(train,test)
            else:
                model=model_factory(method)
                model.fit(vectors(train,method),y)
                v_raw=model.predict(vectors(val,method))
                t_raw=model.predict(vectors(test,method))
            for r,p in zip(val,_rounded(v_raw)):
                val_by_id[r['sample_id']][method]=int(p)
            for r,p in zip(test,_rounded(t_raw)):
                key=(r['sample_id'],method)
                if key not in old_test or int(p)!=old_test[key]:
                    raise ValueError(f'Sprint03 frozen prediction mismatch: {key}: {p} != {old_test.get(key)}')
                test_by_id[r['sample_id']][method]=int(p)
    if len(test_by_id)!=len(test_ids): raise ValueError('Incomplete TEST reproduction')
    if len(val_by_id)!=(len(parts)-len(test_ids)-sum(p=='train' for p in parts.values())):
        raise ValueError('Incomplete VALIDATION predictions')
    return original,ids,parts,val_by_id,test_by_id


def policy_choice(method_predictions, min_n=35, target_lower=0.90):
    """Select only on validation; never look at test labels here.

    We require Wilson 95% lower >= target_lower; if not, no auto-accept.
    Agreement is a heuristic, not a model certainty probability.
    """
    method_names=sorted(next(iter(method_predictions.values()))['pred'])
    candidates={
        'all_7_agree':lambda votes: max(Counter(votes).values())==len(method_names),
        'at_least_6_agree':lambda votes:max(Counter(votes).values())>=6,
        'at_least_5_agree':lambda votes:max(Counter(votes).values())>=5,
    }
    reports={}
    for rule,matcher in candidates.items():
        matched=[]
        for sid,entry in method_predictions.items():
            votes=[entry['pred'][name] for name in method_names]
            if matcher(votes):
                vote_counts=Counter(votes)
                # Ties at 5/6/7 impossible for 7 baselines
                prediction=vote_counts.most_common(1)[0][0]
                matched.append((sid,prediction,entry['gold']))
        n=len(matched);correct=sum(p==gold for _,p,gold in matched)
        lower=wilson_lower(correct,n)
        reports[rule]={'validation_n':n,'validation_correct':correct,'validation_accuracy':round(correct/n,5) if n else None,
                       'wilson_95_lower':round(lower,5),'eligible':n>=min_n and lower>=target_lower}
    feasible=[rule for rule,rep in reports.items() if rep['eligible']]
    best=max(feasible,key=lambda rule:(reports[rule]['validation_n'],reports[rule]['wilson_95_lower'])) if feasible else None
    return best,reports,candidates


def run(out=OUT, dataset=DATA, s03=S03):
    manifest,ids,parts,val,test=predictions_on_frozen_split(dataset,s03)
    val_data={sid:{'pred':pred,'gold':ids[sid]['human_score']} for sid,pred in val.items()}
    selected,candidate_validation,checks=policy_choice(val_data)
    old=manifest['validation_selected_summary']
    frozen_old={r['sample_id']:r for r in __import__('research.sprint4.error_analysis',fromlist=['load_csv']).load_csv(Path(s03)/'asag_s03_test_predictions.csv') if r['selected_on_validation'].lower()=='true'}
    # Validation-selected method for each question, defined by original S03 metadata.
    selection={p['prompt_id']:p['selected_on_validation'] for p in manifest['per_prompt']}
    chosen=[(ids[sid]['human_score'], pred[selection[ids[sid]['prompt_id']]]) for sid,pred in test.items()]
    chosen_scores=scores([g for g,p in chosen],[p for g,p in chosen])
    if not math.isclose(chosen_scores['mae'],old['micro_test_mae'],abs_tol=1e-5):
        raise ValueError('S03 chosen method summary differs on reproduced test')
    for sid,p in test.items():
        selected_name=selection[ids[sid]['prompt_id']]
        if p[selected_name]!=int(frozen_old[sid]['predicted_score']):
            raise ValueError('S03 validation method selected mismatch '+sid)
    audited={}
    for method in METHODS:
        g=[ids[sid]['human_score'] for sid in test]
        p=[row[method] for row in test.values()]
        audited[method]=scores(g,p)
    # Apply research rule only if it passed validation; do not re-tune on test.
    test_gate=[]
    if selected:
        for sid,predictions in test.items():
            votes=list(predictions.values())
            if checks[selected](votes):
                pred=Counter(votes).most_common(1)[0][0]
                test_gate.append({'sid':sid,'pred':pred,'gold':ids[sid]['human_score']})
    total_test=len(test)
    gate={'status':'VALIDATION_RULE_PASSED_RESEARCH_ONLY' if selected else 'DISABLED_NO_VALIDATED_RULE',
          'selected_on_validation':selected,
          'test_n':total_test,'test_accepted':len(test_gate),'test_review_required':total_test-len(test_gate),
          'test_coverage':round(len(test_gate)/total_test,5),
          'test_accepted_errors':sum(x['pred']!=x['gold'] for x in test_gate),
          'test_accepted_accuracy':round(sum(x['pred']==x['gold'] for x in test_gate)/len(test_gate),5) if test_gate else None,
          'production_approval_enabled':False}
    # Detailed error category breakdown for validation-selected S03 method, no answers.
    by_question=defaultdict(list); by_gold=defaultdict(list)
    confusion=confusion_matrix([g for g,p in chosen],[p for g,p in chosen],labels=[0,1,2]).tolist()
    for sid,row in test.items():
        gold=ids[sid]['human_score'];pred=row[selection[ids[sid]['prompt_id']]]
        by_question[ids[sid]['prompt_id']].append((gold,pred))
        by_gold[str(gold)].append((gold,pred))
    per_question={q:{'n':len(arr),'errors':sum(g!=p for g,p in arr),
                     'mae':round(sum(abs(g-p) for g,p in arr)/len(arr),5),
                     'full_credit_overgrading':sum(p==2 and g<2 for g,p in arr)}
                  for q,arr in sorted(by_question.items(),key=lambda e:int(e[0]))}
    score_breakdown={k:{'n':len(v),'errors':sum(g!=p for g,p in v)} for k,v in sorted(by_gold.items())}
    report={
        'status':'EXECUTED_FROZEN_ASAG_LIGHTWEIGHT_AUDIT_SPRINT05',
        'generated_utc':datetime.now(timezone.utc).isoformat(),
        'source_sha256':manifest['dataset']['source_file_sha256'],
        'split_seed':manifest['seed'],'test_n':total_test,'validation_n':len(val),
        'frozen_test_predictions_reproduced':True,
        'method_test_scores':audited,'s03_validation_selected_test_scores':chosen_scores,
        's03_validation_selected_confusion':confusion,
        'per_question_selected':per_question,'by_human_score':score_breakdown,
        'research_gate_validation_candidates':candidate_validation,
        'research_gate':gate,
        'limitations':['Only 607 nonblank ASAG typed long answers; no real 1-3 word handwriting data',
                       'ASAG has only overall 0/1/2 human scores, not approved per-question rubrics',
                       'No transformer models or NLI weights executed in Sprint05 offline audit',
                       'Agreeing models may share the same error; no causal evidence of contradiction correctness',
                       'This ASAG test set has been previously inspected in earlier sprints: do NOT treat it as a fresh independent final test',
                       'Human review and a new untouched holdout required for safety validation',
                       'No score auto-publish or TA approval bypass implemented.'],
    }
    out=Path(out);out.mkdir(parents=True,exist_ok=True)
    (out/'s05_reproducibility_and_gate.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    return report


def main():
    p=argparse.ArgumentParser();p.add_argument('--output',type=Path,default=OUT)
    args=p.parse_args();r=run(args.output)
    print('SUCCESS. Reproduced historical Sprint03 test results. Test n=',r['test_n'])
    print('Validation selected MAE:',r['s03_validation_selected_test_scores']['mae'])
    print('Research gate:',r['research_gate']['status'])
    print('Results:',args.output/'s05_reproducibility_and_gate.json')

if __name__=='__main__': main()
