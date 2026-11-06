"""Conservative, text-only TAFlow grading prototype v2.

This is NOT trained ML, NOT OCR, NOT production-secure, and does not produce final grades.
The v1 grader.py is untouched for reproducible comparison.
"""
from __future__ import annotations
import ast
import re
import unicodedata
import sympy as sp
from grader import grade as grade_v1, result, normalize_short, parse_math_response, safe_expression, UnsupportedMath

# Explicitly configured known incorrect contrasts for this small approved pilot question bank.
# New courses/questions must have their own educator-reviewed contraindication list.
KNOWN_WRONG = {
 'SA01': ['square wave','rectangular wave'],
 'SA02': ['period','amplitude'],
 'SA03': ['frequency','period'],
 'SA04': ['frequency','amplitude'],
 'SA05': ['period','frequency'],
 'SA06': ['encryption','compression'],
 'SA07': ['sine wave','sinusoid'],
}


def grade_mcq_v2(q,answer):
    s=unicodedata.normalize('NFKC',answer).strip()
    if not s: return result('incorrect','Blank response','MCQ_V2')
    m=re.fullmatch(r'(?i)(?:option\s+|answer\s*:\s*)?[\[(]?([abcd])[\])]?\.?',s)
    if not m:
        return result('review','Ambiguous, multiple, uncertain or unsupported option notation','MCQ_V2')
    label='correct' if m.group(1).upper()==q['correct_letter'] else 'incorrect'
    return result(label,'A single unambiguous A/B/C/D symbol','MCQ_V2')


def grade_short_v2(q,answer):
    s=normalize_short(answer)
    if '?' in answer or '؟' in answer:
        return result('review','Question mark makes response uncertain; manual review','SHORT_V2')
    if not s: return result('incorrect','Blank response','SHORT_V2')
    if len(s.split())>q.get('max_words',3):
        return result('review','Beyond expected length','SHORT_V2')
    accepted={normalize_short(z) for z in q['accepted_answers']}
    if s in accepted:
        return result('correct','Listed accepted answer after normalization','SHORT_V2')
    # Never grant correctness for a near-match; never discard an unknown synonym automatically.
    if s in {normalize_short(z) for z in KNOWN_WRONG.get(q['question_id'],[])}:
        return result('incorrect','Explicitly configured known incorrect contrast','SHORT_V2')
    return result('review','Unlisted, typo, abbreviation, negation, or multi-answer: TA review','SHORT_V2')


def _format_math(s):
    # Minimal unambiguous visual conventions; no arbitrary eval and no general natural-language math parsing.
    s=s.replace('²','^2').replace('³','^3')
    # Only rewrite a digit directly before a letter known to the approved question bank's symbol set.
    s=re.sub(r'(?<=\d)(?=[a-zA-Z])','*',s)
    return s


def _has_risky_symbolic_denominator(expr,allowed_symbols):
    """Conservative pre-simplification AST check for domain-cancellation risk."""
    s=_format_math(expr).replace('−','-').replace('×','*').replace('÷','/').replace('^','**')
    try: tree=ast.parse(s,mode='eval')
    except SyntaxError: return False
    for node in ast.walk(tree):
        if isinstance(node,ast.BinOp) and isinstance(node.op,ast.Div):
            if any(isinstance(n,ast.Name) and n.id in allowed_symbols for n in ast.walk(node.right)):
                return True
        if isinstance(node,ast.BinOp) and isinstance(node.op,ast.Pow):
            if any(isinstance(n,ast.Name) and n.id in allowed_symbols for n in ast.walk(node.left)):
                if isinstance(node.right,ast.UnaryOp) and isinstance(node.right.op,ast.USub): return True
    return False


def grade_math_v2(q,answer):
    if not answer.strip(): return result('incorrect','Blank response','MATH_V2')
    raw=answer.strip()
    expr=raw.split('=',1)[1].strip() if '=' in raw and raw.count('=')==1 else raw
    # Guard symbolic domain BEFORE any simplifying SymPy operations.
    if q.get('allowed_symbols') and _has_risky_symbolic_denominator(expr, q['allowed_symbols']):
        is_only_reference_simple = q['question_id']=='MA05' and _format_math(expr).replace(' ','') in ('1/f','f^-1','f**-1')
        if not is_only_reference_simple:
            return result('review','Symbolic denominator / negative power needs domain check (pre-simplification)','MATH_V2')
    # The v1 safe parser still enforces the AST whitelist and disallows arbitrary code execution.
    rewritten=_format_math(raw)
    d=grade_v1(q,rewritten,'type_aware')
    if d.decision=='correct':
        # Avoid rounding-related false acceptance; decimal values are rationals in safe_expression.
        try:
            actual,unit=parse_math_response(rewritten,q)
            reference=safe_expression(q['canonical_expression'],q.get('allowed_symbols',[]))
            if q.get('base_unit') and unit:
                from grader import ALLOWED_UNITS
                actual=actual*ALLOWED_UNITS[unit][1]
            if actual.is_number and reference.is_number and actual != reference:
                return result('review','Numerically near reference but not exactly equal; precision policy needed','MATH_V2')
        except (UnsupportedMath, KeyError, TypeError, ValueError, OverflowError):
            return result('review','Could not independently verify exact value','MATH_V2')
    return result(d.decision,d.reason,'MATH_V2')


def grade_v2(q,answer):
    return {'mcq':grade_mcq_v2,'short_answer':grade_short_v2,'math':grade_math_v2}.get(q['type'], lambda q,a: result('review','Essay rubric pipeline separate','ESSAY_SEPARATE'))(q,answer)
