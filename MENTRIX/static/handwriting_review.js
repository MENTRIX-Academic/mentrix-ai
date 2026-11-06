'use strict';
/* Staff-only visual review; boxes are suggestions, not proof of OCR correctness. */
window.mountHandwritingReview = function(container, draft, questions, regionsBox, paperId) {
 const escapeHtml = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
 const lines = Array.isArray(draft.lines) ? draft.lines : [];
 const ids = (questions||[]).map(x=>x.id);
 const root = document.createElement('div'); root.className = 'space-top';
 const layout = (draft.page_layout || []).map(x=>`Page ${x.page+1}: ${escapeHtml(x.method||'unknown')} ${x.angle_degrees?`• deskew ${escapeHtml(x.angle_degrees)}°`:''}`).join(' | ');
 const qualityCount = lines.filter(x=>(x.quality?.flags||[]).length).length;
 root.innerHTML = `<p class="smaller"><b>Visual QA:</b> ${escapeHtml(layout)}. ${qualityCount} flagged line(s); OCR text is not verified.</p>
   <details class="space-top"><summary><b>Compare original handwriting with OCR — ${lines.length} line crops</b></summary>
    <div style="max-height:550px;overflow:auto;padding:10px 0;display:grid;gap:10px">
      ${lines.map((line,i)=>`<div style="border:1px solid #dbe6d9;border-radius:10px;padding:9px;background:white">
       <div class="smaller"><b>Line ${i+1}</b> • Page ${line.page+1} • ${escapeHtml(line.question_id||'UNASSIGNED')}${line.rotation_degrees?` • deskew ${escapeHtml(line.rotation_degrees)}°`:''}</div>
       ${line.crop_url?`<img loading="lazy" alt="Original handwriting crop, line ${i+1}" src="${escapeHtml(line.crop_url)}" style="display:block;max-width:100%;max-height:140px;margin:7px 0;border:1px solid #e1e5dc;background:white">`:''}
       <div style="white-space:pre-wrap;overflow-wrap:anywhere">${escapeHtml(line.raw_text||'[blank recognition]')}</div>
       ${(line.alternatives||[]).map(a=>`<div class="smaller">Alternative (${escapeHtml(a.preprocess)}): ${escapeHtml(a.text)}</div>`).join('')}
       ${(line.quality?.flags||[]).map(f=>`<div class="smaller" style="color:#985521">⚠ ${escapeHtml(f)}</div>`).join('')}
       </div>`).join('')}
    </div>
   </details>
   <details class="space-top"><summary><b>Mark question areas directly on the image (no JSON typing)</b></summary>
     <p class="smaller">Choose a question, then drag across its handwriting to draw a rectangle. Add one rectangle per answer region; you can add more than one per question. Click <b>Read handwriting with TrOCR</b> again to use these regions. Review all detected lines before grading.</p>
     <div class="inline-form"><label>Question <select id="hwVisualQuestion">${ids.map(id=>`<option value="${escapeHtml(id)}">${escapeHtml(id)}</option>`).join('')}</select></label>
      <button type="button" class="btn outline" id="hwVisualUndo">Undo last box</button>
      <button type="button" class="btn outline" id="hwVisualClear">Clear boxes</button></div>
     <p id="hwVisualMessage" class="smaller"></p><div id="hwPageFigures"></div>
   </details>`;
 container.appendChild(root);
 const qs=root.querySelector('#hwVisualQuestion');const msg=root.querySelector('#hwVisualMessage');
 const figures=root.querySelector('#hwPageFigures');
 function getRegions() {
   try {const parsed=JSON.parse(regionsBox.value||'[]');return Array.isArray(parsed)?parsed:[];}
   catch (_) {msg.textContent='Invalid region JSON. Fix or clear it first.';return null;}
 }
 if (!regionsBox.value.trim() && (draft.manual_regions||[]).length) regionsBox.value=JSON.stringify(draft.manual_regions,null,2);
 function setRegions(rows) {regionsBox.value=rows.length?JSON.stringify(rows,null,2):'';paint();msg.textContent=`${rows.length} region(s) selected. Rerun OCR to apply them.`;}
 function paint() {
    const selected=getRegions();if(!selected)return;
    root.querySelectorAll('[data-drawable]').forEach(wrapper=>{
       wrapper.querySelectorAll('.hw-region-outline').forEach(el=>el.remove());
       const img=wrapper.querySelector('img');const page=Number(img.dataset.page);
       for(const r of selected.filter(x=>x.page===page)) {
         if (!img.naturalWidth || !img.naturalHeight)continue;
         const mark=document.createElement('div');mark.className='hw-region-outline';
         mark.style.cssText=`position:absolute;pointer-events:none;box-sizing:border-box;border:2px solid #db6c38;background:#db6c3829;left:${r.x0/img.naturalWidth*100}%;top:${r.y0/img.naturalHeight*100}%;width:${(r.x1-r.x0)/img.naturalWidth*100}%;height:${(r.y1-r.y0)/img.naturalHeight*100}%;`;
         mark.title=String(r.question_id);wrapper.appendChild(mark);
       }
    });
 }
 for(let page=0;page<(draft.pages||0);page++) {
  const url=draft.page_image_urls?.[page];if(!url)continue;
  const detail=document.createElement('details'); detail.className='space-top';if(page===0)detail.open=true;
  detail.innerHTML=`<summary>Page ${page+1} — select areas</summary><div data-drawable style="position:relative;display:block;width:min(100%,760px);margin:8px 0;line-height:0"><img data-page="${page}" src="${escapeHtml(url)}" alt="Original page ${page+1} for marking question regions" draggable="false" style="display:block;width:100%;height:auto;touch-action:none;cursor:crosshair;border:1px solid #c6d4c8"></div>`;
  figures.appendChild(detail);
  const wrapper=detail.querySelector('[data-drawable]'),img=wrapper.querySelector('img');
  let from=null,temp=null;
  function pixelPoint(e) {const box=img.getBoundingClientRect();return {
   x:Math.max(0,Math.min(img.naturalWidth,Math.round((e.clientX-box.left)*img.naturalWidth/box.width))),
   y:Math.max(0,Math.min(img.naturalHeight,Math.round((e.clientY-box.top)*img.naturalHeight/box.height)))
  };}
  img.addEventListener('pointerdown',e=>{if(!qs?.value || !img.naturalWidth)return;
    from=pixelPoint(e);img.setPointerCapture(e.pointerId);
    temp=document.createElement('div');temp.style.cssText='position:absolute;pointer-events:none;border:2px dashed #1b754e;background:#1b754e22;box-sizing:border-box;';wrapper.appendChild(temp);e.preventDefault();});
  img.addEventListener('pointermove',e=>{if(!from||!temp)return;
    const to=pixelPoint(e),x0=Math.min(from.x,to.x),x1=Math.max(from.x,to.x),y0=Math.min(from.y,to.y),y1=Math.max(from.y,to.y);
    Object.assign(temp.style,{left:(100*x0/img.naturalWidth)+'%',top:(100*y0/img.naturalHeight)+'%',width:(100*(x1-x0)/img.naturalWidth)+'%',height:(100*(y1-y0)/img.naturalHeight)+'%'});});
  img.addEventListener('pointerup',e=>{if(!from)return;const to=pixelPoint(e);temp?.remove();temp=null;
    const x0=Math.min(from.x,to.x),x1=Math.max(from.x,to.x),y0=Math.min(from.y,to.y),y1=Math.max(from.y,to.y);from=null;
    if (x1-x0<20 || y1-y0<10){msg.textContent='Box too small. Drag across the complete handwritten answer.';return;}
    const items=getRegions();if(!items)return;if(items.length>=50){msg.textContent='Maximum 50 boxes.';return;}
    items.push({question_id:qs.value,page,x0,y0,x1,y1});setRegions(items);});
  img.addEventListener('pointercancel',()=>{from=null;temp?.remove();temp=null;});
  img.addEventListener('load',paint);
 }
 root.querySelector('#hwVisualUndo').onclick=()=>{let a=getRegions();if(a){a.pop();setRegions(a)}};
 root.querySelector('#hwVisualClear').onclick=()=>{if(confirm('Clear all selected question boxes?'))setRegions([])};
 paint();
};
