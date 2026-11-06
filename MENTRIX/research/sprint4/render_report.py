"""Offline report: score-based Sprint04 error audit; no raw student answers printed."""
import html, json
from pathlib import Path
from research.sprint4.error_analysis import S04


def render(source=S04,output=None):
    source=Path(source)
    data=json.loads((source/'s04_error_analysis.json').read_text(encoding='utf-8'))
    rich=source/'s04_transformer_results.json'
    transformer=json.loads(rich.read_text(encoding='utf-8')) if rich.exists() else None
    def esc(x):return html.escape(str(x))
    def fmt(x):return '—' if x is None else f'{x:.4f}'
    methods=sorted(data['s03_all_methods'].items(),key=lambda a:a[1]['mae'])
    baseline_rows=''.join(f'<tr><td><code>{esc(name)}</code></td><td>{fmt(m["mae"])}</td><td>{fmt(m["qwk"])}</td><td>{m["exact"]:.1%}</td><td>{m["dangerous_full_credit"]}</td></tr>' for name,m in methods)
    qs=''.join(f'<tr><td>Q{esc(r["question_id"])}</td><td>{r["n"]}</td><td>{fmt(r["mae"])}</td><td>{r["errors"]}</td><td>{r["dangerous_full_credit"]}</td></tr>' for r in sorted(data['per_question_validation_selected'],key=lambda r:-r['mae']))
    selected=data['s03_validation_selected']
    conf=selected['confusion_gold_rows_pred_cols']
    matrix=''.join('<tr><th>Gold '+str(i)+'</th>'+''.join('<td>'+str(v)+'</td>' for v in line)+'</tr>' for i,line in enumerate(conf))
    if transformer:
        rows=''.join(f'<tr><td>{esc(k)}</td><td>{fmt(v["mae"])}</td><td>{fmt(v["qwk"])}</td><td>{v["exact"]:.1%}</td><td>{v["dangerous_full_credit"]}</td></tr>' for k,v in sorted(transformer['methods'].items(),key=lambda r:r[1]['mae']))
        models=f'<h2>Transformer models — EXECUTED ON LOCAL COMPUTER</h2><p>These results are from actual downloaded checkpoints, independently generated in this run. No fine-tuning.</p><table><thead><tr><th>Method</th><th>MAE ↓</th><th>QWK ↑</th><th>Exact</th><th>False full credit</th></tr></thead><tbody>{rows}</tbody></table><p><b>Note:</b> NLI reference features are not an actual rubric scorer. Rubric+NLI remains pending human-approved rubric.</p>'
    else:
        models='<h2>Transformer models — NOT RUN YET</h2><p>MiniLM and NLI require downloading official model weights using <code>RUN_SPRINT04_MODELS.bat</code> on a computer with internet. <b>No new MiniLM/NLI accuracy results are claimed in this report.</b></p>'
    page=f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MENTRIX | Sprint 04 Research</title><style>
    body{{font-family:Segoe UI,Tahoma,Arial,sans-serif;background:#f8f6ef;color:#183c2b;margin:0;line-height:1.85}}
    main{{max-width:1060px;margin:40px auto;padding:0 20px 55px}}h1{{font-size:32px;margin:0}}h2{{font-size:22px;border-bottom:1px solid #dae5dc;padding-bottom:9px;margin-top:36px}}
    .muted{{color:#587565}}.hero{{background:#fdfefb;border:1px solid #d7e5d8;border-radius:20px;padding:30px}}
    .cols{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-top:22px}}.stat{{background:#ebf3ec;border-radius:14px;padding:15px}}.stat strong{{display:block;font-size:27px;line-height:1.1}}
    table{{border-collapse:collapse;width:100%;margin:10px 0 30px;background:white;direction:ltr;text-align:left}}td,th{{border-bottom:1px solid #e6ece7;padding:10px 12px;font-size:14px}}th{{background:#e7efe8}}.scroll{{overflow:auto}}
    .warning{{padding:15px 18px;border-inline-start:4px solid #be8a47;background:#fff6e9;border-radius:6px}}code{{font-family:Consolas,monospace;font-size:13px}}li{{margin:8px 0}}
    @media(max-width:680px){{.cols{{grid-template-columns:repeat(2,minmax(0,1fr))}}main{{margin-top:16px}}}}
    </style></head><body><main>
    <div class="hero"><p class="muted">MENTRIX · Research & Development · Sprint 04</p><h1>تحليل الأخطاء ومقارنة النماذج</h1>
    <p>تحليل أعاد حساب أخطاء Sprint 03 من <b>نتائج محفوظة فعلًا</b> على نفس 129 إجابة. لم تُستخدم إجابات اختبار جديدة ولم يتغير الموقع.</p>
    <div class="cols"><div class="stat"><strong>{selected['n']}</strong>Test answers</div><div class="stat"><strong>{selected['errors']}</strong>خطأ</div><div class="stat"><strong>{selected['mae']:.3f}</strong>MAE</div><div class="stat"><strong>{selected['dangerous_full_credit']}</strong>False full credit</div></div></div>
    <h2>مهم نفهم الأرقام صح</h2><p>النتائج هنا لطريقة اختيار Baseline لكل سؤال بناءً على Validation. أخطاء الدرجات <b>لا تثبت</b> تلقائيًا وجود Contradiction أو Paraphrase؛ لازم مراجعة بشرية.</p>
    <p class="warning"><b>Auto-publish is disabled.</b> داتا ASAG دي إجابات إنجليزية طويلة ومكتوبة إلكترونيًا، وكل سؤال اتصحح بواسطة مُقيِّم بشري واحد؛ ليست اختبارًا للخط اليدوي أو إجابات MENTRIX من 1–3 كلمات.</p>
    <h2>All Sprint03 methods — same held-out test</h2><div class="scroll"><table><thead><tr><th>Baseline</th><th>MAE ↓</th><th>QWK ↑</th><th>Exact ↑</th><th>False full credit ↓</th></tr></thead><tbody>{baseline_rows}</tbody></table></div>
    <h2>Confusion matrix — validation-selected method</h2><p>الصف: الدرجة البشرية (0، 1، 2). العمود: درجة النظام (0، 1، 2).</p><div class="scroll"><table><thead><tr><th>Gold / Pred</th><th>0</th><th>1</th><th>2</th></tr></thead><tbody>{matrix}</tbody></table></div>
    <h2>Questions requiring focused review</h2><div class="scroll"><table><thead><tr><th>Question</th><th>Test n</th><th>MAE ↓</th><th>Errors</th><th>False full credit</th></tr></thead><tbody>{qs}</tbody></table></div>
    {models}
    <h2>Next research actions</h2><ol>
    <li>افتحي <code>s04_human_review_template_LOCAL_ONLY.csv</code>؛ المراجعة تفرّق بين Contradiction وParaphrase وIncomplete وOff-topic وLabel issue.</li>
    <li>شغّلي الـMiniLM الحقيقي أولًا؛ اختبري NLI في خطوة تانية على نفس الـSplit، بدون تغيير الداتا.</li>
    <li>لو عايزين اختبار Rubric+NLI فعلي، لازم Rubric بشرية معتمدة لكل سؤال. ملف ASAG لا يحتوي هذه المعايير.</li>
    <li>لا تستخدمي الأرقام لإعلان نموذج جاهز للنشر، ولا للمقارنة الرقمية مع Work Wrap up: الداتا ومقياس الدرجات مختلفان.</li>
    </ol><p class="muted">Local offline report • No student-answer text embedded • Dataset hash: <code>{data['dataset_hash'][:20]}…</code></p>
    </main></body></html>'''
    path=Path(output or source/'s04_error_analysis_report.html')
    path.write_text(page,encoding='utf-8')
    return path

if __name__=='__main__':print(render())
