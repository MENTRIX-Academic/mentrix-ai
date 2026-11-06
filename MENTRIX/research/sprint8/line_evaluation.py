"""Independent text-line detection, recognition and question mapping metrics.

Requires ground truth from a human reviewer, NOT copied from an OCR prediction.
Each human line: {page, bbox:[x0,y0,x1,y1], question_id, transcription, verified_by}
Boxes and OCR predictions are mapped one-to-one using descending IoU, with an
explicitly recorded threshold. Unmatched human lines count as recognition
*omissions* in an end-to-end diagnostic only; line recognition CER/WER on matched
lines is intentionally reported separately to avoid conflating detection/reading.
"""
from __future__ import annotations
from research.sprint6.benchmark import corpus_scores


def iou(a, b):
    left = max(a[0], b[0]); top = max(a[1], b[1])
    right = min(a[2], b[2]); bottom = min(a[3], b[3])
    inter = max(0, right-left) * max(0, bottom-top)
    area_a = max(0, a[2]-a[0])*max(0,a[3]-a[1])
    area_b = max(0, b[2]-b[0])*max(0,b[3]-b[1])
    return inter/(area_a+area_b-inter) if (area_a+area_b-inter)>0 else 0.0


def _validate(lines, kind):
    if not isinstance(lines,list):raise ValueError(kind+' lines must be a list')
    for n,line in enumerate(lines):
        if not isinstance(line,dict):raise ValueError(kind+f' line {n} is not an object')
        p=line.get('page'); box=line.get('bbox')
        if type(p) is not int or p<0 or not isinstance(box,(list,tuple)) or len(box)!=4:
            raise ValueError(kind+f' line {n}: page/bbox missing')
        if any(type(v) not in (int,float) for v in box) or not (box[0]<box[2] and box[1]<box[3]):
            raise ValueError(kind+f' line {n}: invalid bbox')
        if kind=='Human':
            if not isinstance(line.get('transcription'),str) or not line['transcription'].strip():
                raise ValueError('Human line '+str(n)+' requires independent transcription')
            if not str(line.get('verified_by') or '').strip():
                raise ValueError('Human line '+str(n)+' requires verified_by provenance')
            if not isinstance(line.get('question_id'),str) or not line['question_id'].strip():
                raise ValueError('Human line '+str(n)+' requires question_id (use UNASSIGNED if needed)')


def evaluate_lines(draft: dict, ground_truth: dict, iou_threshold:float=.5) -> dict:
    """One-to-one layout matching, matched-line OCR, and question mapping.

    This is an optical/layout measurement for *supplied* annotations; the
    caller must ensure ground truth is independent of the OCR predictions.
    """
    if not 0<iou_threshold<=1: raise ValueError('iou_threshold must be in (0,1]')
    human=ground_truth.get('lines')
    if human is None:
        return {'status':'NOT_EVALUATED', 'reason':'Supply independently verified human line boxes and transcriptions in ground_truth.lines'}
    if not human:raise ValueError('Human GT lines cannot be empty')
    predicted=draft.get('lines',[])
    _validate(human,'Human');_validate(predicted,'Predicted')
    candidates=[]
    for h,gt in enumerate(human):
        for p,line in enumerate(predicted):
            if gt['page']!=line['page']:continue
            score=iou(gt['bbox'],line['bbox'])
            if score>=iou_threshold:candidates.append((score,h,p))
    candidates.sort(key=lambda t:(-t[0],t[1],t[2]))
    human_used=set();pred_used=set();pairs=[]
    for score,h,p in candidates:
        if h in human_used or p in pred_used:continue
        human_used.add(h);pred_used.add(p)
        pairs.append((h,p,score))
    tp=len(pairs); fp=len(predicted)-tp;fn=len(human)-tp
    ocr_pairs=[{'ground_truth':human[h]['transcription'],
                'prediction':str(predicted[p].get('raw_text',predicted[p].get('text','')))}
               for h,p,_ in pairs]
    # Matched recognition is not valid when nothing was localized.
    recognized=corpus_scores(ocr_pairs) if ocr_pairs else None
    q_pairs=[(human[h]['question_id'],predicted[p].get('question_id')) for h,p,_ in pairs]
    qcorrect=sum(ref==pred for ref,pred in q_pairs)
    # End-to-end text diagnostic counts every missing GT line as a deletion,
    # but never pretends a predicted extra line has zero cost.
    return {'status':'EVALUATED_AGAINST_INDEPENDENT_LINE_GT',
            'threshold_iou':iou_threshold,
            'line_detection':{'human_lines':len(human),'predicted_lines':len(predicted),
                              'true_positives':tp,'false_positives':fp,'false_negatives':fn,
                              'precision':round(tp/(tp+fp),6) if tp+fp else 0.0,
                              'recall':round(tp/(tp+fn),6),
                              'f1':round(2*tp/(2*tp+fp+fn),6) if 2*tp+fp+fn else 0.0,
                              'mean_matched_iou':round(sum(s for _,_,s in pairs)/tp,6) if tp else None},
            'recognition_on_matched_lines':recognized,
            'question_mapping_on_matched_lines':{'exact_id_matches':qcorrect,
                 'matched_lines':tp, 'exact_match_rate':round(qcorrect/tp,6) if tp else None,
                 'match_coverage_of_human_lines':round(qcorrect/len(human),6)},
            'unmatched_human_line_indices':sorted(set(range(len(human)))-human_used),
            'unmatched_prediction_line_indices':sorted(set(range(len(predicted)))-pred_used),
            'caution':'GT lines must be independent; recognition score excludes lines missed by detection. IoU on boxes is a heuristic; hand-review ambiguous matches.'}
