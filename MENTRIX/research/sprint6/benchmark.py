"""MENTRIX Sprint 06: reproducible, paired handwriting-line OCR benchmark.

No model or dataset downloads at import time. Tests may inject a fake recognizer,
but these are engineering checks, NEVER publishable OCR accuracy results.
"""
from __future__ import annotations
import argparse
import csv
import hashlib
import json
import platform
import sys
import time
from collections import defaultdict
from datetime import datetime, timezone
from pathlib import Path
from PIL import Image, ImageOps
from ocr_quality import enhanced_line, padded_line
from research.sprint1.evaluate_ocr import edit_distance

FIELDS = {'sample_id', 'writer_code', 'split', 'image_path', 'ground_truth', 'verified_by'}
PIPELINES = {
    'E01_base_rgb': ('microsoft/trocr-base-handwritten', 'rgb'),
    'E02_base_autocontrast': ('microsoft/trocr-base-handwritten', 'autocontrast'),
    'E03_small_rgb': ('microsoft/trocr-small-handwritten', 'rgb'),
    'E04_base_padded': ('microsoft/trocr-base-handwritten', 'padded'),
}

def preprocess(image: Image.Image, variant: str) -> Image.Image:
    if variant == 'rgb': return image.convert('RGB')
    if variant == 'autocontrast': return enhanced_line(image)
    if variant == 'padded': return padded_line(image)
    raise ValueError('Unknown preprocessing method: ' + variant)

def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open('rb') as f:
        for block in iter(lambda: f.read(1024 * 1024), b''): h.update(block)
    return h.hexdigest()

def load_manifest(manifest: Path, image_root: Path) -> list[dict]:
    with manifest.open(encoding='utf-8-sig', newline='') as f:
        r = csv.DictReader(f)
        if not FIELDS.issubset(r.fieldnames or []):
            raise ValueError('Missing manifest columns: ' + ', '.join(sorted(FIELDS - set(r.fieldnames or []))))
        rows = list(r)
    if not rows: raise ValueError('No IAM/human verified lines provided; cannot calculate CER/WER.')
    image_root = image_root.resolve()
    writers, seen, checked = defaultdict(set), set(), []
    paths_by_split = defaultdict(set)
    for row in rows:
        sid, writer, split = (row[k].strip() for k in ('sample_id', 'writer_code', 'split'))
        if not sid or sid in seen: raise ValueError('Missing/duplicate sample_id: ' + sid)
        if not writer or split not in ('train', 'validation', 'test'):
            raise ValueError('Bad writer_code or split: ' + sid)
        if not row['ground_truth'].strip() or not row['verified_by'].strip():
            raise ValueError('Ground truth and its independent verified_by provenance required: ' + sid)
        relative = Path(row['image_path'])
        p = (image_root / relative).resolve()
        if relative.is_absolute() or image_root not in p.parents or not p.is_file():
            raise ValueError('Image missing or unsafe path for: ' + sid)
        if p.suffix.lower() not in ('.png', '.jpg', '.jpeg', '.webp'):
            raise ValueError('Invalid line image extension: ' + sid)
        seen.add(sid)
        paths_by_split[str(p)].add(split)
        writers[writer].add(split)
        checked.append({**row, 'sample_id': sid, 'writer_code': writer, 'split': split, 'path': p})
    leaked = [w for w, parts in writers.items() if len(parts) > 1]
    if leaked: raise ValueError('Writer leakage across splits: ' + ', '.join(leaked[:8]))
    path_leaks=[path for path,splits in paths_by_split.items() if len(splits)>1]
    if path_leaks:raise ValueError('Image path leakage across splits: '+str(path_leaks[0]))
    return checked

def dataset_content_hash(rows:list[dict]) -> str:
    """Fingerprint all provided image BYTES + GT/metadata; not just the CSV path strings."""
    digest=hashlib.sha256()
    for r in sorted(rows,key=lambda r:r['sample_id']):
        if r['split'] not in ('validation','test'):continue
        entry='\t'.join([r['sample_id'],r['writer_code'],r['split'],r['ground_truth'],sha256(r['path'])])
        digest.update((entry+'\n').encode('utf-8'))
    return digest.hexdigest()

def corpus_scores(rows: list[dict]) -> dict:
    if not rows: raise ValueError('No evaluated rows for CER/WER.')
    chars = words = c_err = w_err = exact_lines = 0
    for r in rows:
        truth = ' '.join(r['ground_truth'].split())
        hyp = ' '.join(r['prediction'].split())
        chars += len(truth); words += len(truth.split())
        c_err += edit_distance(truth, hyp); w_err += edit_distance(truth.split(), hyp.split())
        exact_lines += truth == hyp
    if not chars or not words: raise ValueError('Empty references cannot be scored.')
    return {'n': len(rows), 'cer': round(c_err / chars, 6), 'wer': round(w_err / words, 6),
            'char_errors': c_err, 'reference_chars': chars, 'word_errors': w_err,
            'reference_words': words, 'exact_line_rate': round(exact_lines/len(rows), 6)}

class TrOCRRecognizer:
    def __init__(self, model_id: str, device: str = 'auto'):
        try:
            import torch
            from transformers import TrOCRProcessor, VisionEncoderDecoderModel
        except ImportError as exc:
            raise RuntimeError('Install Sprint06 model dependencies first. See INSTALL_SPRINT06_OCR.bat') from exc
        if device == 'auto': device = 'cuda' if torch.cuda.is_available() else 'cpu'
        if device == 'cuda' and not torch.cuda.is_available(): raise ValueError('CUDA requested but unavailable')
        self.torch = torch; self.device = device
        self.processor = TrOCRProcessor.from_pretrained(model_id, trust_remote_code=False)
        self.model = VisionEncoderDecoderModel.from_pretrained(model_id, trust_remote_code=False).to(device).eval()

    def __call__(self, image: Image.Image) -> str:
        pixels = self.processor(image.convert('RGB'), return_tensors='pt').pixel_values.to(self.device)
        with self.torch.inference_mode():
            tokens = self.model.generate(pixels, max_new_tokens=128)
        return self.processor.batch_decode(tokens, skip_special_tokens=True)[0]

def benchmark(manifest: Path, image_root: Path, out: Path, split: str = 'validation',
              device: str = 'auto', pipeline_names: list[str] | None = None,
              recognizer_factory=None, max_samples: int | None = None) -> dict:
    """Score EXACTLY the same samples per pipeline, never a different or missing subset.

    If recognizer_factory injected, results are marked MOCK and cannot be used to select model.
    """
    if split not in ('validation','test'): raise ValueError('Only validation/test evaluations allowed')
    if split=='test' and recognizer_factory is None and max_samples is not None:
        raise ValueError('Frozen test must evaluate the full test split; no partial runs')
    if split=='test' and recognizer_factory is None and (out/'test_metrics.json').exists():
        raise ValueError('Frozen test already evaluated at this output path; do not tune/retry on test')
    all_rows = load_manifest(manifest,image_root)
    content_hash=dataset_content_hash(all_rows)
    if split == 'test' and recognizer_factory is None:
        selected_file=out.parent/'selected_from_validation.json'
        if not selected_file.exists():raise ValueError('Run validation selection before frozen test')
        selection=json.loads(selected_file.read_text(encoding='utf-8'))
        if selection['validation_manifest_sha256']!=sha256(manifest) or selection['dataset_content_sha256']!=content_hash:
            raise ValueError('Manifest OR image contents changed after validation: frozen-test evaluation blocked')
        validation_path=out.parent/'validation'/'validation_metrics.json'
        if not validation_path.is_file():
            raise ValueError('Missing full real-model validation metrics: frozen test blocked')
        vm=json.loads(validation_path.read_text(encoding='utf-8'))
        sc=vm.get('pipeline_scores') or {}
        if (vm.get('status')!='REAL_OCR_MODELS_EXECUTED' or not vm.get('model_executed')
            or vm.get('partial_run') or vm.get('split')!='validation'
            or set(sc)!=set(PIPELINES)
            or vm.get('manifest_sha256')!=sha256(manifest)
            or vm.get('dataset_content_sha256')!=content_hash):
            raise ValueError('Incomplete/stale validation evidence: frozen test blocked')
        validated_winner=min(PIPELINES,key=lambda n:(sc[n]['cer'],sc[n]['wer'],n))
        if selection['selected_pipeline']!=validated_winner:
            raise ValueError('Selected pipeline differs from genuine validation winner')
        if set(pipeline_names or ())!={selection['selected_pipeline']}:
            raise ValueError('Frozen Test MUST only evaluate the preselected validation winner')
    rows = sorted((r for r in all_rows if r['split'] == split), key=lambda r:r['sample_id'])
    if not rows: raise ValueError('No rows for split=' + split)
    if max_samples:
        if max_samples < 1: raise ValueError('max_samples must be positive')
        rows = rows[:max_samples]
    names = pipeline_names or list(PIPELINES)
    if len(names) != len(set(names)) or any(name not in PIPELINES for name in names):
        raise ValueError('Unknown/repeated pipeline')
    if not names: raise ValueError('No OCR pipelines selected')
    if split == 'test' and not (out.parent/'selected_from_validation.json').exists() and recognizer_factory is None:
        raise ValueError('Evaluate and select a pipeline on VALIDATION first; test cannot choose a winner')
    cache = {}
    predicted, scores, timing = [], {}, {}
    for name in names:
        mid, variant = PIPELINES[name]
        if mid not in cache:
            cache[mid] = recognizer_factory(mid) if recognizer_factory else TrOCRRecognizer(mid, device)
        model = cache[mid]
        batch = []
        t0=time.perf_counter()
        for i, r in enumerate(rows,1):
            with Image.open(r['path']) as original:
                if original.width * original.height > 12_000_000: raise ValueError('Image too large: '+r['sample_id'])
                rgb = original.convert('RGB')
            pred = str(model(preprocess(rgb,variant)))
            batch.append({'sample_id':r['sample_id'],'writer_code':r['writer_code'],'split':split,
                          'ground_truth':r['ground_truth'],'prediction':pred})
            predicted.append({'pipeline':name, **batch[-1]})
            print(f'{name}: {i}/{len(rows)} {r["sample_id"]}',flush=True)
        scores[name]=corpus_scores(batch)
        timing[name]={'elapsed_seconds':round(time.perf_counter()-t0,3),
                      'note':'Wall time includes image decoding/preprocessing/inference; first model load is excluded.'}
    out.mkdir(parents=True, exist_ok=True)
    with (out/f'{split}_predictions_LOCAL_ONLY.csv').open('w', encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f, fieldnames=['pipeline','sample_id','writer_code','split','ground_truth','prediction'])
        writer.writeheader();writer.writerows(predicted)
    is_mock = recognizer_factory is not None
    result = {'status':'ENGINEERING_MOCK_ONLY' if is_mock else 'REAL_OCR_MODELS_EXECUTED',
              'split':split, 'n_unique_lines':len(rows), 'line_ids_sha256':hashlib.sha256('\n'.join(r['sample_id'] for r in rows).encode()).hexdigest(),
              'manifest_sha256':sha256(manifest),'dataset_content_sha256':content_hash, 'pipeline_scores':scores,
              'wall_time_by_pipeline':timing, 'dataset_origin':'User-provided registered IAM or other verified handwriting line images',
              'normalization':'collapse whitespace; preserve case and punctuation',
              'evaluated_at_utc':datetime.now(timezone.utc).isoformat(),
              'python':sys.version.split()[0], 'platform':platform.platform(),
              'torch_and_hf_model_weights_in_zip':False,
              'selection_warning':'Use VALIDATION to choose; frozen TEST only once, not for tuning.',
              'partial_run':bool(max_samples), 'model_executed':not is_mock}
    (out/f'{split}_metrics.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n', encoding='utf-8')
    # Only the complete four-way validation protocol is eligible to lock a winner.
    if split=='validation' and not is_mock and (max_samples is not None or set(names)!=set(PIPELINES)):
        result['selection_status']='DIAGNOSTIC_ONLY_INCOMPLETE_PIPELINE_SET'
        (out/f'{split}_metrics.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if split == 'validation' and not is_mock and max_samples is None and set(names)==set(PIPELINES):
        winner=min(names,key=lambda n:(scores[n]['cer'],scores[n]['wer'],n))
        selection={'selected_pipeline':winner,'selection_criterion':'lowest corpus CER on validation; WER tiebreak',
                   'validation_manifest_sha256':sha256(manifest),'dataset_content_sha256':content_hash,'score':scores[winner],
                   'locked':True, 'not_yet_confirmed_on_test':True}
        (out.parent/'selected_from_validation.json').write_text(json.dumps(selection,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    if split == 'test' and not is_mock:
        selection=json.loads((out.parent/'selected_from_validation.json').read_text(encoding='utf-8'))
        result['preselected_pipeline']=selection['selected_pipeline']
        if selection['selected_pipeline'] not in scores:
            raise ValueError('Run selected pipeline on frozen test split')
        (out/f'{split}_metrics.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    return result

def main():
    p=argparse.ArgumentParser(description='MENTRIX paired IAM/human handwriting OCR benchmark')
    p.add_argument('--manifest',type=Path,required=True)
    p.add_argument('--images-dir',type=Path,required=True)
    p.add_argument('--out',type=Path,default=Path('research/sprint6/results'))
    p.add_argument('--split',choices=('validation','test'),default='validation')
    p.add_argument('--device',choices=('auto','cpu','cuda'),default='auto')
    p.add_argument('--pipelines',nargs='+',choices=list(PIPELINES),help='Optional validation subset for CPU diagnostics')
    p.add_argument('--max-samples',type=int,help='Diagnostic subset only; no model selection')
    args=p.parse_args()
    if args.split=='test':
        selected_file=args.out/'selected_from_validation.json'
        if not selected_file.is_file():p.error('Run full validation first. Missing selected_from_validation.json')
        selected=json.loads(selected_file.read_text(encoding='utf-8'))['selected_pipeline']
        names=[selected]    # Blind test: do not compare competing models again on test
    else: names=args.pipelines or list(PIPELINES)
    result=benchmark(args.manifest,args.images_dir,args.out/args.split,args.split,args.device,names,max_samples=args.max_samples)
    print('COMPLETE',result['status'],result['pipeline_scores'])

if __name__=='__main__':main()
