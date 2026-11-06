"""One-command transparent Phase-1 engineering audit.

Reproduces CURRENT source/cases only. Historical 123 stress examples and 24 original
unit tests cannot be re-run without the missing source CSV and original test files.
"""
from pathlib import Path
import sys, subprocess, hashlib, platform, json, re, datetime, importlib.metadata

ROOT=Path(__file__).resolve().parent
R=ROOT/'reports';R.mkdir(exist_ok=True)
LOG=[]
WARN=[]
PASS=[]
FAIL=[]


def log(line):
    print(line,flush=True)
    LOG.append(line)

def check(ok,label,detail=''):
    bucket=PASS if ok else FAIL
    bucket.append(label)
    log(f"[{'PASS' if ok else 'FAIL'}] {label}"+(f' — {detail}' if detail else ''))

def run(cmd,label):
    log(f'>> {label}: '+ ' '.join(cmd))
    try:
        p=subprocess.run(cmd,cwd=ROOT,text=True,capture_output=True,timeout=120)
        output=(p.stdout+'\n'+p.stderr).strip()
        if p.returncode!=0:log(output[-4000:])
        tests=[int(s) for s in re.findall(r'Ran (\d+) tests',output)]
        check(p.returncode==0,label,(f'tests={sum(tests)}' if tests else '')+ (f'; exit={p.returncode}' if p.returncode else ''))
        return p
    except Exception as exc:
        check(False,label,f'{type(exc).__name__}: {exc}')
        return None

log('MENTRIX / Phase 1 reproducibility audit')
log('IMPORTANT: current engineering reproduction != old stress-suite reproduction != human accuracy')
manifest=json.loads((ROOT/'research/source_manifest.json').read_text(encoding='utf-8'))['sha256']
for filename, expected in manifest.items():
    actual=hashlib.sha256((ROOT/filename).read_bytes()).hexdigest() if (ROOT/filename).exists() else None
    check(actual==expected,f'Original file unchanged: {filename}',actual[:12] if actual else 'MISSING')

p1=run([sys.executable,'-m','unittest','discover','-s','tests','-v'],'Integrated API + engine tests')
p2=run([sys.executable,'-m','unittest','discover','-s','research/tests','-v'],'Research tests')
p3=run([sys.executable,'research/compare.py'],'29-case current demo comparison')
p4=run([sys.executable,'research/smoke_current.py'],'NEW 500-case malformed-input crash smoke')

try:
    observed=json.loads((ROOT/'research/results/observed_summary.json').read_text(encoding='utf-8'))
    check(observed['total_cases']==29 and observed['changed_decisions']==6,'29 example comparison counts',f"cases={observed['total_cases']}, changed={observed['changed_decisions']}")
except Exception as exc:
    check(False,'29 example comparison counts',str(exc))

# Historical archived aggregate is only checked for internal arithmetic; NOT replayed.
try:
    historical=json.loads((ROOT/'research/data/stress_summary.json').read_text(encoding='utf-8'))
    groups=[x for x in historical['summary'] if x['method']=='type_aware_v2']
    total_cases=sum(int(x['cases']) for x in groups)
    total_reviews=sum(int(x['review_cases']) for x in groups)
    check(total_cases==123 and total_reviews==51,'Historical summary arithmetic ONLY',f'archived cases={total_cases}, reviews={total_reviews}; raw test cases absent')
except Exception as exc:
    check(False,'Historical summary arithmetic ONLY',str(exc))

for relative in ['research/data/stress_cases.csv','research/data/synthetic_cases.csv','research/data/test_grader.py','research/data/test_v2.py']:
    if not (ROOT/relative).exists():
        WARN.append(f'MISSING original historical input: {relative}')
        log('[WARN] '+WARN[-1])

for name in ('TA/supervisor actual sign-off','Independent teammate reproduction','Writer-disjoint, TA-labelled holdout for Phase 3'):
    WARN.append('NOT VERIFIED / external gate: '+name)
    log('[WARN] '+WARN[-1])

packages={}
for name in ('fastapi','uvicorn','sympy','httpx'):
    try: packages[name]=importlib.metadata.version(name)
    except importlib.metadata.PackageNotFoundError: packages[name]=None

report={
 'generated_utc':datetime.datetime.now(datetime.timezone.utc).isoformat(),
 'status':'PASS_CURRENT_ENGINEERING_WITH_OPEN_GATES' if not FAIL else 'FAIL_ENGINEERING_CHECKS',
 'python':platform.python_version(), 'os':platform.platform(), 'packages':packages,
 'source_sha256_verified':not any(s.startswith('Original file') for s in FAIL),
 'passed_checks':PASS, 'failed_checks':FAIL, 'known_open_gates':WARN,
 'reproduction_scope':'current 29 curated assistant-authored examples, 20 current unit tests, new 500 crash probes, source hashes',
 'historical_status':'aggregate summaries checked for arithmetic; NOT rerun: historical source cases/tests absent',
 'scientific_status':'not a held-out, independently human-labelled grading evaluation',
}
(R/'phase1_verification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
log('\nFINAL: '+report['status'])
log('Open gates: '+str(len(WARN)))
(R/'phase1_verification.txt').write_text('\n'.join(LOG)+'\n',encoding='utf-8')
sys.exit(1 if FAIL else 0)
