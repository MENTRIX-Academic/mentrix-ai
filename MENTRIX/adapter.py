"""Adapter to the uploaded, ACTUAL typed-answer TAFlow V2 code.

This is a synthetic local research demo, NOT calibrated or authorized grading.
"""
from pathlib import Path
import json
from grader_v2 import grade_v2
from grader import grade as grade_old

VERSION = 'original-uploaded-v2-2026-10-28'
BANK = json.loads((Path(__file__).resolve().parent / 'questions.json').read_text(encoding='utf-8'))
QUESTIONS = {q['question_id']:q for q in BANK}
SAMPLE_IDS = ('MC01','SA02','MA03','E01')
TYPE_LABELS = {'short_answer':'short','essay_descriptive':'essay'}

def public_question(q):
    result = {
        'id':q['question_id'], 'type':TYPE_LABELS.get(q['type'],q['type']),
        'prompt':q['prompt'], 'points':q['max_score'],
    }
    if q['type']=='mcq':result['options']=q['options']
    return result

def public_quiz(full=False):
    return [public_question(q) for q in (BANK if full else [QUESTIONS[k] for k in SAMPLE_IDS])]

def format_decision(d, max_score):
    outcome='needs_review' if d.decision=='review' else d.decision
    return {
        'decision':outcome,
        'proposed_score':None if d.score is None else d.score*max_score,
        'method':d.method,
        'reason':d.reason,
        'confidence':None,  # No calibrated probability exists for these rules.
    }

def grade(q, answer, version='v2'):
    if version=='v2': d=grade_v2(q,answer)
    elif version=='v1':d=grade_old(q,answer,'type_aware')
    elif version=='strict':d=grade_old(q,answer,'strict')
    else:raise ValueError('Unknown grading version')
    return format_decision(d,q['max_score'])
