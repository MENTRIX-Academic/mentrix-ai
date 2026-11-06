"""Sprint04: run real MiniLM and optional NLI against frozen Sprint03 ASAG splits.

NO historical metric overwrite. NO rubric claim: source has only an overall 0/1/2 grade.
Actual Hugging Face checkpoints are fetched at runtime; importing this module does
not download models. Runs are deliberately not simulated with TF-IDF substitutes.
"""
from __future__ import annotations
import argparse, csv, json, time, math
from collections import defaultdict
from pathlib import Path
import numpy as np
from scipy.special import softmax
from sklearn.linear_model import Ridge
from sklearn.neighbors import KNeighborsRegressor
from research.sprint4.error_analysis import (ROOT, S03, S04, DATA, frozen_inputs, scores)
from research.sprint3.asag_benchmark import ref_jaccard

DEFAULT_EMBEDDER='sentence-transformers/all-MiniLM-L6-v2'
DEFAULT_NLI='cross-encoder/nli-MiniLM2-L6-H768'
CATEGORIES=['contradiction','entailment','neutral']


def reference_features(rows, vectors, reference_vectors, nli=None):
    """Return named features per record, all computed independently of labels."""
    similarities=np.array([float(np.dot(vectors[r['sample_id']], reference_vectors[r['prompt_id']])) for r in rows])
    jaccard=np.array([ref_jaccard(r['answer_text'],r['reference_text']) for r in rows])
    features={'minilm_reference_cosine':similarities.reshape(-1,1),
              'minilm_reference_jaccard':np.column_stack([similarities,jaccard])}
    if nli is not None:
        prob=np.array([nli[r['sample_id']] for r in rows])
        if prob.shape!=(len(rows),3): raise ValueError('NLI output must be [n,3] contradiction/entailment/neutral')
        features['nli_reference_probabilities']=prob
        features['minilm_nli_reference_features']=np.column_stack([similarities,jaccard,prob])
    return features


def get_nli_label_mapping(model):
    """Respect meaningful id2label if present; otherwise official checkpoint documented order."""
    config=getattr(getattr(model,'model',None),'config',None)
    ids=getattr(config,'id2label',None)
    if isinstance(ids,dict):
        labels=[str(ids.get(i,ids.get(str(i),''))).lower() for i in range(3)]
        if all(any(name in label for name in CATEGORIES) for label in labels):
            permutation=[labels.index(next(label for label in labels if name in label)) for name in CATEGORIES]
            return permutation,'checkpoint_id2label'
    return [0,1,2],'official_sentence_transformers_nli_documented_label_order'


def calculate_predictions(train, target, features_train, features_target, method):
    gold=np.asarray([r['human_score'] for r in train],dtype=float)
    if method=='minilm_answer_knn':
        k=min(3,len(train))
        model=KNeighborsRegressor(n_neighbors=k, weights='distance',metric='euclidean')
    else:
        model=Ridge(alpha=1.0)
    model.fit(features_train, gold)
    return model.predict(features_target)


def wilson_lower(success,n,z=1.96):
    if n<=0:return 0.0
    p=success/n; den=1+z*z/n
    return (p+z*z/(2*n)-z*math.sqrt(p*(1-p)/n+z*z/(4*n*n)))/den


def choose_review_threshold(validation_raw, validation_true, min_n=40, target_lower=0.95):
    """Conservative validation-only research gate. Never publishes grades.

    Integer boundary proximity is not a calibrated confidence probability; this
    only checks an empirical candidate policy, and can reject all cases.
    """
    raw=np.asarray(validation_raw,dtype=float); truth=np.asarray(validation_true,dtype=int)
    pred=np.clip(np.rint(raw),0,2).astype(int)
    confidence=1-np.abs(raw-pred)
    choices=[]
    for t in (0.995,0.99,0.98,0.97,0.95,0.92,0.90,0.85,0.80,0.75,0.70,0.60,0.50):
        sel=confidence>=t; n=int(sel.sum())
        correct=int((pred[sel]==truth[sel]).sum())
        if n>=min_n and wilson_lower(correct,n)>=target_lower:
            choices.append((n,t,correct,wilson_lower(correct,n)))
    if not choices:
        return {'status':'NO_VALIDATED_AUTO_APPROVAL_THRESHOLD','threshold':None,
                'validation_n':len(raw),'min_n':min_n,'target_wilson_95_lower':target_lower}
    n,thr,k,lower=max(choices,key=lambda x:(x[0],x[1]))
    return {'status':'RESEARCH_CANDIDATE_NOT_FOR_DEPLOYMENT','threshold':thr,
            'validation_accepted':n,'validation_correct':k,
            'validation_wilson_lower':round(lower,5),'validation_n':len(raw),
            'min_n':min_n,'target_wilson_95_lower':target_lower}


def run(data=DATA, s03=S03, output=S04, skip_nli=False, embedder_name=DEFAULT_EMBEDDER,
        nli_name=DEFAULT_NLI, batch_size=8):
    # Verify frozen dataset + split + original prediction manifest, before any downloads.
    manifest, ids, parts, old_predictions, test_ids=frozen_inputs(s03,data)
    rows=[ids[k] for k in sorted(parts,key=int)]
    try:
        from sentence_transformers import SentenceTransformer, CrossEncoder
    except ImportError as e:
        raise RuntimeError('Missing sentence-transformers. Run INSTALL_SPRINT04_MODELS_ONCE.bat') from e
    print('Loading real MiniLM:',embedder_name,flush=True)
    t0=time.monotonic()
    model=SentenceTransformer(embedder_name)
    texts=list(dict.fromkeys([r['answer_text'] for r in rows]+[r['reference_text'] for r in rows]))
    encoded=model.encode(texts,batch_size=max(1,batch_size),normalize_embeddings=True,show_progress_bar=True)
    embeddings=dict(zip(texts,np.asarray(encoded)))
    vec={r['sample_id']:embeddings[r['answer_text']] for r in rows}
    ref_vec={r['prompt_id']:embeddings[r['reference_text']] for r in rows}
    nli=None; mapping_source=None
    if not skip_nli:
        print('Loading real NLI model:',nli_name,flush=True)
        detector=CrossEncoder(nli_name)
        raw=np.asarray(detector.predict([(r['reference_text'],r['answer_text']) for r in rows],
                                        batch_size=max(1,batch_size),show_progress_bar=True))
        if raw.ndim!=2 or raw.shape[1]!=3:
            raise ValueError(f'NLI expected 3-class scores, received shape {raw.shape}')
        order,mapping_source=get_nli_label_mapping(detector)
        probs=raw[:,order]
        if not (np.allclose(np.sum(probs,axis=1),1,rtol=1e-3,atol=1e-3)
                and np.all((probs>=0)&(probs<=1))):
            probs=softmax(probs,axis=1)
        nli={r['sample_id']:probs[i] for i,r in enumerate(rows)}
    per_prompt=defaultdict(list)
    for r in rows:per_prompt[r['prompt_id']].append(r)
    method_raw_val=defaultdict(list); method_gold_val=defaultdict(list)
    method_predictions=defaultdict(list)
    pred_rows=[]; selection_by_prompt={}
    for q,qr in sorted(per_prompt.items(),key=lambda x:int(x[0])):
        tr=[r for r in qr if parts[r['sample_id']]=='train']
        va=[r for r in qr if parts[r['sample_id']]=='validation']
        te=[r for r in qr if parts[r['sample_id']]=='test']
        for n,seq in [('train',tr),('validation',va),('test',te)]:
            if not seq: raise ValueError('Empty frozen split '+q+' '+n)
        feats={name:reference_features(group,vec,ref_vec,nli) for name,group in [('train',tr),('val',va),('test',te)]}
        methods=list(feats['train'])+['minilm_answer_knn']
        results={}
        for method in methods:
            if method=='minilm_answer_knn':
                xt=np.stack([vec[r['sample_id']] for r in tr]); xv=np.stack([vec[r['sample_id']] for r in va]); xe=np.stack([vec[r['sample_id']] for r in te])
            else:
                xt=feats['train'][method];xv=feats['val'][method];xe=feats['test'][method]
            vr=calculate_predictions(tr,va,xt,xv,method)
            er=calculate_predictions(tr,te,xt,xe,method)
            vp=np.clip(np.rint(vr),0,2).astype(int)
            ep=np.clip(np.rint(er),0,2).astype(int)
            vm=scores([r['human_score'] for r in va],vp)
            results[method]={'val_mae':vm['mae'],'val_raw_mae':float(np.mean(np.abs(vr-np.asarray([r['human_score'] for r in va])))),
                             'val_raw':vr,'test_raw':er,'test_pred':ep}
            for r,raw in zip(va,vr):
                method_raw_val[method].append(float(raw));method_gold_val[method].append(r['human_score'])
            for r,raw,pred in zip(te,er,ep):
                method_predictions[method].append((r['human_score'],int(pred)))
                pred_rows.append({'prompt_id':q,'sample_id':r['sample_id'],'method':method,
                                  'gold_score':r['human_score'],'predicted_score':int(pred),
                                  'raw_score':round(float(raw),6),'absolute_error':abs(r['human_score']-int(pred)),
                                  'selected_on_validation':False})
        chosen=min(results,key=lambda m:(results[m]['val_mae'],results[m]['val_raw_mae'],m))
        selection_by_prompt[q]=chosen
        for r in pred_rows:
            if r['prompt_id']==q and r['method']==chosen: r['selected_on_validation']=True
    method_summary={method:scores([p[0] for p in preds],[p[1] for p in preds])
                    for method,preds in method_predictions.items()}
    selected=[r for r in pred_rows if r['selected_on_validation']]
    selected_summary=scores([r['gold_score'] for r in selected],[r['predicted_score'] for r in selected])
    # Calibration is for R&D only; threshold is selected using VALIDATION ONLY.
    # Compute per-method threshold; test is inspected only after thresholds are frozen.
    review_policy={}
    for method in method_summary:
        v=choose_review_threshold(method_raw_val[method],method_gold_val[method])
        ts=[r for r in pred_rows if r['method']==method]
        if v['threshold'] is None:
            v['test_accepted']=0;v['test_coverage']=0.0;v['test_accepted_errors']=None
        else:
            accept=[r for r in ts if 1-abs(r['raw_score']-r['predicted_score'])>=v['threshold']]
            v['test_accepted']=len(accept)
            v['test_coverage']=round(len(accept)/len(ts),5)
            v['test_accepted_errors']=sum(r['gold_score']!=r['predicted_score'] for r in accept)
        review_policy[method]=v
    old_summary={k:{'n':v['heldout_n'],'mae':v['micro_test_mae'],
                    'qwk':v['pooled_test_qwk'],'exact':v['pooled_test_exact_match']}
                 for k,v in manifest['method_summary'].items()}
    output=Path(output);output.mkdir(parents=True,exist_ok=True)
    with (output/'s04_transformer_test_predictions.csv').open('w',encoding='utf-8-sig',newline='') as f:
        cols=['prompt_id','sample_id','method','gold_score','predicted_score','raw_score','absolute_error','selected_on_validation']
        w=csv.DictWriter(f,fieldnames=cols);w.writeheader();w.writerows(pred_rows)
    report={'status':'ACTUALLY_EXECUTED_TRANSFORMER_MODELS_ON_FROZEN_SPRINT03_SPLIT',
            'source_dataset_sha256':manifest['dataset']['source_file_sha256'],
            'source_s03_seed':manifest['seed'],
            'model_ids':{'minilm':embedder_name,'nli':None if skip_nli else nli_name},
            'nli_label_mapping':mapping_source,'seconds_elapsed':round(time.monotonic()-t0,2),
            'methods':method_summary,'old_s03_baselines_same_test':old_summary,
            'validation_selected':selected_summary,'selection_by_question':selection_by_prompt,
            'research_only_review_policy':review_policy,
            'limitations':['ASAG grades 0/1/2 from one rater; no approved per-criterion rubric was provided',
                           'Methods labeled reference_features are NOT Rubric+NLI; no real rubric method is evaluated',
                           'NLI detects general textual inference, not guaranteed factual grading correctness',
                           'No OCR and no 1–3-word handwriting evaluation',
                           'No automatic student grade publication is authorized',
                           'Validation used for per-question method selection and research threshold only; TEST is evaluation only']}
    (output/'s04_transformer_results.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    print('SUCCESS: actual models executed and results saved:',output/'s04_transformer_results.json')
    return report


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--skip-nli',action='store_true',help='Only MiniLM: faster for older CPU laptops')
    p.add_argument('--batch-size',type=int,default=8)
    p.add_argument('--minilm-model',default=DEFAULT_EMBEDDER)
    p.add_argument('--nli-model',default=DEFAULT_NLI)
    args=p.parse_args()
    result=run(skip_nli=args.skip_nli,embedder_name=args.minilm_model,
               nli_name=args.nli_model,batch_size=args.batch_size)
    print('Scores on test (0..2)')
    for m,s in sorted(result['methods'].items(),key=lambda kv:kv[1]['mae']):
        print(f'{m:40s} MAE={s["mae"]:.4f}, QWK={s["qwk"]}, exact={s["exact"]:.2%}')
    print('Rubric + NLI: NOT RUN — approved per-question rubric unavailable.')

if __name__=='__main__':main()
