"""Staff-only, explicit handwritten full-paper draft action for the MENTRIX UI."""
from __future__ import annotations
import json
from functools import lru_cache
from pathlib import Path
from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import FileResponse, Response
import io
from pydantic import BaseModel, Field
from integrated_workflow import conn, staff_required, UPLOADS, audit, utc
from research.sprint6.benchmark import PIPELINES, TrOCRRecognizer, sha256
from research.sprint6.full_sheet import transcribe_full_sheet, annotate_pages, render_pages

router = APIRouter(prefix='/api/workspace',tags=['Handwritten full paper OCR - pilot'])

# Select validation winner ONLY if it was created by complete real-model validation.
# This is a recommendation, not a certified accuracy guarantee for exam sheets.
VALIDATION_RESULT_DIR=Path(__file__).resolve().parent/'research'/'sprint6'/'results'

def preferred_ocr_pipeline() -> tuple[str,str]:
    chosen='E01_base_rgb'
    selection=VALIDATION_RESULT_DIR/'selected_from_validation.json'
    metrics=VALIDATION_RESULT_DIR/'validation'/'validation_metrics.json'
    manifest=Path(__file__).resolve().parent/'research'/'sprint6'/'data'/'iam_manifest.csv'
    if not (selection.is_file() and metrics.is_file() and manifest.is_file()):
        return chosen,'E01 baseline; no verified local full-validation result yet'
    try:
        from research.sprint6.benchmark import PIPELINES as candidates
        s=json.loads(selection.read_text(encoding='utf-8'))
        m=json.loads(metrics.read_text(encoding='utf-8'))
        valid=(s.get('locked') is True
             and s.get('selected_pipeline') in candidates
             and m.get('status')=='REAL_OCR_MODELS_EXECUTED'
             and m.get('model_executed') is True
             and not m.get('partial_run')
             and m.get('split')=='validation'
             and set(m.get('pipeline_scores',{}))==set(candidates)
             and s.get('selected_pipeline')==min(candidates,key=lambda n:(m['pipeline_scores'][n]['cer'],m['pipeline_scores'][n]['wer'],n))
             and s.get('validation_manifest_sha256')==sha256(manifest)
             and s.get('validation_manifest_sha256')==m.get('manifest_sha256'))
        if valid:return s['selected_pipeline'],'Selected using full IAM validation CER (in-domain only); review handwriting before grading'
    except (ValueError,KeyError,TypeError,OSError,json.JSONDecodeError):
        pass
    return chosen,'E01 baseline; validation evidence absent, incomplete, or changed'


class HandwritingDraftRequest(BaseModel):
    pipeline: str | None = None
    regions: list[dict] | None = None
    line_detection: str = Field(default='smart', pattern='^(smart|legacy)$')
    retry_unclear: bool = False

@lru_cache(maxsize=2)
def get_recognizer(model_id:str):
    return TrOCRRecognizer(model_id)

@router.get('/handwriting/config')
def handwriting_config(request:Request):
    staff_required(request)
    preferred,reason=preferred_ocr_pipeline()
    return {'preferred_pipeline':preferred, 'preferred_reason':reason,
            'pipelines':{k:{'model_id':v[0],'preprocess':v[1]} for k,v in PIPELINES.items()},
            'line_detection_modes':['smart','legacy'],
            'optional_second_pass_for_unclear_lines':True,
            'model_weights_bundled':False,'approved_for_auto_grading':False,
            'status':'available_after_optional_dependencies_and_model_download',
            'warning':'A whole page requires line segmentation; staff must verify every answer.'}

@router.post('/papers/{paper_id}/handwriting-draft')
def handwriting_draft(paper_id:str,body:HandwritingDraftRequest,request:Request):
    staff_required(request)
    pipeline=body.pipeline or preferred_ocr_pipeline()[0]
    if pipeline not in PIPELINES:raise HTTPException(422,'Unknown benchmark pipeline')
    with conn() as db:
        paper=db.execute('SELECT * FROM papers WHERE id=?',(paper_id,)).fetchone()
        if not paper:raise HTTPException(404,'Paper not found')
        if paper['published_at'] is not None:raise HTTPException(409,'Cannot change published grades')
        questions=[r['id'] for r in db.execute('SELECT id FROM questions WHERE quiz_id=? ORDER BY position',(paper['quiz_id'],))]
    files=[p for p in UPLOADS.glob(paper_id+'.*') if p.is_file()]
    if len(files)!=1:raise HTTPException(404,'Original paper file unavailable')
    try:
        model=get_recognizer(PIPELINES[pipeline][0])
        draft=transcribe_full_sheet(files[0].read_bytes(),files[0].name,model,pipeline,questions,body.regions,
                                    body.line_detection,body.retry_unclear)
    except (ValueError,RuntimeError,ImportError,OSError) as exc:
        raise HTTPException(422 if isinstance(exc,ValueError) else 503,'Handwriting OCR failed: '+str(exc)[:400]) from exc
    # OCR output must never be mistaken for verified text or existing safe grades.
    results_dir=UPLOADS.parent/'handwriting_drafts';results_dir.mkdir(parents=True,exist_ok=True)
    annotate_pages(files[0].read_bytes(),files[0].name,draft['lines'],results_dir,paper_id+'_page')
    # Save review crops from the ORIGINAL image (not the model's altered pixels).
    # Images are staff-only, and old crops are discarded when OCR reruns.
    for old in results_dir.glob(paper_id+'_line_*.png'):
        old.unlink()
    source_pages=render_pages(files[0].read_bytes(),files[0].name)
    for index,line in enumerate(draft['lines']):
        original=source_pages[line['page']]
        cropped=original.crop(tuple(line['bbox']))
        cropped.save(results_dir/f'{paper_id}_line_{index}.png',format='PNG')
        line['crop_url']=f'/api/workspace/papers/{paper_id}/handwriting-line/{index}'
    draft['page_image_urls']=[f'/api/workspace/papers/{paper_id}/handwriting-page/{n}' for n in range(draft['pages'])]
    draft['overlay_urls']=[f'/api/workspace/papers/{paper_id}/handwriting-overlay/{n}' for n in range(draft['pages'])]
    (results_dir/(paper_id+'.json')).write_text(json.dumps(draft,ensure_ascii=False,indent=2),encoding='utf-8')
    with conn() as db:
        db.execute('DELETE FROM grades WHERE paper_id=?',(paper_id,))
        db.execute("UPDATE papers SET extracted_text=?,source_kind=?,transcript_verified=0,status='needs_transcript' WHERE id=?",
                   (draft['extracted_text'],'handwriting_trOCR_unverified',paper_id))
        audit(db,'handwriting_ocr_draft',paper_id,{'pipeline':pipeline,
                       'questions_matched':draft['question_coverage']['matched'],
                       'questions_expected':draft['question_coverage']['expected'],
                       'manual_regions':body.regions is not None})
    return {'paper_id':paper_id,**draft}

@router.get('/papers/{paper_id}/handwriting-draft')
def handwriting_draft_detail(paper_id:str,request:Request):
    staff_required(request)
    path=UPLOADS.parent/'handwriting_drafts'/(paper_id+'.json')
    if not path.is_file():raise HTTPException(404,'No handwriting OCR draft for this paper')
    with conn() as db:
        if not db.execute('SELECT 1 FROM papers WHERE id=?',(paper_id,)).fetchone():
            raise HTTPException(404,'Paper not found')
    return json.loads(path.read_text(encoding='utf-8'))

@router.get('/papers/{paper_id}/handwriting-overlay/{page_num}')
def handwriting_overlay(paper_id:str,page_num:int,request:Request):
    staff_required(request)
    if page_num<0 or page_num>7:raise HTTPException(422,'Page outside supported range')
    with conn() as db:
        if not db.execute('SELECT 1 FROM papers WHERE id=?',(paper_id,)).fetchone():
            raise HTTPException(404,'Paper not found')
    path=UPLOADS.parent/'handwriting_drafts'/f'{paper_id}_page_{page_num}.png'
    if not path.is_file():raise HTTPException(404,'Overlay page not available')
    return FileResponse(path,media_type='image/png',headers={'Cache-Control':'no-store'})


@router.get('/papers/{paper_id}/handwriting-page/{page_num}')
def handwriting_page(paper_id:str,page_num:int,request:Request):
    """Original image for visual region selection, independent from OCR overlay."""
    staff_required(request)
    if not 0 <= page_num < 8:raise HTTPException(422,'Page outside supported range')
    with conn() as db:
        if not db.execute('SELECT 1 FROM papers WHERE id=?',(paper_id,)).fetchone():
            raise HTTPException(404,'Paper not found')
    files=[p for p in UPLOADS.glob(paper_id+'.*') if p.is_file()]
    if len(files)!=1:raise HTTPException(404,'Original paper file unavailable')
    pages=render_pages(files[0].read_bytes(),files[0].name)
    if page_num >= len(pages):raise HTTPException(404,'Page not found')
    buffer=io.BytesIO()
    pages[page_num].save(buffer,format='PNG')
    return Response(content=buffer.getvalue(),media_type='image/png',
                    headers={'Cache-Control':'no-store'})


@router.get('/papers/{paper_id}/handwriting-line/{line_index}')
def handwriting_line(paper_id:str,line_index:int,request:Request):
    """A staff-only thumbnail to compare each transcription to the actual ink."""
    staff_required(request)
    if not 0 <= line_index < 640:raise HTTPException(422,'Line outside supported range')
    path=UPLOADS.parent/'handwriting_drafts'/f'{paper_id}_line_{line_index}.png'
    if not path.is_file():raise HTTPException(404,'Line crop not found')
    with conn() as db:
        if not db.execute('SELECT 1 FROM papers WHERE id=?',(paper_id,)).fetchone():
            raise HTTPException(404,'Paper not found')
    return FileResponse(path,media_type='image/png',headers={'Cache-Control':'no-store'})
