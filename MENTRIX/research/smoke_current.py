"""NEW deterministic malformed-input crash smoke (not historical test, not safety certification)."""
from pathlib import Path
import collections, json, random, string, sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from adapter import QUESTIONS, grade
SEED=20261030
N=500
ALPHABET=string.ascii_letters+string.digits+' /\\^+=-()[]{}.,;:?_@*\n²٣؟\u200b'
IDS=('MC01','SA02','MA03','MA04','MA05')
def run():
    rng=random.Random(SEED)
    labels=collections.Counter()
    failures=[]
    for index in range(N):
        qid=IDS[index%len(IDS)]
        answer=''.join(rng.choices(ALPHABET,k=rng.randint(0,32)))
        try:
            decision=grade(QUESTIONS[qid],answer,'v2')['decision']
            labels[decision]+=1
        except Exception as exc:
            failures.append({'case_index':index,'question_id':qid,'exception_type':type(exc).__name__})
    result={
        'name':'NEW_2026_10_30_MALFORMED_STRING_EXCEPTION_SMOKE',
        'seed':SEED, 'count':N,
        'outcome_counts':dict(labels), 'crash_count':len(failures),
        'failures':failures,
        'not_evidence_of':'model accuracy, student grading quality, production security, historical fuzz test reproduction'
    }
    (ROOT/'reports').mkdir(exist_ok=True)
    (ROOT/'reports/smoke_current.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    print(f'NEW SMOKE: {N} cases | crashes={len(failures)} | {dict(labels)}')
    if failures: raise RuntimeError(f'{len(failures)} malformed inputs caused unhandled exceptions')
    return result
if __name__=='__main__':run()
