"""Honest, independent train/validation/test TF-IDF baselines on human-scored ASAP-SAS.
Not the archived project's historical methods: separate new experiment.
No trained model or Kaggle data is shipped. Requires scikit-learn.
"""
import argparse,csv,json,statistics
from pathlib import Path
from collections import defaultdict

def evaluate(input_csv:Path,output_json:Path):
    try:
        import numpy as np
        from sklearn.feature_extraction.text import TfidfVectorizer
        from sklearn.pipeline import make_pipeline
        from sklearn.linear_model import Ridge
        from sklearn.dummy import DummyRegressor
        from sklearn.metrics import mean_absolute_error,cohen_kappa_score
    except ImportError as exc:raise RuntimeError('Install scikit-learn: python -m pip install -r research/sprint1/requirements.txt') from exc
    with input_csv.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    if not rows:raise ValueError('No prepared rows')
    required={'sample_id','prompt_id','answer_text','human_score','split'}
    if not required.issubset(rows[0]):raise ValueError(f'Missing columns {required-set(rows[0])}')
    by_prompt=defaultdict(list)
    for r in rows:
        if r['split'] not in ('train','validation','test'):raise ValueError('Unexpected split')
        by_prompt[r['prompt_id']].append(r)
    report=[]
    def scoring(y_true,pred,scale):
        pred=np.clip(np.rint(pred),scale[0],scale[1]).astype(int)
        y=np.asarray(y_true).astype(int)
        labels=list(range(scale[0],scale[1]+1))
        return {'mae':round(float(mean_absolute_error(y,pred)),5),
                'qwk':round(float(cohen_kappa_score(y,pred,labels=labels,weights='quadratic')),5)
                  if len(set(y.tolist()+pred.tolist()))>1 else None,
                'within_one':round(float(np.mean(np.abs(y-pred)<=1)),5)}
    for prompt,items in sorted(by_prompt.items()):
        sets={s:[r for r in items if r['split']==s] for s in ('train','validation','test')}
        if min(len(arr) for arr in sets.values())<2:raise ValueError('Not enough rows in a split for prompt '+prompt)
        scale=(int(min(float(r['human_score']) for r in sets['train'])),int(max(float(r['human_score']) for r in sets['train'])))
        if scale[0]==scale[1]:raise ValueError('Only one score in training split for prompt '+prompt)
        def xs(s):return [r['answer_text'] for r in sets[s]]
        def ys(s):return [float(r['human_score']) for r in sets[s]]
        candidates={
           'mean_baseline':DummyRegressor(strategy='mean'),
           'tfidf_word_ridge':make_pipeline(TfidfVectorizer(analyzer='word',ngram_range=(1,2),min_df=1),Ridge(alpha=2.0)),
           'tfidf_char_ridge':make_pipeline(TfidfVectorizer(analyzer='char',ngram_range=(2,5),min_df=1),Ridge(alpha=2.0)),
        }
        candidate_results={}
        for label,model in candidates.items():
            model.fit(xs('train'),ys('train')) if label!='mean_baseline' else model.fit([[0]]*len(xs('train')),ys('train'))
            val=model.predict(xs('validation') if label!='mean_baseline' else [[0]]*len(xs('validation')))
            candidate_results[label]={'validation':scoring(ys('validation'),val,scale),'model':model}
        # Val chooses model. Test read just once for selected model.
        selected=min(candidate_results,key=lambda k:candidate_results[k]['validation']['mae'])
        best=candidate_results[selected]['model']
        predictions=best.predict(xs('test') if selected!='mean_baseline' else [[0]]*len(xs('test')))
        report.append({'prompt_id':prompt,'n':{k:len(v) for k,v in sets.items()},'train_score_range':list(scale),
             'selected_by_validation':selected,'validation_candidates':{k:v['validation'] for k,v in candidate_results.items()},
             'heldout_test_selected_model':scoring(ys('test'),predictions,scale),
             'average_answer_words':round(statistics.mean(int(r['word_count']) for r in items),2)
                  if all('word_count' in r for r in items) else None})
    outcome={'status':'EXECUTED_ON_PROVIDED_DATA_VERIFY_DATA_PROVENANCE','dataset':'KAGGLE_ASAP_SAS',
      'test_evaluation_policy':'Validation selects baseline per prompt. Test evaluated on selected baseline only.',
      'warning':'ASAP-SAS has ~50 word answers on average; this is NOT validation for 1-3 word MENTRIX questions.',
      'results_by_prompt':report}
    output_json.parent.mkdir(exist_ok=True,parents=True)
    output_json.write_text(json.dumps(outcome,indent=2,ensure_ascii=False,allow_nan=False),encoding='utf-8')
    print('Wrote',output_json)
    for r in report:print('Prompt',r['prompt_id'],'choice',r['selected_by_validation'],'test',r['heldout_test_selected_model'])
    return outcome

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',type=Path,required=True)
    p.add_argument('--output',type=Path,default=Path(__file__).parent/'results'/'asap_baseline_metrics.json')
    args=p.parse_args();evaluate(args.input,args.output)
if __name__=='__main__':main()
