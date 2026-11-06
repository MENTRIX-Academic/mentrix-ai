"""MENTRIX Sprint 03: honest, reproducible ASAG baseline comparison.

Dataset: DigiKlausur ASAG, 17 questions x 38 students, 0/1/2 scores.
Not handwriting OCR; not 1-3 word grading; no student identities or rubric criteria.
All models trained per question; answers are not placed in outputs.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
import math
import re
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

import numpy as np
from sklearn.linear_model import Ridge
from sklearn.model_selection import GroupShuffleSplit

# Existing implementation retained from Sprint 02; no historical results overwritten.
from research.sprint2.benchmark import BASELINES, model_factory, vectors, metrics, normalize

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DATASET = ROOT / 'research' / 'sprint3' / 'data' / 'asag_dataset.csv'
DEFAULT_OUTPUT = ROOT / 'research' / 'sprint3' / 'results'
METHODS = BASELINES + ('reference_jaccard_ridge',)
RANGE = (0, 2)
SEED = 42


def filehash(path):
    hasher = hashlib.sha256()
    with open(path, 'rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            hasher.update(chunk)
    return hasher.hexdigest()


def read_asag(path):
    """Read only RAW student answers, references, question ids and human grades.

    Ignore embedded vectors and engineered features to prevent ambiguous provenance.
    Blank answers are a separate, explicit rule (0), not a scored-model result.
    """
    with Path(path).open(encoding='utf-8-sig', newline='') as f:
        reader = csv.DictReader(f)
        needed = {'question_id', 'question', 'student_answer', 'ref_answer', 'grades_round'}
        if not needed.issubset(reader.fieldnames or []):
            raise ValueError('Missing ASAG CSV fields: '+', '.join(sorted(needed - set(reader.fieldnames or []))))
        all_rows, nonempty, blanks = [], [], []
        for rownum, row in enumerate(reader, start=1):
            prompt = (row['question_id'] or '').strip()
            answer = (row['student_answer'] or '').strip()
            gold = (row['grades_round'] or '').strip()
            reference = (row['ref_answer'] or '').strip()
            if not prompt or not reference or gold not in {'0', '1', '2'}:
                raise ValueError(f'Invalid question, reference or human 0/1/2 label on data row {rownum}')
            item = {'sample_id': str(rownum), 'prompt_id': prompt,
                    'answer_text': answer, 'reference_text': reference,
                    'human_score': int(gold)}
            all_rows.append(item)
            if answer:
                nonempty.append(item)
            else:
                if item['human_score'] != 0:
                    raise ValueError(f'Blank answer with nonzero gold grade on data row {rownum}; manual inspection required')
                blanks.append(item)
    if not nonempty:
        raise ValueError('ASAG input contains no nonblank answers')
    return all_rows, nonempty, blanks


def split_prompt(rows, seed=SEED):
    """Group exact normalized duplicates, disjoint train/val/test for each prompt.

    20% test; 25% of remaining (20% overall) validation, rest train.
    """
    groups = [normalize(r['answer_text']) for r in rows]
    if len(set(groups)) < 15:
        raise ValueError('Fewer than 15 answer groups: insufficient for evaluation')
    idx = np.arange(len(rows))
    first = GroupShuffleSplit(n_splits=1, test_size=0.20, random_state=seed)
    trainval_idx, test_idx = next(first.split(idx, groups=groups))
    second = GroupShuffleSplit(n_splits=1, test_size=0.25, random_state=seed + 101)
    train_part, val_part = next(second.split(trainval_idx, groups=[groups[int(i)] for i in trainval_idx]))
    indexes = {'train': [int(trainval_idx[i]) for i in train_part],
               'validation': [int(trainval_idx[i]) for i in val_part],
               'test': [int(i) for i in test_idx]}
    used = set()
    per_split = {}
    for name, positions in indexes.items():
        if len(positions) < 4:
            raise ValueError(f'Too few samples in {name} for prompt {rows[0]["prompt_id"]}')
        keys = {groups[i] for i in positions}
        if used.intersection(keys):
            raise AssertionError('Duplicate answer text leaked across splits')
        used.update(keys)
        per_split[name] = [rows[i] for i in positions]
    return per_split


def ref_jaccard(student, reference):
    a = set(re.findall(r"(?u)\b\w+\b", student.casefold()))
    b = set(re.findall(r"(?u)\b\w+\b", reference.casefold()))
    return (len(a & b) / len(a | b)) if a or b else 0.0


def predict_reference(train, future):
    """Learn linear calibration of reference-token Jaccard on TRAIN ONLY.

    This is NOT the historical Token Overlap or Rubric+NLI from Work Wrap up.
    """
    xt = np.asarray([[ref_jaccard(r['answer_text'], r['reference_text'])] for r in train])
    yt = np.asarray([r['human_score'] for r in train], dtype=float)
    xf = np.asarray([[ref_jaccard(r['answer_text'], r['reference_text'])] for r in future])
    return Ridge(alpha=0.5).fit(xt, yt).predict(xf)


def qwk_or_none(gold, pred):
    from sklearn.metrics import cohen_kappa_score
    if len(set(gold) | set(pred)) < 2:
        return None
    value = float(cohen_kappa_score(gold, pred, labels=[0,1,2], weights='quadratic'))
    return round(value, 5) if math.isfinite(value) else None


def _rounded(raw):
    return np.clip(np.rint(np.asarray(raw, dtype=float)), 0, 2).astype(int)


def execute(dataset=DEFAULT_DATASET, output=DEFAULT_OUTPUT, seed=SEED):
    dataset, output = Path(dataset), Path(output)
    if not dataset.is_file():
        raise FileNotFoundError(f'ASAG CSV not found: {dataset}')
    all_rows, usable, blanks = read_asag(dataset)
    prompts = defaultdict(list)
    for row in usable:
        prompts[row['prompt_id']].append(row)
    if len(prompts) < 2:
        raise ValueError('Expected multiple questions; inspect dataset')
    summary = defaultdict(lambda: {'val_mae': [], 'test_mae': [], 'test_qwk': [], 'test_true': [], 'test_pred': []})
    prompt_results, prediction_rows = [], []
    selected_gold, selected_pred = [], []
    split_manifest = []

    for prompt_id, rows in sorted(prompts.items(), key=lambda kv: int(kv[0]) if kv[0].isdigit() else kv[0]):
        # Include prompt in the seed so each question receives its own reproducible shuffle.
        prompt_seed = seed + (int(prompt_id) if prompt_id.isdigit() else int(hashlib.sha256(prompt_id.encode()).hexdigest()[:5], 16))
        splits = split_prompt(rows, seed=prompt_seed)
        train, val, test = (splits[s] for s in ('train', 'validation', 'test'))
        split_manifest.extend({'prompt_id': prompt_id, 'sample_id': r['sample_id'], 'split': s}
                              for s, part in splits.items() for r in part)
        ytrain = np.asarray([r['human_score'] for r in train])
        yval = np.asarray([r['human_score'] for r in val])
        ytest = np.asarray([r['human_score'] for r in test])
        outcome = {}
        for method in METHODS:
            if method == 'reference_jaccard_ridge':
                valraw = predict_reference(train, val)
                testraw = predict_reference(train, test)
            else:
                model = model_factory(method)
                model.fit(vectors(train, method), ytrain)
                valraw = model.predict(vectors(val, method))
                testraw = model.predict(vectors(test, method))
            v = metrics(yval, valraw, RANGE)
            t = metrics(ytest, testraw, RANGE)
            outcome[method] = {'validation': v, 'test': t}
            summary[method]['val_mae'].append(v['mae'])
            summary[method]['test_mae'].append(t['mae'])
            if t['qwk'] is not None:
                summary[method]['test_qwk'].append(t['qwk'])
            summary[method]['test_true'].extend(int(x) for x in ytest)
            summary[method]['test_pred'].extend(int(x) for x in _rounded(testraw))
            for row, score, pred in zip(test, ytest, _rounded(testraw)):
                prediction_rows.append({'prompt_id': prompt_id, 'sample_id': row['sample_id'],
                                        'method': method, 'gold_score': int(score),
                                        'predicted_score': int(pred), 'absolute_error': abs(int(score)-int(pred)),
                                        'selected_on_validation': False})
        chosen = min(METHODS, key=lambda name: (outcome[name]['validation']['mae'],
                                                 outcome[name]['validation']['raw_mae'], name))
        for rec in prediction_rows:
            if rec['prompt_id'] == prompt_id and rec['method'] == chosen:
                rec['selected_on_validation'] = True
                selected_gold.append(rec['gold_score'])
                selected_pred.append(rec['predicted_score'])
        prompt_results.append({'prompt_id': prompt_id,
                               'rows': {k: len(v) for k,v in splits.items()},
                               'selected_on_validation': chosen, 'baselines': outcome})

    # Pool answers for micro MAE (each answer has the same 0-2 score scale).
    method_summary = {}
    for name in METHODS:
        vals = summary[name]
        truth, pred = vals['test_true'], vals['test_pred']
        method_summary[name] = {
            'macro_test_mae': round(float(np.mean(vals['test_mae'])), 5),
            'micro_test_mae': round(float(np.mean(np.abs(np.array(truth)-np.array(pred)))), 5),
            'macro_test_qwk_defined_only': round(float(np.mean(vals['test_qwk'])), 5) if vals['test_qwk'] else None,
            'questions_with_defined_qwk': len(vals['test_qwk']),
            'pooled_test_qwk': qwk_or_none(truth, pred),
            'pooled_test_exact_match': round(float(np.mean(np.array(truth)==np.array(pred))), 5),
            'heldout_n': len(truth),
        }
    selected_summary = {'test_n': len(selected_gold),
                        'micro_test_mae': round(float(np.mean(np.abs(np.array(selected_gold)-np.array(selected_pred)))),5),
                        'exact_match': round(float(np.mean(np.array(selected_gold)==np.array(selected_pred))),5),
                        'pooled_test_qwk': qwk_or_none(selected_gold,selected_pred)}
    wordcounts = sorted(len(r['answer_text'].split()) for r in usable)
    profile = {
        'total_rows':len(all_rows),'human_scored_nonblank':len(usable),'blank_score_0':len(blanks),
        'question_count':len(prompts),
        'grades_all': dict(sorted(Counter(str(r['human_score']) for r in all_rows).items())),
        'median_words_nonblank':float(np.median(wordcounts)),
        'mean_words_nonblank':round(float(np.mean(wordcounts)),2),
        'one_to_three_word_answers':sum(x<=3 for x in wordcounts),
        'source_file_sha256':filehash(dataset),
    }
    report = {'status':'EXECUTED_ON_USER_UPLOADED_ASAG_CSV',
              'source': 'DigiKlausur/ASAG-Dataset; original dataset URL: https://github.com/DigiKlausur/ASAG-Dataset',
              'run_utc':datetime.now(timezone.utc).isoformat(),
              'dataset':profile,
              'seed':seed,
              'split':'Per-question grouped exact normalized answers; ~60% train, 20% validation, 20% test; 39 blank answers excluded from model test.',
              'model_selection':'Lowest validation rounded MAE, tie-break validation raw MAE; held-out test not used for selection.',
              'methods_are_new_baselines_not_reproductions_of_historical_models':True,
              'grading_scope':'Only typed text responses 0,1,2; NOT OCR, not 1-3-word answers, not TA auto-publish.',
              'limitations':[
                  'Only 27-38 nonblank examples per question, hence high uncertainty and unstable per-question QWK.',
                  'Single human rater; reliability and disagreements cannot be measured.',
                  'No stable student identity column; no cross-question student-disjoint split.',
                  'Exact duplicate leakage blocked within question; semantic near-duplicate leakage not fully excluded.',
                  'No OCR, no approved MENTRIX rubrics, no real 1-3 word final evaluation.',
                  'Text-based baselines do not demonstrate grading correctness on contradictions or safe auto-publishing.'
              ],
              'method_summary':method_summary,
              'validation_selected_summary':selected_summary,
              'per_prompt':prompt_results}
    output.mkdir(parents=True, exist_ok=True)
    (output/'asag_s03_metrics.json').write_text(json.dumps(report,ensure_ascii=False,indent=2,allow_nan=False)+'\n',encoding='utf-8')
    (output/'asag_s03_profile.json').write_text(json.dumps(profile,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
    with (output/'asag_s03_test_predictions.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['prompt_id','sample_id','method','gold_score','predicted_score','absolute_error','selected_on_validation'])
        writer.writeheader();writer.writerows(prediction_rows)
    with (output/'asag_s03_splits.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['prompt_id','sample_id','split']);writer.writeheader();writer.writerows(split_manifest)
    fmt=lambda x: 'N/A' if x is None else f'{x:.4f}'
    lines = ['# MENTRIX — Sprint 03 | ASAG Human-Scored Benchmark', '',
             '**Status:** ACTUALLY EXECUTED on the uploaded `asag_dataset.csv`. No OCR experiment or website changes.', '',
             '## Dataset profile', '',
             f'- Total **{profile["total_rows"]}** graded records from **{profile["question_count"]}** questions.',
             f'- Nonblank answers for learned baselines: **{profile["human_scored_nonblank"]}**. Blank answers excluded: **{profile["blank_score_0"]}**, each human-graded zero.',
             f'- Word count median: **{profile["median_words_nonblank"]:.0f}**, mean: **{profile["mean_words_nonblank"]:.2f}**; only **{profile["one_to_three_word_answers"]}** answer(s) have 1–3 words.',
             f'- Score labels: {profile["grades_all"]}. SHA-256: `{profile["source_file_sha256"]}`.', '',
             '## Held-out test results (same split and scale)', '',
             '| Method | Macro MAE ↓ | Micro MAE ↓ | Pooled QWK ↑ | Exact match ↑ |',
             '|---|---:|---:|---:|---:|']
    for method, result in sorted(method_summary.items(), key=lambda x:x[1]['micro_test_mae']):
        lines.append(f'| {method} | {fmt(result["macro_test_mae"])} | {fmt(result["micro_test_mae"])} | {fmt(result["pooled_test_qwk"])} | {100*result["pooled_test_exact_match"]:.1f}% |')
    lines += ['', '### Validation-selected method per question', '',
              f'This strategy (selected separately per question on VALIDATION) achieved **Micro MAE {fmt(selected_summary["micro_test_mae"])}**, **pooled QWK {fmt(selected_summary["pooled_test_qwk"])}**, **exact match {100*selected_summary["exact_match"]:.1f}%** on **{selected_summary["test_n"]}** held-out nonblank answers.', '',
              '| Question | Train | Val | Test | Selected (validation) | Test MAE | Test QWK |',
              '|---|---:|---:|---:|---|---:|---:|']
    for p in prompt_results:
        chosen=p['selected_on_validation'];t=p['baselines'][chosen]['test']
        lines.append(f'| {p["prompt_id"]} | {p["rows"]["train"]} | {p["rows"]["validation"]} | {p["rows"]["test"]} | {chosen} | {fmt(t["mae"])} | {fmt(t["qwk"])} |')
    lines += ['', '## How to interpret / إزاي نفسّر النتائج؟', '',
              '- الأرقام أعلاه **حقيقية من تشغيل الكود على الملف المرفوع**، لكن حجم البيانات لكل سؤال صغير (27–38 إجابة غير فارغة).',
              '- **النتائج مش مقارنة مباشرة مع أرقام Work Wrap up**؛ لأن الداتا وتقسيمها ومقياس الدرجات مختلفين.',
              '- النماذج 7 Baselines خفيفة مناسبة للجهاز؛ مش MiniLM/NLI/Rubric models التاريخية، ومش Fine-tuning.',
              '- Blank (39) مسار تصحيح rule-based منفصل؛ لم نحتسبها ضمن Test ML حتى لا ترفع الدقة ظاهريًا.',
              '- تقسيم Train / Validation / Test بيمنع تطابق نفس نص الإجابة داخل نفس السؤال عبر المجموعات، لكن لا يوجد Student ID يساعدنا نعمل Writer/Student-disjoint split.',
              '- نجاح Baseline هنا لا يسمح بتفعيل نشر الدرجات تلقائيًا، ولا يثبت قراءة OCR أو إجابات 1–3 كلمات.',
              '- صاحب البيانات يصفها بأنها مناسبة للتصحيح المساعد Assissted وليس بديلًا للمراجع البشري.', '',
              '## Next experiments', '',
              '1. Error Analysis for incorrect, paraphrased and contradictory answers using manual adjudication.',
              '2. Build an independent 1–3 word human-scored dataset for MENTRIX.',
              '3. Evaluate actual Rubric+NLI and MiniLM on EXACT same split; report costs, review rate, and false approvals.',
              '4. Separately evaluate TrOCR CER/WER on independently transcribed handwriting samples.', '',
              'Outputs: `asag_s03_metrics.json`, `asag_s03_profile.json`, `asag_s03_splits.csv`, `asag_s03_test_predictions.csv`.', '']
    (output/'asag_s03_report_AR.md').write_text('\n'.join(lines),encoding='utf-8')
    from research.sprint3.render_report import render
    render(report, output/'asag_s03_report.html')
    return report


def main(argv=None):
    parser=argparse.ArgumentParser(description='MENTRIX Sprint 03 ASAG — real dataset benchmark')
    parser.add_argument('--input',type=Path,default=DEFAULT_DATASET)
    parser.add_argument('--output-dir',type=Path,default=DEFAULT_OUTPUT)
    parser.add_argument('--seed',type=int,default=SEED)
    args=parser.parse_args(argv)
    try:
        report=execute(args.input,args.output_dir,args.seed)
    except (OSError,ValueError,RuntimeError,ImportError,AssertionError) as error:
        print('BENCHMARK_FAILED:',error)
        return 1
    print('BENCHMARK_SUCCESS — Actual file:',args.input)
    print('Records:',report['dataset']['total_rows'],'Nonblank:',report['dataset']['human_scored_nonblank'])
    for method, m in sorted(report['method_summary'].items(),key=lambda kv:kv[1]['micro_test_mae']):
        print(f'{method:30s} MAE={m["micro_test_mae"]:.4f} QWK={m["pooled_test_qwk"]}')
    print('Report:',args.output_dir/'asag_s03_report_AR.md')
    return 0


if __name__=='__main__':
    raise SystemExit(main())
