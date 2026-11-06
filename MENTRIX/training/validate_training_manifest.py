"""Validate user-authorized training manifest before GPU fine-tuning. No download or training."""
import csv,sys
from pathlib import Path

def validate(path):
    root=Path(path).resolve().parent;seen=set();writers={};n=0
    with open(path,encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f)
        if not {'image_path','text','writer_code','split'}.issubset(reader.fieldnames or []):raise ValueError('Required image_path,text,writer_code,split')
        for row in reader:
            n+=1
            if row['split'] not in ('train','validation','test'):raise ValueError(f'Row {n}: invalid split')
            if not row['writer_code'].strip() or not row['text'].strip():raise ValueError(f'Row {n}: writer / text missing')
            filename=(root/row['image_path']).resolve()
            if not filename.is_relative_to(root) or not filename.is_file():raise ValueError(f'Row {n}: unsafe or missing image')
            if filename in seen:raise ValueError(f'Row {n}: duplicate image path')
            seen.add(filename)
            writers.setdefault(row['writer_code'],set()).add(row['split'])
    leakage={k:list(v) for k,v in writers.items() if len(v)>1}
    if leakage:raise ValueError(f'Writer leakage across splits: {leakage}')
    if n==0:raise ValueError('Empty manifest')
    print(f'PASS: {n} labelled line images, {len(writers)} writer codes; no writer overlap')

if __name__=='__main__':
    if len(sys.argv)!=2:sys.exit('Usage: python validate_training_manifest.py manifest.csv')
    validate(sys.argv[1])
