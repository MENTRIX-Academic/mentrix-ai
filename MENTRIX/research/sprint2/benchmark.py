"""Reproducible, prompt-wise baseline comparison for human-scored ASAP-SAS.

Trains on Sprint 01 grouped train split; selects on validation; reports all
held-out test baselines *without* using test metrics for model selection.
No pretrained models or student private records are downloaded or shipped.
"""
from __future__ import annotations
import csv
import hashlib
import json
import math
from collections import defaultdict
from pathlib import Path
from datetime import datetime, timezone

import numpy as np
from sklearn.dummy import DummyRegressor
from sklearn.feature_extraction.text import CountVectorizer, TfidfVectorizer
from sklearn.linear_model import Ridge
from sklearn.pipeline import make_pipeline
from sklearn.metrics import cohen_kappa_score

BASELINES = (
    'mean', 'tfidf_word_ridge', 'tfidf_char_ridge',
    'token_overlap_knn', 'tfidf_word_knn', 'tfidf_char_knn',
)


def normalize(answer):
    return ' '.join(answer.casefold().split())


class SimilarityKNN:
    """Simple scored-example retrieval. No claim of reproducing historical models."""
    def __init__(self, method, k=3):
        self.method, self.k = method, k
        if method == 'token_overlap_knn':
            self.vectorizer = CountVectorizer(binary=True, token_pattern=r'(?u)\b\w+\b')
        elif method == 'tfidf_word_knn':
            self.vectorizer = TfidfVectorizer(ngram_range=(1,2), sublinear_tf=True)
        elif method == 'tfidf_char_knn':
            self.vectorizer = TfidfVectorizer(analyzer='char', ngram_range=(2,5), sublinear_tf=True)
        else:
            raise ValueError(method)

    def fit(self, answers, scores):
        self.train = self.vectorizer.fit_transform(answers)
        self.scores = np.asarray(scores, dtype=float)
        self.mean = float(np.mean(self.scores))
        self.train_sizes = np.asarray(self.train.sum(axis=1)).ravel() if self.method == 'token_overlap_knn' else None
        return self

    def predict(self, answers):
        X = self.vectorizer.transform(answers)
        output = np.empty(X.shape[0], dtype=float)
        for start in range(0, X.shape[0], 128):
            batch = X[start:start+128]
            sim = (batch @ self.train.T).toarray().astype(float)
            if self.method == 'token_overlap_knn':
                # Binary vectors: Jaccard = |A intersection B| / |A union B|
                sizes = np.asarray(batch.sum(axis=1)).ravel()
                denominator = sizes[:, None] + self.train_sizes[None, :] - sim
                sim = np.divide(sim, denominator, out=np.zeros_like(sim), where=denominator>0)
            for offset, similarities in enumerate(sim):
                # Zero similarity => no evidence; fallback to training mean.
                best = np.argpartition(similarities, -min(self.k,len(similarities)))[-min(self.k,len(similarities)):]
                weights = similarities[best]
                output[start+offset] = (float(np.dot(weights,self.scores[best])/weights.sum())
                                         if weights.sum()>0 else self.mean)
        return output


def model_factory(name):
    if name == 'mean':
        return DummyRegressor(strategy='mean')
    if name == 'tfidf_word_ridge':
        return make_pipeline(TfidfVectorizer(ngram_range=(1,2), sublinear_tf=True), Ridge(alpha=2))
    if name == 'tfidf_char_ridge':
        return make_pipeline(TfidfVectorizer(analyzer='char',ngram_range=(2,5),sublinear_tf=True),Ridge(alpha=2))
    return SimilarityKNN(name)


def vectors(rows, method):
    return [[0]]*len(rows) if method == 'mean' else [row['answer_text'] for row in rows]


def metrics(gold, prediction, score_range):
    gold = np.asarray(gold, dtype=float)
    raw = np.asarray(prediction, dtype=float)
    pred = np.clip(np.rint(raw), *score_range).astype(int)
    truth = np.asarray(gold, dtype=int)
    if not np.allclose(gold,truth):
        raise ValueError('Non-integer human scores: inspect score scale before QWK scoring')
    labels = list(range(score_range[0],score_range[1]+1))
    # For constant ratings cohen_kappa_score is undefined. Return null, not fake zero.
    qwk = None
    if len(set(truth.tolist()+pred.tolist()))>1:
        value = float(cohen_kappa_score(truth,pred,labels=labels,weights='quadratic'))
        if math.isfinite(value): qwk=round(value,5)
    return {'n':len(truth), 'mae':round(float(np.mean(np.abs(truth-pred))),5),
            'raw_mae':round(float(np.mean(np.abs(gold-raw))),5),
            'qwk':qwk, 'exact_match':round(float(np.mean(truth==pred)),5),
            'within_one':round(float(np.mean(np.abs(truth-pred)<=1)),5)}


def source_hash(path):
    h = hashlib.sha256()
    with Path(path).open('rb') as f:
        for chunk in iter(lambda: f.read(1024*1024), b''):h.update(chunk)
    return h.hexdigest()


def analyze(prepared_csv:Path, outdir:Path, original_source:Path|None=None):
    with Path(prepared_csv).open(encoding='utf-8-sig',newline='') as f:
        reader=csv.DictReader(f)
        fields={'sample_id','prompt_id','answer_text','human_score','split'}
        if not fields.issubset(reader.fieldnames or []):
            raise ValueError('Missing prepared CSV columns: '+str(fields-set(reader.fieldnames or [])))
        rows=list(reader)
    if not rows:raise ValueError('No rows found: no benchmark executed')
    ids=set(); groups=defaultdict(set); prompts=defaultdict(lambda:defaultdict(list))
    for row in rows:
        if row['split'] not in ('train','validation','test'):raise ValueError('Invalid split: '+row['split'])
        key=(row['prompt_id'],row['sample_id'])
        if key in ids:raise ValueError('Duplicate sample ID within prompt '+str(key))
        ids.add(key)
        groups[(row['prompt_id'],normalize(row['answer_text']))].add(row['split'])
        prompts[row['prompt_id']][row['split']].append(row)
    if any(len(s)>1 for s in groups.values()):
        raise ValueError('Duplicate normalized answer leaked across splits')
    if len(rows)<1000:
        raise ValueError('Dataset too small for a large-scale benchmark (<1000 rows): likely test fixture')
    results=[]; predictions=[]; metric_aggregator=defaultdict(lambda:defaultdict(list))
    for prompt, splitrows in sorted(prompts.items(),key=lambda kv:(len(kv[0]),kv[0])):
        if min(len(splitrows[split]) for split in ('train','validation','test'))<10:
            raise ValueError('Too few rows in split of prompt '+prompt)
        train, val, test=(splitrows[split] for split in ('train','validation','test'))
        ytrain=np.array([float(r['human_score']) for r in train])
        yval=np.array([float(r['human_score']) for r in val])
        ytest=np.array([float(r['human_score']) for r in test])
        if not np.all(np.isfinite(np.concatenate([ytrain,yval,ytest]))):raise ValueError('Non-finite labels')
        scale=(int(ytrain.min()),int(ytrain.max()))
        if scale[0]==scale[1] or not np.allclose(np.concatenate([ytrain,yval,ytest]),
                    np.rint(np.concatenate([ytrain,yval,ytest]))):
            raise ValueError('Invalid/constant integer score scale for prompt '+prompt)
        candidates={}
        for method in BASELINES:
            model=model_factory(method)
            model.fit(vectors(train,method),ytrain)
            valpred=model.predict(vectors(val,method))
            testpred=model.predict(vectors(test,method))
            valmetrics=metrics(yval,valpred,scale)
            testmetrics=metrics(ytest,testpred,scale)
            candidates[method]={'validation':valmetrics,'test':testmetrics}
            metric_aggregator[method]['mae'].append(testmetrics['mae'])
            metric_aggregator[method]['qwk'].append(testmetrics['qwk'])
            for item,score,pred in zip(test,ytest,testpred):
                rounded=int(np.clip(np.rint(pred),*scale))
                predictions.append({'prompt_id':prompt,'sample_id':item['sample_id'],
                                    'method':method,'gold_score':int(score),
                                    'predicted_score':rounded,'absolute_error':abs(rounded-int(score))})
        selected=min(BASELINES,key=lambda name:(candidates[name]['validation']['mae'],
                                    candidates[name]['validation']['raw_mae'],name))
        results.append({'prompt_id':prompt,
                        'rows':{s:len(splitrows[s]) for s in ('train','validation','test')},
                        'score_range_from_train':list(scale),
                        'selected_on_validation':selected,
                        'baselines':candidates})
    summary={name:{'average_test_mae':round(float(np.mean(metric_aggregator[name]['mae'])),5),
                    'average_test_qwk':round(float(np.mean([v for v in metric_aggregator[name]['qwk'] if v is not None])),5)
                        if any(v is not None for v in metric_aggregator[name]['qwk']) else None}
                 for name in BASELINES}
    manifest={'status':'EXECUTED_ON_LOCAL_FILE_SOURCE_NOT_INDEPENDENTLY_VERIFIED',
              'source':'Kaggle ASAP-SAS expected; verify provenance and competition permission',
              'source_file_sha256':source_hash(original_source) if original_source and original_source.is_file() else None,
              'prepared_file_sha256':source_hash(prepared_csv),
              'rows_total':len(rows),'prompts':len(prompts),
              'date_utc':datetime.now(timezone.utc).isoformat(),
              'grouped_duplicate_split':'normalized answer grouped inside each prompt; seed=42',
              'validation_policy':'select candidate with lowest validation rounded MAE, tie-break raw MAE',
              'test_policy':'evaluate every predetermined baseline once on held-out test for comparisons; never select with test',
              'methods_are_not_exact_historical_implementations':True,
              'limitations':['Prompt-specific models trained on labeled answers, not grading against approved university rubric.',
                             'Data answers usually ~50 words, not MENTRIX 1-3-word answers.',
                             'Shared writer identity unavailable: near-duplicates and writer leakage not excluded.',
                             'No OCR in this benchmark. No deployment/auto-publishing validated.'],
              'method_summary':summary,'per_prompt':results}
    outdir=Path(outdir); outdir.mkdir(parents=True,exist_ok=True)
    (outdir/'asap_s02_metrics.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2,allow_nan=False),encoding='utf-8')
    with (outdir/'asap_s02_test_predictions.csv').open('w',encoding='utf-8-sig',newline='') as f:
        writer=csv.DictWriter(f,fieldnames=['prompt_id','sample_id','method','gold_score','predicted_score','absolute_error'])
        writer.writeheader();writer.writerows(predictions)
    lines=['# MENTRIX | Sprint 02 — Short Answer Benchmark', '',
        '**Result status:** Executed on locally supplied data. Dataset provenance must be checked against the SHA-256 in JSON.',
        '', '> ⚠️ This does not validate 1–3-word grading, handwriting OCR, or unattended grade publishing.', '',
        'Dataset rows: **'+str(len(rows))+'**; prompts: **'+str(len(prompts))+'**.','',
        '| Method | Mean Test MAE across prompts ↓ | Mean Test QWK across prompts ↑ |',
        '|---|---:|---:|']
    for name,values in summary.items():
        lines.append(f"| {name} | {values['average_test_mae']:.5f} | {values['average_test_qwk'] if values['average_test_qwk'] is not None else 'N/A'} |")
    lines.extend(['','## Selected methods (validation only)','',
                 '| Prompt | Train | Val | Test | Selected | Test MAE | Test QWK |',
                 '|---|---:|---:|---:|---|---:|---:|'])
    for p in results:
        met=p['baselines'][p['selected_on_validation']]['test']
        lines.append(f"| {p['prompt_id']} | {p['rows']['train']} | {p['rows']['validation']} | {p['rows']['test']} | {p['selected_on_validation']} | {met['mae']:.5f} | {met['qwk'] if met['qwk'] is not None else 'N/A'} |")
    lines.extend(['','## Interpretation (Arabic)','',
                  '- دي **تجربة جديدة** مش نفس أرقام Work Wrap up؛ المقارنة المباشرة بينهم غير عادلة بسبب اختلاف البيانات.',
                  '- المقاييس مبنية على درجات بشرية على ASAP-SAS؛ لكن دي إجابات أطول من إجابات 1–3 كلمات عندنا.',
                  '- طرق similarity KNN تبحث عن إجابات بشرية مصححة داخل Train ولا تستخدم Approved Rubric.',
                  '- الاختيار من Validation فقط. عرض كل نتائج Test للتوثيق؛ ممنوع اختيار موديل جديد بالاعتماد على نتائج Test.',
                  '- لا يُستنتج من MAE/QWK السماح بنشر درجات الطلاب تلقائيًا.',
                  '- الخطوة التالية: rubric-based methods on the SAME split + independent MENTRIX 1–3-word set + error analysis.',
                  '', 'Outputs: `asap_s02_metrics.json` and `asap_s02_test_predictions.csv`.'])
    (outdir/'asap_s02_report.md').write_text('\n'.join(lines)+'\n',encoding='utf-8')
    return manifest
