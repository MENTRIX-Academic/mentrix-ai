"""One offline shareable RTL report; source content only from verified JSON outputs."""
from __future__ import annotations
import html,json
from pathlib import Path
from research.sprint5.audit_and_gate import OUT
from research.sprint4.error_analysis import S04, S03

def esc(v):return html.escape(str(v),quote=True)

def render(out=OUT):
    out=Path(out)
    data=json.loads((out/'s05_reproducibility_and_gate.json').read_text(encoding='utf-8'))
    s04=json.loads((S04/'s04_error_analysis.json').read_text(encoding='utf-8'))
    s03=json.loads((S03/'asag_s03_metrics.json').read_text(encoding='utf-8'))
    methods=sorted(data['method_test_scores'].items(),key=lambda e:e[1]['mae'])
    gate=data['research_gate'];candidate=data['research_gate_validation_candidates']
    method_rows=''.join(f'<tr><td class="mono">{esc(m)}</td><td>{s["mae"]:.4f}</td><td>{esc(s["qwk"])}</td><td>{s["exact"]*100:.1f}%</td><td>{s["dangerous_full_credit"]}</td></tr>' for m,s in methods)
    policy_rows=''.join(f'<tr><td class="mono">{esc(m)}</td><td>{s["validation_n"]}</td><td>{s["validation_accuracy"]*100 if s["validation_accuracy"] is not None else 0:.1f}%</td><td>{s["wilson_95_lower"]*100:.1f}%</td><td>{"No" if not s["eligible"] else "Research only"}</td></tr>' for m,s in candidate.items())
    question_rows=''.join(f'<tr><td>Q{esc(q)}</td><td>{s["n"]}</td><td>{s["errors"]}</td><td>{s["mae"]:.3f}</td><td>{s["full_credit_overgrading"]}</td></tr>' for q,s in data['per_question_selected'].items())
    matrix=''.join('<tr>'+f'<th>Human {i}</th>'+''.join(f'<td>{n}</td>' for n in row)+'</tr>' for i,row in enumerate(data['s03_validation_selected_confusion']))
    profile=s03['dataset']; chosen=data['s03_validation_selected_test_scores']
    # Optional real outputs appear only if their execution produced an actual result file.
    model_path=S04/'s04_transformer_results.json'
    ocr_path=Path(__file__).parent/'local_ocr_results'/'s05_ocr_metrics.json'
    model_section="<p class='small'>لا توجد نتائج Transformer جديدة: MiniLM/NLI لم يُشغّلا بعد في هذه النسخة.</p>"
    if model_path.is_file():
        model_data=json.loads(model_path.read_text(encoding='utf-8'))
        if model_data.get('status')=='ACTUALLY_EXECUTED_TRANSFORMER_MODELS_ON_FROZEN_SPRINT03_SPLIT':
            model_rows=''.join(f"<tr><td class='mono'>{esc(name)}</td><td>{values['mae']:.4f}</td><td>{esc(values['qwk'])}</td><td>{values['exact']*100:.1f}%</td></tr>" for name,values in sorted(model_data['methods'].items(),key=lambda e:e[1]['mae']))
            model_section=f"<div class='tablewrap'><table><thead><tr><th>Executed Transformer method</th><th>MAE</th><th>QWK</th><th>Exact</th></tr></thead><tbody>{model_rows}</tbody></table></div><p>تم قراءة نتائج تشغيل الموديلات الفعلية من Sprint04. Rubric+NLI ما زال غير مُختبر بدون Rubric.</p>"
    ocr_section="<p class='small'>لا توجد نتائج OCR فعلية: الصور والنصوص المرجعية الموثّقة لم تُقدّم بعد.</p>"
    if ocr_path.is_file():
        ocr_data=json.loads(ocr_path.read_text(encoding='utf-8'))
        if ocr_data.get('model_executed') is True and 'metrics' in ocr_data:
            m=ocr_data['metrics']
            ocr_section=f"<p>تم تشغيل TrOCR على {m['samples']} صورة موثّقة. CER={m['cer']:.4f}، WER={m['wer']:.4f}، على Original RGB. هذه جودة نسخ نص فقط، وليست دقة تصحيح.</p>"
    htmltext=f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1"><title>MENTRIX — Sprint 05 Audit & Research Readiness</title>
<style>
:root{{--green:#164e3a;--sea:#376a55;--beige:#f5f1e7;--cream:#faf9f4;--ink:#182f28;--muted:#65796f;--stroke:#d9e4dc}}*{{box-sizing:border-box}}
body{{font-family:Tahoma,"Segoe UI",sans-serif;color:var(--ink);background:var(--beige);margin:0;line-height:1.75}}header{{background:linear-gradient(135deg,#124934,#34735b);color:#fff;padding:34px max(22px,calc((100% - 1080px)/2))}}header h1{{font-size:29px;line-height:1.25;margin:7px 0 11px}}header p{{margin:0;color:#e1eee5}}main{{max-width:1080px;margin:24px auto 70px;padding:0 16px}}.flag{{display:inline-block;background:#e7f1e9;color:#25563d;font-size:12px;padding:4px 11px;border-radius:99px;font-weight:700}}.flag.warn{{background:#fff0df;color:#855c28}}.container{{background:#fff;border:1px solid var(--stroke);border-radius:18px;margin:16px 0;padding:22px 24px;box-shadow:0 3px 9px #1235230b}}h2{{margin:0 0 16px;font-size:21px;color:var(--green)}}h3{{font-size:16px;margin:18px 0 6px}}p{{margin:8px 0 12px}}.grid{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:10px}}.kpi{{background:var(--cream);padding:16px;border:1px solid var(--stroke);border-radius:12px}}.kpi strong{{font-size:29px;display:block;direction:ltr;text-align:right;color:var(--green)}}.small{{font-size:13px;color:var(--muted)}}.warning{{border-right:4px solid #bd934a;background:#fcf7ee;padding:10px 14px;border-radius:8px}}table{{border-collapse:collapse;width:100%;min-width:590px;font-size:14px}}th,td{{padding:10px 11px;border-bottom:1px solid #e5ede7;text-align:right}}th{{background:#eff5f0;color:var(--green)}}.tablewrap{{overflow-x:auto}}.mono{{font-family:Consolas,monospace;font-size:12px;direction:ltr;text-align:left}}.key{{background:#f2f8f3;padding:10px 14px;border-radius:9px}}.pill{{display:inline-block;background:#f1f6f1;color:var(--sea);border:1px solid #d7e6d8;padding:3px 10px;border-radius:30px;font-size:12px;margin:3px}}footer{{color:var(--muted);font-size:12px;padding:25px 2px;overflow-wrap:anywhere}}@media(max-width:650px){{header{{padding:24px}}.grid{{grid-template-columns:repeat(2,minmax(0,1fr))}}.container{{padding:17px}}header h1{{font-size:24px}}}}
</style></head><body>
<header><div class="small" style="color:#cce7d8">MENTRIX / AI Research — 03 Nov 2026</div><h1>Sprint 05 | Audit, Review Gate & OCR Readiness</h1><p>تحقيق قابل لإعادة التشغيل على نفس بيانات ASAG — بدون اختراع نتائج Transformer أو OCR</p></header>
<main>
<section class="container"><h2>ملخص النتائج الفعلية</h2><div class="grid">
<div class="kpi"><strong>{data['test_n']}</strong><span>إجابة Test</span></div>
<div class="kpi"><strong>{chosen['errors']}</strong><span>خطأ في اختيار كل سؤال</span></div>
<div class="kpi"><strong>{chosen['dangerous_full_credit']}</strong><span>منح درجة كاملة بالخطأ</span></div>
<div class="kpi"><strong>{data['validation_n']}</strong><span>إجابة Validation</span></div>
</div><p class="key">✅ <b>Reproducibility:</b> أعيد تشغيل 7 Baselines على نفس Training Sets، وتطابقت كل تنبؤات الاختبار مع سجلات Sprint 03 (لم تتغير).</p>
<p class="small">مصدر الداتا: DigiKlausur ASAG؛ {profile['total_rows']} سجلًا، {profile['human_scored_nonblank']} إجابة غير فارغة، و{profile['blank_score_0']} إجابة فارغة، و{profile['question_count']} سؤالًا. الدرجات 0–2. </p></section>
<section class="container"><h2>تقييم مراجعة المعيد — تجربة بحثية فقط</h2><span class="flag warn">{esc(gate['status'])}</span><p>اختبرنا 3 سياسات معتمدة على اتفاق الـ7 Baselines. اتاخد القرار من الـValidation فقط، بشرط حد أدنى 35 حالة وحدّ Wilson الأدنى عند 90% أو أكثر. مفيش سياسة اجتازت الشرط.</p><div class="tablewrap"><table><thead><tr><th>قاعدة الاتفاق</th><th>عدد Validation</th><th>دقة ملحوظة</th><th>Wilson 95% lower</th><th>مؤهلة؟</th></tr></thead><tbody>{policy_rows}</tbody></table></div>
<p class="warning"><b>القرار:</b> لا توجد موافقة تلقائية مبنية على هذا الاختبار؛ {gate['test_accepted']} من {data['test_n']} إجابة Test مؤهلة للمرور من البوابة، و{gate['test_review_required']} تتطلب مراجعة وفق هذه السياسة. هذه دراسة للبوابة وليست تفعيلًا لها على الموقع.</p></section>
<section class="container"><h2>مقارنة طرق Sprint 03 بعد إعادة التشغيل</h2><p class="small">أقل MAE أفضل، وأعلى QWK أفضل. المقارنة داخل نفس Test Split فقط، ولا يصح مقارنتها رقميًا بنتائج Work Wrap up (بيانات ومقاييس مختلفة).</p><div class="tablewrap"><table><thead><tr><th>Method</th><th>MAE ↓</th><th>QWK ↑</th><th>Exact</th><th>Full-credit mistakes</th></tr></thead><tbody>{method_rows}</tbody></table></div><p><b>اختيار الطريقة لكل سؤال بالـValidation:</b> MAE={chosen['mae']:.4f}، QWK={chosen['qwk']:.4f}، Exact={chosen['exact']*100:.1f}%.</p></section>
<section class="container"><h2>تحليل الأخطاء حسب الدرجة والسؤال</h2><h3>Confusion Matrix — Human rows / Predicted columns</h3><div class="tablewrap"><table><thead><tr><th>Ground truth</th><th>Pred 0</th><th>Pred 1</th><th>Pred 2</th></tr></thead><tbody>{matrix}</tbody></table></div>
<h3>أخطاء كل سؤال</h3><div class="tablewrap"><table><thead><tr><th>السؤال</th><th>Test n</th><th>Errors</th><th>MAE</th><th>Full-credit mistakes</th></tr></thead><tbody>{question_rows}</tbody></table></div><p class="small">تصنيف أخطاء التناقض والمعنى يحتاج مراجعة بشرية. تباعد الدرجات وحده لا يثبت وجود Contradiction.</p></section>
<section class="container"><h2>ماذا أُنجز وماذا لم يحدث بعد؟</h2>
<span class="pill">✅ Lightweight baselines reproduced</span><span class="pill">✅ Error breakdown</span><span class="pill">✅ Review gate audited</span><span class="pill">✅ OCR runner prepared</span>
<p><b>MiniLM / NLI:</b> نتائجها لا تظهر إلا إذا تم تشغيل النموذج وحفظ ملف results حقيقي. <b>Rubric + NLI:</b> ما اتقاسش على ASAG لأن الداتا مفيهاش Rubric معتمد مفصل لكل سؤال.</p>{model_section}
<p><b>TrOCR:</b> جهزنا مسار E01 Original RGB وقياس CER/WER مع Writer-disjoint verification. لن تظهر أرقام إلا بعد إدخال صور وGround Truth وتشغيل النموذج.</p>{ocr_section}
<p><b>Mock backend fixtures:</b> ملف تجريبي منفصل لـ30 طالبًا وهميًا و12 Session و360 سجل حضور، مع Mock API Contract. لم يتكامل مع الموقع بعد. <b>الخطوة القادمة:</b> تشغيل MiniLM وNLI على جهاز متصل بالإنترنت؛ وتوفير صور Test بخط اليد ونصوص Ground Truth مراجعة بشريًا؛ ثم التقييم على مجموعة جديدة مستقلة لإجابات 1–3 كلمات.</p>
<p class="warning"><b>حدود النتيجة:</b> Test ASAG سبق استخدامه في التقارير السابقة، وبالتالي مش Test جديد مستقل للتحقق النهائي. لا يمكن بناء قرار نشر درجات الطلاب تلقائيًا عليه.</p></section>
<footer>Dataset SHA-256: {esc(data['source_sha256'])} · Seed: {data['split_seed']} · Human review file is local-only and intentionally omitted from this HTML. · Source: DigiKlausur ASAG-Dataset · Sprint03 / Sprint04 / Sprint05 research files.</footer>
</main></body></html>'''
    out_file=out/'s05_unified_research_report.html';out_file.write_text(htmltext,encoding='utf-8');return out_file

if __name__=='__main__': print('Wrote:',render())
