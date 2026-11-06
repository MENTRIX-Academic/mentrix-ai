"""TAFlow minimal, typed-answer-only grading baselines.

NOT an OCR system; NOT a trained ML model; NOT approved for student grades.
Run with: python run_pilot.py
"""
from __future__ import annotations
import ast
from dataclasses import dataclass, asdict
from difflib import SequenceMatcher
import re
import unicodedata

try:
    import sympy as sp
except ImportError:
    sp = None


@dataclass
class Decision:
    decision: str               # correct, incorrect, review
    score: float | None         # None means send to human; not zero
    reason: str
    method: str

    def to_dict(self): return asdict(self)


def result(label, reason, method):
    return Decision(label, None if label == 'review' else float(label == 'correct'), reason, method)


def mcq_strict(answer, q):
    if not answer.strip():
        return result('incorrect','Blank answer','MCQ_STRICT')
    return result('correct' if answer.strip()==q['correct_letter'] else 'incorrect', 'Literal letter match only','MCQ_STRICT')


def mcq_normalized(answer, q):
    s = answer.strip()
    if not s:
        return result('incorrect','Blank answer','MCQ_NORMALIZED')
    # Accept exactly one option; do not extract a letter from a longer answer.
    m = re.fullmatch(r'(?i)\s*(?:option\s+)?\(?([abcd])\)?\.?\s*',s)
    if not m:
        return result('review','Invalid or multiple option characters; do not guess','MCQ_NORMALIZED')
    return result('correct' if m.group(1).upper() == q['correct_letter'] else 'incorrect','Validated single option letter','MCQ_NORMALIZED')


def normalize_short(s):
    s=unicodedata.normalize('NFKC',s).casefold().strip()
    s=re.sub(r'[-‐‑–]', ' ', s)
    s=re.sub(r'^[\s.,;:!?()]+|[\s.,;:!?()]+$', '', s)
    return re.sub(r'\s+',' ',s)


def short_strict(answer,q):
    if not answer.strip(): return result('incorrect','Blank answer','SHORT_STRICT')
    return result('correct' if answer.strip()==q['canonical_answer'] else 'incorrect','Literal canonical answer only','SHORT_STRICT')


def short_aliases(answer,q):
    s=normalize_short(answer)
    if not s: return result('incorrect','Blank answer','SHORT_ALIASES')
    if len(s.split()) > q['max_words']:
        return result('review','Over expected response length; could be descriptive or ambiguous','SHORT_ALIASES')
    accepted = [normalize_short(x) for x in q['accepted_answers']]
    if s in accepted:
        return result('correct','Exact accepted variant after normalization','SHORT_ALIASES')
    if re.search(r'\b(no|not|never|or)\b',s):
        return result('review','Negation or multiple answer requires review','SHORT_ALIASES')
    if max(SequenceMatcher(None,s,a).ratio() for a in accepted) >= 0.79:
        return result('review','Close spelling/possible typo; do not auto-award marks','SHORT_ALIASES')
    return result('incorrect','No listed accepted variant','SHORT_ALIASES')


class UnsupportedMath(ValueError):
    pass


MATH_FUNCS = {'sqrt':lambda v:sp.sqrt(v), 'sin':lambda v:sp.sin(v),'cos':lambda v:sp.cos(v)}
ALLOWED_UNITS = {'hz':('frequency',1),'khz':('frequency',1000),'s':('time',1),'ms':('time',sp.Rational(1,1000) if sp else 0.001)}

def safe_expression(s, allowed_symbols=()):
    """Small AST parser, no eval, no imports or arbitrary functions.

    Restricted to simple math; real security still requires external resource limits.
    """
    if sp is None: raise UnsupportedMath('SymPy required')
    if len(s)>100: raise UnsupportedMath('Expression too long')
    s = s.strip().replace('−','-').replace('×','*').replace('÷','/').replace('^','**')
    if '**' in s and '***' in s: raise UnsupportedMath('Malformed exponent')
    try: t=ast.parse(s,mode='eval')
    except SyntaxError as e: raise UnsupportedMath('Unparseable expression') from e
    if sum(1 for _ in ast.walk(t))>45: raise UnsupportedMath('Expression too complex')
    syms = {name:sp.Symbol(name, real=True, nonzero=True) for name in allowed_symbols}
    def walk(n,depth=0):
        if depth>12: raise UnsupportedMath('Nesting depth exceeded')
        if isinstance(n,ast.Expression): return walk(n.body,depth+1)
        if isinstance(n,ast.Constant) and type(n.value) in (int,float):
            if abs(n.value)>10**9: raise UnsupportedMath('Numeric magnitude too large')
            return sp.Rational(str(n.value))
        if isinstance(n,ast.Name) and n.id in syms: return syms[n.id]
        if isinstance(n,ast.UnaryOp) and isinstance(n.op,(ast.UAdd,ast.USub)):
            v=walk(n.operand,depth+1)
            return v if isinstance(n.op,ast.UAdd) else -v
        if isinstance(n,ast.BinOp):
            a,b=walk(n.left,depth+1),walk(n.right,depth+1)
            if isinstance(n.op,ast.Add): return a+b
            if isinstance(n.op,ast.Sub): return a-b
            if isinstance(n.op,ast.Mult): return a*b
            if isinstance(n.op,ast.Div):
                if b==0: raise UnsupportedMath('Division by zero')
                return a/b
            if isinstance(n.op,ast.Pow):
                if not b.is_number or b.free_symbols or abs(float(b))>10 or (a.is_number and abs(float(a))>10**6):
                    raise UnsupportedMath('Exponent outside safe prototype limits')
                return a**b
        if isinstance(n,ast.Call) and isinstance(n.func,ast.Name) and n.func.id in MATH_FUNCS and len(n.args)==1 and not n.keywords:
            return MATH_FUNCS[n.func.id](walk(n.args[0],depth+1))
        raise UnsupportedMath('Unsupported math syntax/variable')
    try:
        out=walk(t)
        if out.has(sp.zoo,sp.nan,sp.oo,-sp.oo): raise UnsupportedMath('Non-finite expression')
        if sp.count_ops(out)>100: raise UnsupportedMath('Too many operations')
        return out
    except (ZeroDivisionError,OverflowError,TypeError,ValueError) as e:
        raise UnsupportedMath(str(e)) from e


def parse_math_response(response,q):
    raw=response.strip()
    if not raw: raise UnsupportedMath('Blank')
    # No multiline answer / multiple answer alternatives in this baseline.
    if ' or ' in raw.lower() or '\n' in raw or ',' in raw: raise UnsupportedMath('Multiple/ambiguous answers')
    lhs=q.get('allow_lhs')
    if '=' in raw:
        if raw.count('=')!=1 or not lhs or raw.split('=',1)[0].strip()!=lhs:
            raise UnsupportedMath('Equation with unsupported left-hand side')
        raw=raw.split('=',1)[1].strip()
    m=re.fullmatch(r'(.*?)\s*(kHz|Hz|ms|s)\s*',raw,flags=re.I)
    if m:
        raw=m.group(1).strip()
        unit=m.group(2).casefold()
    else: unit=None
    return safe_expression(raw,q.get('allowed_symbols',[])),unit


def math_strict(answer,q):
    if not answer.strip(): return result('incorrect','Blank answer','MATH_STRICT')
    accepted=q['canonical_expression'] + (' '+q['base_unit'] if q['base_unit'] else '')
    return result('correct' if answer.strip()==accepted else 'incorrect','Literal canonical expression and unit','MATH_STRICT')


def math_verified(answer,q):
    if not answer.strip(): return result('incorrect','Blank answer','MATH_TYPED_VERIFIER')
    try:
        actual,unit=parse_math_response(answer,q)
        reference=safe_expression(q['canonical_expression'],q.get('allowed_symbols',[]))
        target_unit=q.get('base_unit')
        if target_unit:
            if unit is None and q.get('require_unit'):
                return result('review','Required unit missing','MATH_TYPED_VERIFIER')
            if unit is not None:
                if unit not in ALLOWED_UNITS:
                    return result('review','Unsupported unit','MATH_TYPED_VERIFIER')
                dim,factor=ALLOWED_UNITS[unit]
                base_dim=ALLOWED_UNITS[target_unit.lower()][0]
                if dim!=base_dim:
                    return result('incorrect','Unit has wrong physical dimension','MATH_TYPED_VERIFIER')
                actual=actual*factor
        elif unit is not None:
            return result('review','Unit is not defined in this question','MATH_TYPED_VERIFIER')
        if actual.is_number and reference.is_number:
            try:
                if abs(float(actual-reference)) <= max(1e-9, 1e-9*abs(float(reference))):
                    return result('correct','Equivalent numerical value / unit','MATH_TYPED_VERIFIER')
                return result('incorrect','Different numerical value','MATH_TYPED_VERIFIER')
            except Exception: raise UnsupportedMath('Cannot compare numeric values')
        if actual==reference:
            return result('correct','Same symbolic expression','MATH_TYPED_VERIFIER')
        # A counterexample at an allowed, non-singular numeric point can prove non-equivalence,
        # even when a symbolic denominator is present. Matching finite samples NEVER proves equality.
        symbols=sorted(actual.free_symbols | reference.free_symbols, key=lambda x:x.name)
        if symbols and len(symbols)<=3:
            for num in (2,3,5):
                substitutions={symbol:sp.Integer(num+i) for i,symbol in enumerate(symbols)}
                try:
                    delta=(actual-reference).subs(substitutions)
                    if delta.is_real and delta.is_finite and delta.is_zero is False:
                        return result('incorrect','A valid numeric counterexample proves non-equivalence','MATH_TYPED_VERIFIER')
                except (TypeError,ValueError,ZeroDivisionError):
                    pass
        # Domain-sensitive cancellation can discard singularities: don't auto-grade it.
        for expr in (actual,reference):
            if any(isinstance(p,sp.Pow) and p.exp.is_negative and p.base.free_symbols for p in sp.preorder_traversal(expr)):
                return result('review','Symbolic denominator needs domain verification','MATH_TYPED_VERIFIER')
        diff=sp.simplify(actual-reference)
        if diff==0:
            return result('correct','Algebraically equivalent expression in supported domain','MATH_TYPED_VERIFIER')
        if diff.is_number and diff != 0 or diff.is_zero is False:
            return result('incorrect','Non-equivalent expression','MATH_TYPED_VERIFIER')
        return result('review','Cannot establish non-equivalence conclusively','MATH_TYPED_VERIFIER')
    except (UnsupportedMath,ValueError,TypeError,OverflowError) as ex:
        return result('review',f'Unsupported or ambiguous math input: {ex}','MATH_TYPED_VERIFIER')


def grade(question,answer,baseline='type_aware'):
    ty=question['type']
    funcs={
      'mcq': (mcq_strict,mcq_normalized),
      'short_answer':(short_strict,short_aliases),
      'math':(math_strict,math_verified),
    }
    if ty not in funcs:
        return result('review','Essay model and rubric remain in earlier project; not rerun here','ESSAY_NOT_RUN')
    return funcs[ty][0 if baseline=='strict' else 1](answer,question)
