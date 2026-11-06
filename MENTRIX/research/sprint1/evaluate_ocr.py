"""Evaluate OCR predictions against independently verified transcriptions (CER/WER).
CSV columns: sample_id,writer_code,split,ground_truth,prediction
Can evaluate test split only by default. Fails when no test ground truth is supplied.
"""
import argparse,csv,json,re
from pathlib import Path
from collections import defaultdict

def edit_distance(a,b):
    prev=list(range(len(b)+1))
    for i,ch in enumerate(a,1):
        nxt=[i]
        for j,token in enumerate(b,1):
            nxt.append(min(prev[j]+1,nxt[-1]+1,prev[j-1]+(ch!=token)))
        prev=nxt
    return prev[-1]

def evaluate(path:Path,out:Path,split:str='test'):
    with path.open(encoding='utf-8-sig',newline='') as f:rows=list(csv.DictReader(f))
    fields={'sample_id','writer_code','split','ground_truth','prediction'}
    if not rows:raise ValueError('Input empty')
    if not fields.issubset(rows[0]):raise ValueError('CSV columns missing: '+','.join(sorted(fields-set(rows[0]))))
    writers=defaultdict(set);seen=set();review=[]
    for r in rows:
        if r['split'] not in ('train','validation','test'):raise ValueError('Invalid split')
        if not r['writer_code'].strip():raise ValueError('Unknown writer_code; avoid writer leakage')
        writers[r['writer_code']].add(r['split'])
        if not r['sample_id'].strip() or r['sample_id'] in seen:raise ValueError('Missing/duplicate sample_id')
        seen.add(r['sample_id'])
        if r['split']==split:
            if not r['ground_truth'].strip():raise ValueError('Missing independently verified ground_truth')
            gt=' '.join(r['ground_truth'].split());pr=' '.join((r['prediction'] or '').split())
            review.append({'sample_id':r['sample_id'],'writer_code':r['writer_code'],
                'c_errors':edit_distance(gt,pr),'c_total':len(gt),
                'w_errors':edit_distance(gt.split(),pr.split()),'w_total':len(gt.split())})
    leaked={k:list(v) for k,v in writers.items() if len(v)>1}
    if leaked:raise ValueError('Writer leakage detected across splits: '+str(leaked))
    if not review:raise ValueError(f'No rows with split={split}; NO metric is available.')
    total_chars=sum(x['c_total'] for x in review);total_words=sum(x['w_total'] for x in review)
    bywriter=defaultdict(list)
    for r in review:bywriter[r['writer_code']].append(r)
    def stats(rs):
        return {'samples':len(rs),'cer':round(sum(x['c_errors'] for x in rs)/sum(x['c_total'] for x in rs),5),
                'wer':round(sum(x['w_errors'] for x in rs)/sum(x['w_total'] for x in rs),5)}
    if not total_chars or not total_words:raise ValueError('Missing text references')
    report={'status':'EXECUTED_ON_PROVIDED_HUMAN_VERIFIED_TRANSCRIPTIONS',
      'normalization':'NFKC not applied; collapse whitespace only; case and punctuation are scored',
      'split_evaluated':split,'metrics':stats(review),
      'by_writer':{writer:stats(arr) for writer,arr in sorted(bywriter.items())},
      'worst_samples_by_CER':sorted([dict(sample_id=r['sample_id'],writer_code=r['writer_code'],cer=round(r['c_errors']/r['c_total'],4)) for r in review],key=lambda x:x['cer'],reverse=True)[:20],
      'notes':['CER/WER are transcription quality only, not grading accuracy','Only use truth transcribed independently of OCR; do not treat model predictions as ground truth']}
    out.parent.mkdir(parents=True,exist_ok=True)
    out.write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print('Wrote',out,report['metrics']);return report

def main():
    p=argparse.ArgumentParser();p.add_argument('--input',required=True,type=Path)
    p.add_argument('--split',choices=['validation','test'],default='test')
    p.add_argument('--output',type=Path,default=Path(__file__).parent/'results'/'ocr_metrics.json')
    args=p.parse_args();evaluate(args.input,args.output,args.split)
if __name__=='__main__':main()
