"""Full-sheet handwritten OCR prototype with explicit segment/recognize/grade separation.

TrOCR is a LINE recognizer. It never detects questions itself. Here a simple
row-projection detector proposes lines; textual Q labels (or TA-specified regions)
assign them to questions. Every output is a DRAFT pending human verification.
"""
from __future__ import annotations
import argparse, io, json, re
from pathlib import Path
from PIL import Image, ImageOps, ImageDraw
from ocr_quality import line_quality
from research.sprint6.benchmark import PIPELINES, TrOCRRecognizer, preprocess, corpus_scores
from research.sprint6.handwriting_layout import Candidate, smart_line_candidates

Q_START = re.compile(r'^\s*(?:Q\s*(\d{1,4})|Question\s*(\d{1,4}))\s*[:.)\-]\s*',re.I)


def render_pages(raw: bytes, filename: str) -> list[Image.Image]:
    if len(raw) > 10_000_000:raise ValueError('Maximum paper size: 10 MB')
    if raw.startswith(b'%PDF-'):
        import fitz
        pages=[]
        with fitz.open(stream=raw,filetype='pdf') as pdf:
            if not 1<=len(pdf)<=8:raise ValueError('PDF must have 1–8 pages')
            for page in pdf:
                pix=page.get_pixmap(matrix=fitz.Matrix(1.5,1.5),alpha=False)
                if pix.width*pix.height > 18_000_000:raise ValueError('PDF rendered page too large')
                pages.append(Image.open(io.BytesIO(pix.tobytes('png'))).convert('RGB'))
        return pages
    with Image.open(io.BytesIO(raw)) as img:
        if img.format not in ('PNG','JPEG','WEBP'):raise ValueError('Unsupported image')
        if img.width*img.height>18_000_000 or img.width<100 or img.height<80:
            raise ValueError('Image dimensions outside allowed range')
        return [ImageOps.exif_transpose(img).convert('RGB')]


def suggest_line_boxes(image:Image.Image,max_lines:int=80) -> list[tuple[int,int,int,int]]:
    """Heuristic only: single-column pages, no tables, skew, handwriting lines overlap."""
    import numpy as np
    from PIL import ImageFilter
    gray=ImageOps.grayscale(image)
    # Avoid moving coordinates by always computing the projection at original resolution.
    gray=gray.filter(ImageFilter.MedianFilter(size=3))
    a=np.asarray(gray,dtype='uint8')
    w,h=image.width,image.height
    mask=a < 185
    # A dark border or shadow is ignored in the row count by cropping horizontal margins.
    edge=max(2,int(w*.015))
    row_ink=mask[:,edge:w-edge].sum(axis=1)
    min_pixels=max(4,round(w*.006))
    active=[int(y) for y in np.where(row_ink >= min_pixels)[0]]
    if not active:return []
    gap=max(3,min(13,round(h*.004)))
    clusters=[];start=last=active[0]
    for y in active[1:]:
        if y-last<=gap:last=y
        else:
            if last-start>=4:clusters.append((start,last))
            start=last=y
    if last-start>=4:clusters.append((start,last))
    if len(clusters)>max_lines:raise ValueError('Too many/overlapping lines; use manually selected question regions')
    boxes=[]
    for y0,y1 in clusters:
        lo=max(0,y0-7);hi=min(h,y1+8)
        sub=mask[lo:hi,:]
        xs=np.where(sub.any(axis=0))[0]
        if not len(xs):continue
        x0=max(0,int(xs[0])-12);x1=min(w,int(xs[-1])+13)
        if x1-x0>=20 and hi-lo>=10:boxes.append((x0,lo,x1,hi))
    return boxes




def line_candidates(image:Image.Image, mode:str='smart', max_lines:int=80):
    """Keep the proven legacy detector available as an explicit fallback."""
    if mode not in ('smart','legacy'):
        raise ValueError('Unknown line detection mode')
    if mode == 'smart':
        try:
            smart, details = smart_line_candidates(image,max_lines=max_lines)
            if smart:
                return smart, details
            # A single cropped line with faint handwriting should not be lost
            # if projection thresholding fails. NEVER OCR an arbitrary full page.
            if image.width/image.height >= 1.7 and image.height <= 380:
                return [Candidate((0,0,image.width,image.height),image.convert('RGB'))], {
                    'method':'single_line_crop_fallback', 'reason':details.get('reason'),
                    'requires_review':True, 'angle_degrees':0.}
            return [],details
        except ImportError:
            pass
        except RuntimeError as exc:
            if 'opencv' not in str(exc).lower(): raise
    boxes=suggest_line_boxes(image,max_lines)
    return [Candidate(tuple(b),image.crop(b)) for b in boxes],{
        'method':'legacy_row_projection', 'requires_review':True,
        'reason':'legacy_selected' if mode == 'legacy' else 'opencv_not_installed',
        'angle_degrees':0.}


def validate_regions(regions:list[dict],pages:list[Image.Image],valid_ids:set[str]) -> list[dict]:
    if not isinstance(regions,list) or not 1<=len(regions)<=50:raise ValueError('1–50 TA-labeled regions required')
    out=[]
    for i,item in enumerate(regions):
        if not isinstance(item,dict):raise ValueError('Region must be an object')
        qid=item.get('question_id')
        if qid not in valid_ids:raise ValueError(f'Unknown question_id at region {i}: {qid}')
        page=item.get('page')
        box=[item.get(k) for k in ('x0','y0','x1','y1')]
        if type(page) is not int or not 0<=page<len(pages) or any(type(v) is not int for v in box):
            raise ValueError('Region requires 0-based integer page index and integer pixel coordinates')
        x0,y0,x1,y1=box;w,h=pages[page].size
        if not (0<=x0<x1<=w and 0<=y0<y1<=h and x1-x0>=20 and y1-y0>=10):
            raise ValueError('Region outside page or too small')
        out.append({'question_id':qid,'page':page,'bbox':box})
    return out


def transcribe_full_sheet(raw:bytes,filename:str,recognizer,
                          pipeline:str='E01_base_rgb',valid_question_ids:list[str]|None=None,
                          regions:list[dict]|None=None, line_detection:str='smart',
                          retry_unclear:bool=False) -> dict:
    if pipeline not in PIPELINES:raise ValueError('Unknown OCR pipeline')
    if line_detection not in ('smart','legacy'):raise ValueError('Unknown line detection mode')
    pages=render_pages(raw,filename)
    valid_ids=set(valid_question_ids or [])
    if not valid_ids: raise ValueError('Approved quiz question IDs must be supplied')
    variant=PIPELINES[pipeline][1]
    lines=[];warnings=[];answers={};layout=[];retry_count=0
    segment_mode='manual_question_regions' if regions is not None else 'detected_lines_plus_text_labels'

    def recognize_line(pic, variant):
        nonlocal retry_count
        first=str(recognizer(preprocess(pic,variant))).strip()
        quality=line_quality(pic,first)
        alternatives=[]
        selected=first
        suspicious=not first or any('repeats a word' in flag for flag in quality['flags'])
        if retry_unclear and suspicious and retry_count < 12:
            retry_count+=1
            alternate_variant='autocontrast' if variant != 'autocontrast' else 'padded'
            attempt=str(recognizer(preprocess(pic,alternate_variant))).strip()
            if attempt and attempt!=first:
                alternatives.append({'preprocess':alternate_variant,'text':attempt})
                if not first:
                    selected=attempt
                    quality=line_quality(pic,selected)
                    quality['flags'].append('Original OCR was empty; displayed text came from a second preprocessing pass. Verify it.')
        return selected,first,quality,alternatives

    if regions is not None:
        areas=validate_regions(regions,pages,valid_ids)
        for area in areas:
            x0,y0,x1,y1=area['bbox'];page=pages[area['page']]
            region_crop=page.crop((x0,y0,x1,y1))
            candidates,details=line_candidates(region_crop,line_detection)
            layout.append({'page':area['page'],'question_id':area['question_id'],**details})
            # Manual regions are explicit enough for a single-line crop fallback,
            # but never silently send a multi-line block to a line-only model.
            if not candidates and region_crop.width/region_crop.height >= 1.7:
                candidates=[Candidate((0,0,region_crop.width,region_crop.height),region_crop)]
                warnings.append('Region has no detected lines; using single-line crop fallback')
            if not candidates:
                warnings.append('No lines found in manual region for '+area['question_id'])
            for item in candidates:
                ax0,ay0,ax1,ay1=item.bbox
                txt,first,quality,alternatives=recognize_line(item.image,variant)
                lines.append({'page':area['page'],'bbox':[x0+ax0,y0+ay0,x0+ax1,y0+ay1],
                              'question_id':area['question_id'],'text':txt,'raw_text':txt,
                              'first_pass_text':first,'alternatives':alternatives,
                              'rotation_degrees':item.angle,'quality':quality})
        for qid in valid_question_ids:
            content=[line['text'] for line in lines if line['question_id']==qid]
            answers[qid]='\n'.join(content).strip()
    else:
        current=None
        for page_no,page in enumerate(pages):
            candidates,details=line_candidates(page,line_detection)
            layout.append({'page':page_no,**details})
            if not candidates:warnings.append(f'No stable lines detected on page {page_no+1}')
            for item in candidates:
                txt,first,quality,alternatives=recognize_line(item.image,variant)
                model_raw_text=txt
                found=Q_START.match(txt)
                if found:
                    proposed='Q'+(found.group(1) or found.group(2))
                    if proposed in valid_ids:
                        current=proposed
                        txt=txt[found.end():].strip()
                    else:
                        current=None
                        warnings.append('Unknown question marker recognized: '+proposed)
                row={'page':page_no,'bbox':list(item.bbox),'question_id':current,'text':txt,
                     'raw_text':model_raw_text,'first_pass_text':first,
                     'alternatives':alternatives,'rotation_degrees':item.angle,
                     'quality':quality}
                lines.append(row)
                if current is not None:
                    answers.setdefault(current,[]).append(txt)
                elif txt:
                    warnings.append(f'Unassigned OCR text at page {page_no+1}: check question boundaries')
        answers={qid:'\n'.join(parts).strip() for qid,parts in answers.items()}
        if not answers:warnings.append('Question labels not confidently recognized; use manually labeled question regions')
    missing=sorted(valid_ids-set(answers))
    if missing:warnings.append('Questions with no assigned answer: '+', '.join(missing))
    if any(line['quality']['flags'] for line in lines):
        warnings.append('Some line crops have quality flags; inspect them visually')
    # Recognized handwriting must never disappear merely because the model did not
    # understand Q1/Q2 labels. Keep *all* raw lines independent of question mapping.
    # A single cropped line such as IAM p01_region_01.jpg is not a full quiz sheet.
    raw_lines=[str(ln.get('raw_text', ln.get('text', ''))).strip() for ln in lines]
    raw_text='\n'.join(t for t in raw_lines if t)
    unassigned=[{'page':ln['page'], 'bbox':ln['bbox'], 'text':ln['text']}
                for ln in lines if not ln.get('question_id') and ln.get('text', '').strip()]
    assigned_text='\n'.join(f'{qid}: {value}' for qid,value in answers.items())
    # With *zero* question matches, showing the raw transcription is more useful
    # than silently storing an empty textarea. This is still NEVER a graded answer.
    display_text=assigned_text if answers else raw_text
    if not raw_text:
        warnings.append('No readable text was returned by OCR; check line detection, image quality and model output')
    elif unassigned:
        warnings.append(f'{len(unassigned)} OCR line(s) could not be linked to a question; inspect raw text below')
    # Do NOT grade or publish from these predictions. Staff must compare original paper.
    return {'status':'UNVERIFIED_OCR_DRAFT', 'pipeline':pipeline,
            'model_id':PIPELINES[pipeline][0],'segmentation':segment_mode,
            'line_detection':line_detection,'page_layout':layout, 'extra_pass_attempts':retry_count,
            'manual_regions':regions or [],
            'pages':len(pages),'lines':lines,'question_answers':answers,
            'raw_ocr_text':raw_text,'unassigned_lines':unassigned,
            'line_stats':{'detected':len(lines),'nonempty':sum(bool(t) for t in raw_lines),
                          'unassigned_nonempty':len(unassigned)},
            'extracted_text':display_text,
            'question_coverage':{'matched':len(valid_ids & set(answers)),'expected':len(valid_ids)},
            'warnings':list(dict.fromkeys(warnings)),
            'grading_performed':False,'transcription_verified':False,
            'next_action':'TA must verify original image and correct text, then submit existing verify-and-grade endpoint.'}


def annotate_pages(raw:bytes,filename:str,lines:list[dict],out_dir:Path,prefix:str='page') -> list[Path]:
    """Visualize heuristic line cuts; green means a Q ID was assigned, not correct OCR."""
    out_dir.mkdir(parents=True,exist_ok=True)
    result=[]
    for page_no,page in enumerate(render_pages(raw,filename)):
        overlay=page.copy();drawer=ImageDraw.Draw(overlay)
        for ln in lines:
            if ln['page']!=page_no:continue
            color=(23,117,79) if ln.get('question_id') else (182,80,46)
            drawer.rectangle(ln['bbox'],outline=color,width=3)
            drawer.text((ln['bbox'][0],max(0,ln['bbox'][1]-13)),ln.get('question_id') or 'UNASSIGNED',fill=color)
        path=out_dir/f'{prefix}_{page_no}.png'
        overlay.save(path)
        result.append(path)
    return result


def bbox_iou(box_a,box_b):
    x0=max(box_a[0],box_b[0]);y0=max(box_a[1],box_b[1]);x1=min(box_a[2],box_b[2]);y1=min(box_a[3],box_b[3])
    intersection=max(0,x1-x0)*max(0,y1-y0)
    aa=max(0,box_a[2]-box_a[0])*max(0,box_a[3]-box_a[1])
    bb=max(0,box_b[2]-box_b[0])*max(0,box_b[3]-box_b[1])
    return intersection/(aa+bb-intersection) if aa+bb>intersection else 0.


def question_region_scores(draft:dict,ground_truth:dict) -> dict:
    """Optional spatial matching: human annotated question region bboxes at rendered image resolution."""
    references=ground_truth.get('regions')
    if references is None:return {'status':'NOT_EVALUATED','reason':'No human-annotated question-region boxes supplied'}
    if not isinstance(references,list) or not references:raise ValueError('GT regions must be non-empty list')
    predictions={}
    for line in draft.get('lines',[]):
        qid=line.get('question_id')
        if not qid:continue
        key=(qid,line['page'])
        box=line['bbox']
        if key not in predictions:predictions[key]=list(box)
        else:
            p=predictions[key]
            predictions[key]=[min(p[0],box[0]),min(p[1],box[1]),max(p[2],box[2]),max(p[3],box[3])]
    ious=[]
    for ref in references:
        qid=ref['question_id'];page=ref['page'];box=ref['bbox']
        if len(box)!=4:raise ValueError('GT region bbox must contain four numbers')
        ious.append(bbox_iou(predictions.get((qid,page),[0,0,0,0]),box))
    return {'status':'EVALUATED', 'gt_regions':len(ious),
            'mean_iou':round(sum(ious)/len(ious),6),
            'iou_at_0_5_recall':round(sum(x>=.5 for x in ious)/len(ious),6),
            'caution':'Line box unions are compared with human region annotations; not a standalone page-layout benchmark'}


def evaluate_full_sheet(draft:dict, ground_truth:dict, question_bank:dict|None=None) -> dict:
    """Independent OCR, question-ID segmentation, and OPTIONAL provisional scoring agreement.

    Ground-truth schema: {questions:{Q1:{transcription:"...",gold_grade:1}, ...}}.
    Gold scoring must be assigned by a human independent of OCR.
    """
    qs=ground_truth.get('questions',{})
    if not isinstance(qs,dict) or not qs:raise ValueError('Human ground-truth questions required')
    expected=set(qs);actual=set(draft['question_answers'])
    pairs=[]
    for qid,info in qs.items():
        ref=info.get('transcription','')
        if not ref.strip():raise ValueError('Missing human transcription for '+qid)
        pairs.append({'ground_truth':ref,'prediction':draft['question_answers'].get(qid,'')})
    matched=expected & actual
    from research.sprint8.line_evaluation import evaluate_lines
    result={'status':'EVALUATED_AGAINST_SUPPLIED_GROUND_TRUTH',
            'ocr_metrics':corpus_scores(pairs),
            'question_segmentation':{'matched_ids':len(matched),'expected_ids':len(expected),
                 'detected_ids':len(actual),'recall':round(len(matched)/len(expected),6),
                 'precision':round(len(matched)/len(actual),6) if actual else 0.0,
                 'metric_scope':'Question ID assignment only; NOT bounding-box IoU or line segmentation accuracy'},
            'spatial_question_regions':question_region_scores(draft,ground_truth),
            'independent_line_evaluation':evaluate_lines(draft,ground_truth),
            'grading_diagnostics':{'status':'NOT_EVALUATED','reason':'Human grade labels/quiz policy not provided'},
            'never_auto_publish_from_ocr':True}
    if question_bank:
        from integrated_workflow import grade_rule
        count=0;oracle_scored=oracle_correct=0;draft_scored=draft_correct=draft_unsafe=0
        draft_disagreements=[];error_after_perfect_transcription=[];ocr_changed_decision=[]
        for qid,info in qs.items():
            if 'gold_grade' not in info or qid not in question_bank:continue
            count+=1
            gold=float(info['gold_grade'])
            gold_answer=info['transcription']
            qpolicy=dict(question_bank[qid])
            if isinstance(qpolicy.get('allowed_answers'),list):
                qpolicy['allowed_answers']=json.dumps(qpolicy['allowed_answers'])
            o_score,o_status,_=grade_rule(qpolicy,gold_answer)
            d_score,d_status,_=grade_rule(qpolicy,draft['question_answers'].get(qid,''))
            if o_status=='auto_scored':
                oracle_scored+=1
                if float(o_score)==gold: oracle_correct+=1
                else: error_after_perfect_transcription.append(qid)
            if d_status=='auto_scored':
                draft_scored+=1
                if float(d_score)==gold:draft_correct+=1
                else:draft_unsafe+=1;draft_disagreements.append(qid)
            if d_status!=o_status or (d_status=='auto_scored' and o_status=='auto_scored' and d_score!=o_score):
                ocr_changed_decision.append(qid)
        result['grading_diagnostics']={'status':'DIAGNOSTIC_ONLY_NOT_PUBLISHED',
              'human_grade_labeled_questions':count,
              'verified_text_oracle':{'auto_scored_cases':oracle_scored,
                 'correct_auto_grades':oracle_correct,'incorrect_auto_grades':oracle_scored-oracle_correct,
                 'auto_coverage':round(oracle_scored/count,6) if count else None,
                 'accuracy_of_auto_decisions':round(oracle_correct/oracle_scored,6) if oracle_scored else None},
              'unverified_ocr_draft':{'auto_scored_cases':draft_scored,
                 'correct_auto_grades':draft_correct,'unsafe_auto_grades':draft_unsafe,
                 'auto_coverage':round(draft_scored/count,6) if count else None,
                 'accuracy_of_auto_decisions':round(draft_correct/draft_scored,6) if draft_scored else None},
              'policy_errors_even_with_correct_transcription':error_after_perfect_transcription,
              'ocr_changed_scoring_decision_question_ids':ocr_changed_decision,
              'unsafe_ocr_based_auto_grades_question_ids':draft_disagreements,
              'caution':'Oracle = true independent human transcription. OCR draft scoring is offline diagnostic ONLY; actual MENTRIX always requires TA verified text before scoring.'}
    return result


def main():
    p=argparse.ArgumentParser(description='Full handwritten paper OCR, never auto-grade')
    p.add_argument('--input',type=Path,required=True)
    p.add_argument('--out',type=Path,required=True)
    p.add_argument('--question-ids',required=True,help='Comma-separated approved question IDs, e.g. Q1,Q2,Q3,Q4')
    p.add_argument('--pipeline',choices=list(PIPELINES),default='E01_base_rgb')
    p.add_argument('--line-detection',choices=['smart','legacy'],default='smart')
    p.add_argument('--retry-unclear',action='store_true',help='Try a second preprocessing pass on blank/repetitive lines; slower')
    p.add_argument('--regions-json',type=Path,help='Optional manual question boxes in rendered page pixel coordinates')
    p.add_argument('--ground-truth-json',type=Path,help='Independently human-transcribed question answers')
    p.add_argument('--question-bank-json',type=Path,help='Optional approved quiz policy to measure grading vs human scores')
    p.add_argument('--annotated-dir',type=Path,help='Save pages with line bounding-box overlay')
    args=p.parse_args()
    recognizer=TrOCRRecognizer(PIPELINES[args.pipeline][0])
    boxes=json.loads(args.regions_json.read_text(encoding='utf-8')) if args.regions_json else None
    draft=transcribe_full_sheet(args.input.read_bytes(),args.input.name,recognizer,args.pipeline,args.question_ids.split(','),boxes, args.line_detection,args.retry_unclear)
    if args.ground_truth_json:
        bank=json.loads(args.question_bank_json.read_text(encoding='utf-8')) if args.question_bank_json else None
        draft['evaluation']=evaluate_full_sheet(draft,json.loads(args.ground_truth_json.read_text(encoding='utf-8')),bank)
    if args.annotated_dir:
        paths=annotate_pages(args.input.read_bytes(),args.input.name,draft['lines'],args.annotated_dir)
        draft['annotated_images_LOCAL_ONLY']=[str(p) for p in paths]
    args.out.parent.mkdir(parents=True,exist_ok=True)
    args.out.write_text(json.dumps(draft,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    print('Saved',args.out,'; status:',draft['status'],'; questions:',draft['question_coverage'])
if __name__=='__main__':main()
