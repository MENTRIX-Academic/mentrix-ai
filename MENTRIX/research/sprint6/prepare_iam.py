"""Convert REGISTERED official IAM line archives, XML writer IDs and official task lists.

No datasets redistributed; rejects absent writer IDs and cross-split writer leakage.
"""
from __future__ import annotations
import argparse, csv, re, xml.etree.ElementTree as ET
from pathlib import Path
from research.sprint6.benchmark import load_manifest

LINE_RE = re.compile(r'^[a-zA-Z0-9][\w-]+$')

def parse_lines_txt(path: Path):
    labels={}
    for s in path.read_text(encoding='latin1').splitlines():
        if not s.strip() or s.startswith('#'): continue
        # IAM lines.txt columns: id status gray-level x y w h tag transcription
        parts=s.strip().split(maxsplit=8)
        if len(parts)<9: continue
        name=parts[0];status=parts[1]
        if status!='ok': continue  # segmentation-error entries are excluded
        labels[name]=parts[8].replace('|',' ').strip()
    if not labels:raise ValueError('No valid IAM lines.txt transcriptions found')
    return labels

def writer_map(xml_dir: Path):
    lookup={}
    for p in xml_dir.rglob('*.xml'):
        root=ET.parse(p).getroot()
        form_id=root.attrib.get('id') or p.stem
        writer=(root.attrib.get('writer-id') or root.attrib.get('writer_id') or '').strip()
        if writer:lookup[form_id]=writer
    if not lookup: raise ValueError('No IAM writer IDs in XML. Writer-independent evaluation cannot proceed.')
    return lookup

def read_ids(path:Path):
    vals=set()
    for line in path.read_text(encoding='utf-8-sig').splitlines():
        s=line.strip()
        if not s or s.startswith('#'):continue
        # Official IAM task files contain line identifiers per line.
        s=s.split()[0]
        if not LINE_RE.fullmatch(s):raise ValueError('Invalid IAM line ID in '+str(path))
        vals.add(s)
    return vals

def build(lines_txt:Path, xml_dir:Path, images_dir:Path, split_files:dict[str,Path],output:Path):
    labels=parse_lines_txt(lines_txt)
    writers=writer_map(xml_dir)
    groups={k:read_ids(v) for k,v in split_files.items()}
    if not groups.get('validation') or not groups.get('test') or not groups.get('train'):
        raise ValueError('Expected non-empty official writer-independent train/validation/test lists')
    all_ids=[]
    for split,ids in groups.items():
        for item in ids:
            if any(item in other for k,other in groups.items() if k!=split):
                raise ValueError('Same IAM line in several splits: '+item)
            all_ids.append((item,split))
    records=[]
    for sid,split in sorted(all_ids):
        if sid not in labels:raise ValueError('Missing label for IAM line '+sid)
        form=sid.rsplit('-',1)[0]
        if form not in writers:raise ValueError('Missing XML writer-id for form '+form)
        subdir=sid[:3]
        candidates=[images_dir/subdir/form/(sid+'.png'), images_dir/(sid+'.png')]
        loc=next((p for p in candidates if p.is_file()),None)
        if loc is None:raise ValueError('Missing IAM line image: '+sid)
        records.append({'sample_id':sid,'writer_code':writers[form],'split':split,
                        'image_path':loc.relative_to(images_dir).as_posix(),
                        'ground_truth':labels[sid],'verified_by':'IAM_OFFICIAL_TRANSCRIPTION'})
    output.parent.mkdir(parents=True,exist_ok=True)
    with output.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['sample_id','writer_code','split','image_path','ground_truth','verified_by'])
        w.writeheader();w.writerows(records)
    load_manifest(output,images_dir)
    return {'count':len(records),'by_split':{k:len(v) for k,v in groups.items()},'writer_count':len(set(r['writer_code'] for r in records))}

def main():
    p=argparse.ArgumentParser()
    p.add_argument('--lines-txt',type=Path,required=True)
    p.add_argument('--xml-dir',type=Path,required=True)
    p.add_argument('--images-dir',type=Path,required=True)
    p.add_argument('--train-ids',type=Path,required=True)
    p.add_argument('--validation-ids',type=Path,required=True)
    p.add_argument('--test-ids',type=Path,required=True)
    p.add_argument('--output',type=Path,default=Path('research/sprint6/data/iam_manifest.csv'))
    a=p.parse_args()
    print(build(a.lines_txt,a.xml_dir,a.images_dir,{'train':a.train_ids,'validation':a.validation_ids,'test':a.test_ids},a.output))
if __name__=='__main__':main()
