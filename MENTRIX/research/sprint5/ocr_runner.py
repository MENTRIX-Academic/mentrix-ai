"""Run real TrOCR ORIGINAL RGB baseline on human-verified handwritten images.
No images or ground truths are included in the distributed research bundle.
`--validate-only` checks the local manifest without downloading model weights.
"""
from __future__ import annotations
import argparse, csv, json
from collections import defaultdict
from pathlib import Path
from research.sprint1.evaluate_ocr import evaluate

FIELDS={'sample_id','writer_code','split','image_path','ground_truth','verified_by'}


def validate_manifest(manifest:Path, images_dir:Path, split='test'):
    with manifest.open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f)
        if not FIELDS.issubset(reader.fieldnames or []):
            raise ValueError('Manifest columns missing: '+', '.join(sorted(FIELDS-set(reader.fieldnames or []))))
        rows=list(reader)
    if not rows:raise ValueError('Manifest has no verified image rows: no OCR result is available yet.')
    writers=defaultdict(set);samples=set();checked=[]
    images_dir=images_dir.resolve()
    for r in rows:
        sid=r['sample_id'].strip(); writer=r['writer_code'].strip();part=r['split'].strip()
        if not sid or sid in samples:raise ValueError('Missing or duplicated sample_id: '+sid)
        samples.add(sid)
        if not writer or part not in {'train','validation','test'}:raise ValueError('Invalid writer or split: '+sid)
        writers[writer].add(part)
        path=Path(r['image_path'])
        if path.is_absolute():
            # Restrict to a known local research image directory
            raise ValueError('Only relative image paths inside --images-dir are permitted: '+sid)
        image_path=(images_dir/path).resolve()
        if images_dir not in image_path.parents or not image_path.is_file():
            raise ValueError('Missing image or unsafe path: '+str(path))
        if part==split:
            if not r['ground_truth'].strip() or not r['verified_by'].strip():
                raise ValueError('A human-verified independent GT + verified_by is required: '+sid)
            checked.append({**r,'image_file':image_path})
    if any(len(parts)>1 for parts in writers.values()):
        raise ValueError('Writer leakage: a writer occurs in more than one split')
    if not checked:raise ValueError('No independently verified images in requested split: '+split)
    return checked


def run(manifest:Path,images_dir:Path,out:Path,split='test',model_id='microsoft/trocr-base-handwritten', validate_only=False):
    rows=validate_manifest(manifest,images_dir,split=split)
    if validate_only:
        return {'status':'MANIFEST_VALIDATED_ONLY','test_samples_ready':len(rows),'model_executed':False}
    try:
        import torch
        from PIL import Image
        from transformers import TrOCRProcessor, VisionEncoderDecoderModel
    except ImportError as exc:
        raise RuntimeError('Install packages with INSTALL_SPRINT05_OCR_MODELS_ONCE.bat first') from exc
    device='cuda' if torch.cuda.is_available() else 'cpu'
    processor=TrOCRProcessor.from_pretrained(model_id,trust_remote_code=False)
    model=VisionEncoderDecoderModel.from_pretrained(model_id,trust_remote_code=False).to(device)
    model.eval()
    output_rows=[]
    with torch.inference_mode():
        for ix,r in enumerate(rows,1):
            # E01 Original RGB baseline. No denoising, rotations or threshold enhancements.
            with Image.open(r['image_file']) as original:rgb=original.convert('RGB')
            pixels=processor(rgb,return_tensors='pt').pixel_values.to(device)
            tokens=model.generate(pixels,max_new_tokens=128)
            prediction=processor.batch_decode(tokens,skip_special_tokens=True)[0]
            output_rows.append({'sample_id':r['sample_id'],'writer_code':r['writer_code'],
                                'split':r['split'],'ground_truth':r['ground_truth'],
                                'prediction':prediction})
            print(f'OCR processed {ix}/{len(rows)}: {r["sample_id"]}',flush=True)
    out.mkdir(parents=True,exist_ok=True)
    private_path=out/'s05_private_ocr_predictions_LOCAL_ONLY.csv'
    with private_path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=['sample_id','writer_code','split','ground_truth','prediction'])
        w.writeheader();w.writerows(output_rows)
    public_report=evaluate(private_path,out/'s05_ocr_metrics.json',split)
    public_report.update({'model_id':model_id,'input_mode':'Original RGB E01',
                          'device':device,'model_executed':True,'published_grade_accuracy':False})
    (out/'s05_ocr_metrics.json').write_text(json.dumps(public_report,indent=2,ensure_ascii=False)+'\n',encoding='utf-8')
    return public_report


def main():
    p=argparse.ArgumentParser()
    p.add_argument('--manifest',type=Path,default=Path('research/sprint5/data/ocr_manifest.csv'))
    p.add_argument('--images-dir',type=Path,default=Path('research/sprint5/data/images'))
    p.add_argument('--out',type=Path,default=Path('research/sprint5/local_ocr_results'))
    p.add_argument('--split',choices=['validation','test'],default='test')
    p.add_argument('--model-id',default='microsoft/trocr-base-handwritten')
    p.add_argument('--validate-only',action='store_true')
    a=p.parse_args()
    r=run(a.manifest,a.images_dir,a.out,a.split,a.model_id,a.validate_only)
    print('STATUS:',r['status'] if a.validate_only else 'REAL_OCR_BENCHMARK_EXECUTED')
    if not a.validate_only:print('CER/WER:',r['metrics'])

if __name__=='__main__':main()
