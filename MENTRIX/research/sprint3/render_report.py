"""Standalone, printable HTML briefing of Sprint 03 results. No remote assets."""
from __future__ import annotations
from html import escape
from pathlib import Path


def render(report, target):
    profile = report['dataset']
    allresults = report['method_summary']
    ranked = sorted(allresults.items(), key=lambda v: v[1]['micro_test_mae'])
    selected = report['validation_selected_summary']
    def s(x):
        return escape(str(x))
    def fmt(x):
        return 'N/A' if x is None else f'{x:.4f}'
    rows = []
    bars = []
    top = max(v['micro_test_mae'] for _,v in ranked)
    for method, m in ranked:
        rows.append('<tr><td><code>'+s(method)+'</code></td><td>'+fmt(m['micro_test_mae'])+
                    '</td><td>'+fmt(m['pooled_test_qwk'])+'</td><td>'+f'{m["pooled_test_exact_match"]*100:.1f}%'+
                    '</td><td>'+s(m['heldout_n'])+'</td></tr>')
        # Lower MAE is better. Intentionally no scaled axis deception: show zero baseline and exact value.
        bars.append('<div class="barline"><span class="barlabel">'+s(method)+'</span><div class="barbg"><div class="bar" style="width:'+
                    f'{100*m["micro_test_mae"]/top:.1f}%'+ '"></div></div><b>'+fmt(m['micro_test_mae'])+'</b></div>')
    perrows=[]
    for p in report['per_prompt']:
        met=p['baselines'][p['selected_on_validation']]['test']
        perrows.append('<tr><td>'+s(p['prompt_id'])+'</td><td>'+s(p['rows']['train'])+' / '+s(p['rows']['validation'])+' / '+s(p['rows']['test'])+
                       '</td><td><code>'+s(p['selected_on_validation'])+'</code></td><td>'+fmt(met['mae'])+'</td><td>'+fmt(met['qwk'])+'</td></tr>')
    html = f'''<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>MENTRIX | Sprint 03 — ASAG Research Benchmark</title>
<style>
:root{{--cream:#faf8ef;--card:#fff;--pine:#184c3c;--accent:#2b735a;--text:#243c32;--muted:#65766d;--line:#dfe7dd;--pale:#edf6ef}}*{{box-sizing:border-box}}body{{margin:0;background:var(--cream);font-family:"Segoe UI",Tahoma,Arial,sans-serif;color:var(--text);line-height:1.65}}header{{background:linear-gradient(115deg,#184c3c,#2f7257);color:white;padding:48px max(24px,calc((100vw - 1040px)/2));}}header small{{color:#b9dbc9;letter-spacing:2px}}header h1{{font-size:clamp(30px,4vw,44px);margin:8px 0}}header p{{color:#e3efe8;margin:0;max-width:800px}}main{{max-width:1100px;padding:30px 24px 65px;margin:auto}}.eyebrow{{font-size:13px;text-transform:uppercase;letter-spacing:1px;color:var(--accent);font-weight:700}}h2{{margin:0 0 15px;font-size:23px;color:var(--pine)}}h3{{font-size:17px;color:var(--pine)}}.grid{{display:grid;grid-template-columns:repeat(4,minmax(0,1fr));gap:12px;margin-bottom:18px}}.stat,.panel{{border:1px solid var(--line);border-radius:16px;background:var(--card);padding:22px}}.stat strong{{display:block;font-size:31px;line-height:1.1;color:var(--pine)}}.stat span{{font-size:13px;color:var(--muted)}}.panel{{margin:16px 0 22px;overflow:auto}}.highlight{{background:#f0f6ed;border-right:4px solid var(--accent);padding:14px 18px;border-radius:8px;margin:17px 0}}.warning{{background:#fcf5e8;border-right:4px solid #aa854a;padding:15px 18px;border-radius:8px;margin:17px 0}}table{{border-collapse:collapse;width:100%;direction:ltr;text-align:left;font-variant-numeric:tabular-nums}}th,td{{border-bottom:1px solid var(--line);padding:10px 12px;white-space:nowrap}}th{{background:#f3f7f3;color:#284c3e;font-size:13px}}tr:hover td{{background:#fbfdfb}}code{{font-family:Consolas,monospace;font-size:12px;color:#355f4d}}.barline{{display:grid;grid-template-columns:215px 1fr 60px;direction:ltr;align-items:center;gap:12px;font-size:12px;margin:10px 0}}.barlabel{{white-space:nowrap;overflow:hidden;text-overflow:ellipsis}}.barbg{{background:#edf1ed;height:14px;border-radius:20px;overflow:hidden}}.bar{{height:100%;background:#3c9674;border-radius:20px}}.barline b{{color:#245942;font-variant-numeric:tabular-nums}}ul{{padding-right:22px}}li{{margin:7px 0}}.foot{{font-size:12px;color:var(--muted);overflow-wrap:anywhere}}a{{color:var(--accent)}}@media(max-width:700px){{.grid{{grid-template-columns:repeat(2,minmax(0,1fr))}}.barline{{grid-template-columns:130px 1fr 50px;gap:8px;font-size:10px}}.stat strong{{font-size:24px}}header{{padding:32px 22px}}main{{padding:20px 12px}}.panel{{padding:14px}}}}@media print{{header{{background:#fff;color:#143b2d;padding:20px 0}}header p{{color:#244e3c}}body{{background:#fff}}.panel,.stat{{break-inside:avoid}}}}
</style></head><body><header><small>MENTRIX · AI RESEARCH / SPRINT 03</small><h1>ASAG — Grading Benchmark</h1><p>تقرير تشغيل فعلي على البيانات المرفوعة. للمقارنة البحثية فقط؛ لا يسمح باعتماد درجات الطلاب تلقائيًا أو بإثبات دقة الـOCR.</p></header><main>
<div class="eyebrow">Dataset overview</div><section class="grid"><div class="stat"><strong>{profile['total_rows']}</strong><span>إجابات بشرية التقييم</span></div><div class="stat"><strong>{profile['human_scored_nonblank']}</strong><span>إجابة داخل الاختبار النصي</span></div><div class="stat"><strong>{profile['question_count']}</strong><span>سؤالًا مختلفًا</span></div><div class="stat"><strong>{profile['blank_score_0']}</strong><span>إجابة فارغة مستبعدة من ML</span></div></section>
<div class="warning"><b>مهم:</b> الداتا تحتوي على إجابات طويلة بمتوسط {profile['mean_words_nonblank']:.2f} كلمة، بينما MENTRIX يستهدف أيضًا إجابات 1–3 كلمات. النموذج لا يتعامل مع الصور أو الـOCR هنا، والمصحح البشري في المصدر واحد فقط.</div>
<section class="panel"><h2>المقارنة بين 7 طرق — Test Set</h2><p>الأفضل في MAE هو الأقل، والأفضل في QWK هو الأعلى. دي نتائج على 129 إجابة غير فارغة في الـTest، ونفس التقسيم لكل الطرق.</p><div>{''.join(bars)}</div><table><thead><tr><th>Method</th><th>Micro MAE ↓</th><th>Pooled QWK ↑</th><th>Exact Match ↑</th><th>Test N</th></tr></thead><tbody>{''.join(rows)}</tbody></table><p class="foot">جميع الدرجات من 0 إلى 2. Method names الجديدة لا تُعتبر تنفيذًا مطابقًا لـ MiniLM / NLI / Rubric + NLI المذكورين في التقرير السابق.</p></section>
<section class="panel"><h2>اختيار الطريقة بناءً على Validation</h2><div class="highlight"><b>Validation-selected per question:</b> Test MAE = {fmt(selected['micro_test_mae'])} • Pooled QWK = {fmt(selected['pooled_test_qwk'])} • Exact Match = {100*selected['exact_match']:.1f}%. أفضل طريقة ثابتة على هذه الـTest اختلفت عن اختيار Validation؛ وده مؤشر لتذبذب النتائج بسبب صِغر الداتا.</div><table><thead><tr><th>Q</th><th>Train / Val / Test</th><th>Selected on Val</th><th>Test MAE</th><th>Test QWK</th></tr></thead><tbody>{''.join(perrows)}</tbody></table><p class="foot">QWK ممكن يكون N/A عند غياب التنوع في درجات جزء الاختبار لسؤال معين.</p></section>
<section class="panel"><h2>ما الذي نستنتجه؟</h2><ul><li>شغّلنا فعليًا 7 طرق خفيفة على Dataset حقيقية بدرجات بشرية؛ لم ندرّب Transformer أو نستخدم صورة خط يد.</li><li>تقسيم كل سؤال لا يسمح بتطابق نفس الإجابة حرفيًا بين التدريب والتحقق والاختبار؛ لا نملك Student ID لضمان الفصل بين الطلاب عبر الأسئلة.</li><li>39 إجابة فارغة درجتها صفر؛ اتعاملنا معاها كحالات Rule-Based منفصلة بدون رفع نتيجة ML ظاهريًا.</li><li>كل سؤال لديه 27–38 إجابة غير فارغة تقريبًا، فنتائج QWK للسؤال الواحد غير مستقرة.</li><li>ممنوع مقارنة MAE هنا بقيم <i>Work Wrap up</i> مباشرةً؛ البيانات وسُلَّم الدرجات مختلفان.</li></ul></section>
<section class="panel"><h2>الخطوة البحثية التالية</h2><ol><li>تحليل أخطاء الإجابات المتناقضة والمعاد صياغتها، بإشراف بشري.</li><li>إنشاء Test Set مستقل لإجابات MENTRIX من 1–3 كلمات.</li><li>اختبار MiniLM وRubric + NLI على <b>نفس</b> Splits مع قياس معدل طلب مراجعة المعيد.</li><li>تجربة OCR بشكل منفصل باستخدام CER / WER ونصوص بشرية مرجعية.</li></ol></section><p class="foot">Source: <a href="https://github.com/DigiKlausur/ASAG-Dataset">DigiKlausur ASAG-Dataset</a> · File SHA-256: {s(profile['source_file_sha256'])}. This report contains no student answers. Generated from the user's provided dataset with seed {report['seed']}.</p></main></body></html>'''
    Path(target).write_text(html, encoding='utf-8')
