"""Read-only audit. Does not touch or retrain any existing model."""
import json,hashlib,csv
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
    source=['grader.py','grader_v2.py','adapter.py','ocr_integration.py','training/finetune_trocr_gpu.py','questions.json']
    hashes={f:sha(ROOT/f) for f in source}
    with (ROOT/'research/data/curated_demo_cases.csv').open(encoding='utf-8-sig',newline='') as f:
        rows=list(csv.DictReader(f))
    original=json.loads((ROOT/'research/results/observed_summary.json').read_text(encoding='utf-8'))
    out={'project':'MENTRIX','existing_files_sha256':hashes,
      'archived_29_case_design_demo':{'case_count':len(rows),'labels':'ASSISTANT_AUTHORED_NOT_HUMAN_GROUND_TRUTH',
        'archived_changed_decisions':original['changed_decisions']},
      'ocr_status':'TrOCR pipeline exists. Real independent OCR CER/WER not supplied in archive.',
      'training_status':'Optional GPU script exists; no evidence of executed project-specific fine-tuning.',
      'website_status':'No website components changed in Sprint 01.'}
    return out
if __name__=='__main__':
    print(json.dumps(main(),indent=2,ensure_ascii=False))
