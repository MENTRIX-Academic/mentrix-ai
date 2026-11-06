"""Create a reproducible, leakage-aware experiment split from Kaggle ASAP-SAS train.tsv.
No datasets included. Designed for short-answer research (~50 words), NOT 1-3 word validity.
Usage: python research/sprint1/prepare_asap.py --input research/sprint1/data/asap/train.tsv
"""
import argparse
import csv
import hashlib
import random
import re
from pathlib import Path
from collections import defaultdict

FIELDS=['sample_id','prompt_id','answer_text','human_score','word_count','split','source']
def normalized(text):return ' '.join(text.casefold().split())
def groupsplits(groups,seed):
    keys=list(groups)
    # Random seed and stable group keys; duplicates always belong to a single split.
    random.Random(seed).shuffle(keys)
    count=len(keys)
    if count<10:raise ValueError(f'Only {count} unique-answer groups. Need at least 10 per prompt.')
    ntrain=max(1,int(count*.70)); nval=max(1,int(count*.15))
    if ntrain+nval>=count:raise ValueError('Not enough groups for 3 splits')
    return {key:('train' if i<ntrain else 'validation' if i<ntrain+nval else 'test') for i,key in enumerate(keys)}

def prepare(source:Path,out:Path,seed:int=42,max_words:int=0):
    with source.open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f,delimiter='\t')
        # Original Kaggle train.tsv fields: Id, EssaySet, Score1, Score2, EssayText.
        mapping={key.lower().strip():key for key in reader.fieldnames or []}
        required=['id','essayset','score1','essaytext']
        if any(key not in mapping for key in required):
            raise ValueError(f'Invalid ASAP-SAS header, expected {required}. Found: {reader.fieldnames}')
        raw=list(reader)
    if not raw:raise ValueError('Empty TSV')
    prompts=defaultdict(list)
    seenids=set()
    for rownum,row in enumerate(raw,2):
        sample_id=(row[mapping['id']] or '').strip()
        prompt_id=(row[mapping['essayset']] or '').strip()
        answer=(row[mapping['essaytext']] or '').strip()
        score=(row[mapping['score1']] or '').strip()
        if not all((sample_id,prompt_id,answer,score)):
            continue
        if sample_id in seenids:raise ValueError(f'Duplicate Id at source row {rownum}: {sample_id}')
        seenids.add(sample_id)
        # Human ratings can be integers; float preserved for any unusual score scale.
        try:score_value=float(score)
        except ValueError:continue
        if not (float('-inf')<score_value<float('inf')):continue
        word_count=len(answer.split())
        if max_words and word_count>max_words:continue
        prompts[prompt_id].append({'sample_id':sample_id,'prompt_id':prompt_id,'answer_text':answer,
             'human_score':str(score_value),'word_count':word_count,'source':'KAGGLE_ASAP_SAS_TRAIN'})
    if not prompts:raise ValueError('No valid rows after filtering; ASAP-SAS may have few 1-3-word answers.')
    data=[];info=[]
    for prompt,items in sorted(prompts.items(),key=lambda p:p[0]):
        groups=defaultdict(list)
        for item in items:
            digest=hashlib.sha256(normalized(item['answer_text']).encode('utf-8')).hexdigest()
            groups[digest].append(item)
        # Small filtered 1-3 word prompts should be shown as insufficient, not silently included.
        if len(groups)<10:
            raise ValueError(f'Prompt {prompt} has only {len(groups)} distinct answers; cannot make reliable train/val/test.')
        assignment=groupsplits(groups,seed+sum(map(ord,prompt)))
        for group,items_ in groups.items():
            for item in items_:
                data.append(dict(item,split=assignment[group]))
        info.append({'prompt':prompt,'rows':len(items),'unique_responses':len(groups),
                     'splits':{split:sum(r['split']==split for r in data if r['prompt_id']==prompt) for split in ['train','validation','test']}})
    out.parent.mkdir(parents=True,exist_ok=True)
    with out.open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=FIELDS);writer.writeheader();writer.writerows(data)
    print('CREATED',out,'rows',len(data),'prompts',len(info))
    print('NOT an evaluation: only data preparation; no model trained.')
    for obj in info:print(obj)
    return data,info

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--input',required=True,type=Path,help='Unzipped Kaggle ASAP-SAS train.tsv')
    p.add_argument('--output',type=Path,default=Path(__file__).parent/'data'/'asap_prepared.csv')
    p.add_argument('--seed',type=int,default=42)
    p.add_argument('--max-words',type=int,default=0,help='Optional filter. Use 0 for all; <4 for research only, not proof of applicability.')
    args=p.parse_args()
    prepare(args.input,args.output,args.seed,args.max_words)
if __name__=='__main__':main()
