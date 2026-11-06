"""Auditable, PAIRWISE model diagnostics. Does not train or run OCR models.

Input is the LOCAL_ONLY CSV emitted by the real-model benchmark. Never treat
synthetic/mock results as scientific evidence. Avoid running on frozen test for
model selection or changing the deployed pipeline after seeing test errors.
"""
from __future__ import annotations
import argparse,csv,json,hashlib
from collections import defaultdict
from pathlib import Path
from research.sprint6.benchmark import PIPELINES, corpus_scores


def analyze(predictions:list[dict],metrics:dict, worst_n:int=20) -> dict:
    if metrics.get('status')!='REAL_OCR_MODELS_EXECUTED' or not metrics.get('model_executed'):
        raise ValueError('Scientific error analysis requires REAL OCR inference metadata, not mock scores')
    if metrics.get('partial_run'):
        raise ValueError('A partial diagnostic cannot be described as a full evaluation')
    if metrics.get('split')!='validation':
        raise ValueError('Use validation only for choosing/tuning; do not mine the frozen test set')
    names=sorted(metrics.get('pipeline_scores',{}))
    if set(names)!=set(PIPELINES):
        raise ValueError('All four pre-registered pipelines required for a four-way comparison')
    groups=defaultdict(dict)
    for r in predictions:
        name=r.get('pipeline');sid=r.get('sample_id')
        if name not in names or not sid or sid in groups[name]:
            raise ValueError('Unknown pipeline / missing or duplicate line identifier')
        if not r.get('writer_code') or not r.get('ground_truth','').strip():
            raise ValueError('Missing writer or reference transcription')
        groups[name][sid]=r
    ids=set(groups[names[0]])
    if not ids:raise ValueError('Empty prediction file')
    if metrics.get('n_unique_lines') is not None and metrics['n_unique_lines']!=len(ids):
        raise ValueError('Prediction rows disagree with metrics unique-line count')
    if metrics.get('line_ids_sha256') is not None:
        line_hash=hashlib.sha256('\n'.join(sorted(ids)).encode()).hexdigest()
        if metrics['line_ids_sha256']!=line_hash:
            raise ValueError('Predictions do not match hashed validation line IDs')
    for name in names:
        if set(groups[name])!=ids:raise ValueError('Paired comparison requires exactly the same sample_ids')
    for sid in ids:
        examples=[groups[name][sid] for name in names]
        if len({(r['ground_truth'],r['writer_code'],r.get('split','')) for r in examples})!=1:
            raise ValueError('Ground truth/writers inconsistent for paired sample '+sid)
        if examples[0].get('split')!='validation':raise ValueError('Expected validation predictions only')
    by_writer={}
    for name in names:
        writers=defaultdict(list)
        for r in groups[name].values():writers[r['writer_code']].append(r)
        by_writer[name]={writer:corpus_scores(batch) for writer,batch in sorted(writers.items())}
    per_sample=[]
    for sid in sorted(ids):
        err={}
        for name in names:
            r=groups[name][sid]
            err[name]=corpus_scores([r])
        per_sample.append({'sample_id':sid,'writer_code':groups[names[0]][sid]['writer_code'],
                           'reference_chars':len(groups[names[0]][sid]['ground_truth']),
                           'errors_by_pipeline':{n:{'char_errors':err[n]['char_errors'],
                                                    'word_errors':err[n]['word_errors']} for n in names},
                           'ocr_text':{n:groups[n][sid]['prediction'] for n in names},
                           'reference_text':groups[names[0]][sid]['ground_truth']})
    sorted_worst={name:sorted(per_sample,key=lambda r:(-r['errors_by_pipeline'][name]['char_errors'],r['sample_id']))[:worst_n]
                  for name in names}
    base='E01_base_rgb'
    delta={name:{'delta_cer_vs_E01':round(metrics['pipeline_scores'][name]['cer']-metrics['pipeline_scores'][base]['cer'],6),
                 'delta_wer_vs_E01':round(metrics['pipeline_scores'][name]['wer']-metrics['pipeline_scores'][base]['wer'],6)}
           for name in names}
    return {'status':'ANALYSIS_OF_RECORDED_REAL_VALIDATION_PREDICTIONS',
        'split':'validation','line_count':len(ids),'writer_count':len(by_writer[names[0]]),
        'metric_scope':'Corpus micro CER/WER; per-writer micro metrics; paired deltas vs E01',
        'pipeline_scores':metrics['pipeline_scores'],'paired_deltas':delta,
        'by_writer':by_writer,'worst_lines_LOCAL_ONLY':sorted_worst,
        'notice':'Negative delta is better. These OCR results are in-domain IAM, not representative of novel exam sheets. Do not select by frozen test.'}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--predictions',type=Path,default=Path('research/sprint6/results/validation/validation_predictions_LOCAL_ONLY.csv'))
    p.add_argument('--metrics',type=Path,default=Path('research/sprint6/results/validation/validation_metrics.json'))
    p.add_argument('--out',type=Path,default=Path('research/sprint6/results/validation/validation_error_analysis_LOCAL_ONLY.json'))
    a=p.parse_args()
    with a.predictions.open(encoding='utf-8-sig',newline='') as f: records=list(csv.DictReader(f))
    report=analyze(records,json.loads(a.metrics.read_text(encoding='utf-8')))
    a.out.parent.mkdir(exist_ok=True,parents=True)
    a.out.write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Analyzed REAL OCR validation outputs:',report['line_count'],'lines,',report['writer_count'],'writers')
    for name,score in sorted(report['pipeline_scores'].items()):
        print(f"{name:25s} CER={score['cer']:.4f} WER={score['wer']:.4f}")
    print('LOCAL_ONLY',a.out)
if __name__=='__main__':main()
