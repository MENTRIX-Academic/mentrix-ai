"""Create an EMPTY human-annotation form from OCR geometry.

Crucially, NEVER copy OCR predictions into independent ground truth.
Use a separate reviewer, viewing original paper pixels (not predicted text).
"""
from __future__ import annotations
import argparse,json
from pathlib import Path


def create_template(draft: dict) -> dict:
    if draft.get('status') != 'UNVERIFIED_OCR_DRAFT':
        raise ValueError('Expected an unverified OCR draft')
    return {
       'instructions': 'INDEPENDENT HUMAN REVIEW ONLY. Fill verified_by, transcription and question_id from ORIGINAL IMAGE without consulting OCR predictions. Keep boxes or correct them.',
       'annotation_status':'BLANK_NOT_GROUND_TRUTH',
       'questions':{qid:{'transcription':'','gold_grade':None} for qid in draft.get('question_answers',{})},
       'lines':[{'page':line['page'],'bbox':line['bbox'],'question_id':'',
                 'transcription':'','verified_by':''} for line in draft['lines']],
       'regions':[],
       'source_draft_status':'UNVERIFIED_OCR_DRAFT'}

def main():
    ap=argparse.ArgumentParser(description='Create BLANK, human-only GT annotation; never use OCR text as label')
    ap.add_argument('--draft',type=Path,required=True)
    ap.add_argument('--output',type=Path,required=True)
    a=ap.parse_args()
    draft=json.loads(a.draft.read_text(encoding='utf-8'))
    target=create_template(draft)
    if a.output.exists():ap.error('Refusing to overwrite human annotations: '+str(a.output))
    a.output.parent.mkdir(parents=True,exist_ok=True)
    a.output.write_text(json.dumps(target,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Saved empty annotation form:',a.output,'; NO ground truth has been verified.')

if __name__=='__main__':main()
