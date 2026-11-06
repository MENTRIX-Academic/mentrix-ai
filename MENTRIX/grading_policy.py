"""Transparent conservative rule policy; not trained grading accuracy or essay grading."""
from adapter import grade

def evaluate(q,answer):
    out=grade(q,answer,'v2')
    typ=q['type']
    # Never auto-score essays or any uncertain model output. OCR must first be user verified.
    safe=(typ=='mcq' and out['decision'] in ('correct','incorrect')
          or typ=='short_answer' and out['decision'] in ('correct','incorrect')
          or typ=='math' and out['decision']=='correct')
    if out['proposed_score'] is None:safe=False
    return {**out,'auto_scoring_eligible':safe,
            'scoring_policy':'strict_mcq_explicit_short_exact_math_exact_v1',
            'policy_notice':'Provisional/local auto-score: human audit & override supported; do not use as official grade without TA-approved policy.'}
