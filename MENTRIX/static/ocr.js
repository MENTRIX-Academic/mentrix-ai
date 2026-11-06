'use strict';
const $ = s => document.querySelector(s);
let qbank = [], activeId = null, activeCandidates=[], file=null, img=null, boundaries=[], canvas=$('#cropCanvas'),ctx=canvas.getContext('2d');
function text(el, value){$(el).textContent=String(value ?? '');}
function setStatus(selector,msg,error=false){const el=$(selector);el.textContent=msg;el.className='micro '+(error?'error-msg':'');}
async function request(path,options={}){
  const response=await fetch(path,options);let data;
  try {data=await response.json();}catch {throw new Error('Non-JSON server response');}
  if(!response.ok) throw new Error(typeof data.detail==='string'?data.detail:JSON.stringify(data.detail || data));
  return data;
}
function draw(){
  if(!img) return;
  canvas.width=img.naturalWidth;canvas.height=img.naturalHeight; canvas.style.display='block';
  ctx.drawImage(img,0,0,canvas.width,canvas.height);
  ctx.lineWidth=Math.max(3,canvas.width/370);ctx.strokeStyle='#f05d74';
  for(let i=1;i<boundaries.length-1;i++){
    const y=boundaries[i];ctx.beginPath();ctx.moveTo(0,y);ctx.lineTo(canvas.width,y);ctx.stroke();
    ctx.fillStyle='#e3e6ee';ctx.fillRect(3,y-9,52,18);ctx.fillStyle='#91243b';
    ctx.font='bold 13px sans-serif';ctx.fillText('L'+(i+1),6,y+5);
  }
  text('#lineCount',`Line crops: ${boundaries.length-1}. Click between handwritten lines to add dividers. Click near an existing divider to remove it.`);
  $('#runOcr').disabled=!file || !$('#confirmLines').checked;
}
$('#imageFile').addEventListener('change',e=>{
  file=e.target.files[0]||null;$('#confirmLines').checked=false;$('#runOcr').disabled=true;
  if(!file){img=null;canvas.style.display='none';return;}
  if(file.size>12*1024*1024){setStatus('#ocrStatus','File exceeds 12 MB',true);return;}
  const url=URL.createObjectURL(file);const picture=new Image();
  picture.onload=()=>{img=picture;boundaries=[0,img.naturalHeight];$('#noImage').style.display='none';
    text('#imageInfo',`${file.name} · ${img.naturalWidth} × ${img.naturalHeight} · ${(file.size/1024/1024).toFixed(1)} MB`);
    draw();URL.revokeObjectURL(url);};
  picture.onerror=()=>{setStatus('#ocrStatus','Cannot read image',true);URL.revokeObjectURL(url);};
  picture.src=url;
});
canvas.addEventListener('click',e=>{
  if(!img)return;
  const r=canvas.getBoundingClientRect();const y=Math.round((e.clientY-r.top)*canvas.height/r.height);
  const threshold=Math.max(8,12*canvas.height/r.height);
  const index=boundaries.findIndex((v,i)=>i>0&&i<boundaries.length-1&&Math.abs(v-y)<threshold);
  if(index>0)boundaries.splice(index,1);
  else if(y>12&&y<canvas.height-12){boundaries.push(y);boundaries.sort((a,b)=>a-b);}
  $('#confirmLines').checked=false;draw();
});
$('#undo').onclick=()=>{if(boundaries.length>2)boundaries.splice(boundaries.length-2,1);$('#confirmLines').checked=false;draw();};
$('#clear').onclick=()=>{if(img){boundaries=[0,img.naturalHeight];$('#confirmLines').checked=false;draw();}};
$('#confirmLines').addEventListener('change',draw);
$('#suggest').addEventListener('click',async()=>{
 if(!file||!img){setStatus('#suggestStatus','Choose an image first.',true);return;}
 const b=$('#suggest');b.disabled=true;setStatus('#suggestStatus','Checking ink rows locally...');
 try{const body=new FormData();body.append('image',file);
 const d=await request('/api/v1/ocr/suggest-lines',{method:'POST',body});
 if(d.height!==img.naturalHeight){setStatus('#suggestStatus','EXIF image rotation mismatch. Mark boundaries manually.',true);return;}
 boundaries=d.boundaries;$('#confirmLines').checked=false;draw();setStatus('#suggestStatus',d.message+' Verify every red line manually.');
 }catch(e){setStatus('#suggestStatus',e.message,true);}finally{b.disabled=false;}
});
function showCandidates(d){
 const rows=$('#candidateRows');rows.replaceChildren();activeCandidates=d.candidates||[];
 $('#candidateSection').hidden=!activeCandidates.length;
 const allFlags=[];
 (d.quality||[]).forEach(q=>{(q.flags||[]).forEach(flag=>allFlags.push(`Line ${q.line}: ${flag}`));});
 $('#qualityFlags').hidden=!allFlags.length;
 text('#qualityFlags',allFlags.length?'⚠ OCR QA flags (not error probabilities):\n'+allFlags.join('\n'):'');
 activeCandidates.forEach((c,i)=>{
 const row=document.createElement('div');row.className='candidate-line';
 const title=document.createElement('b');title.textContent=`Line ${i+1}`;
 const a=document.createElement('label');const ar=document.createElement('input');ar.type='radio';ar.name='cand_'+i;ar.value='original';ar.checked=true;
 a.append(ar,document.createTextNode(' Original: '+c.original));
 row.append(title,a);
 if(c.padded!==null&&c.padded!==undefined){const b=document.createElement('label'),br=document.createElement('input');br.type='radio';br.name='cand_'+i;br.value='padded';b.append(br,document.createTextNode(' Padded/upscaled: '+c.padded));row.append(b);}
 if(c.autocontrast!==null&&c.autocontrast!==undefined){const b=document.createElement('label'),br=document.createElement('input');br.type='radio';br.name='cand_'+i;br.value='autocontrast';b.append(br,document.createTextNode(' Autocontrast: '+c.autocontrast));row.append(b);}
 rows.append(row);
 });
}
$('#applyCandidate').addEventListener('click',()=>{
 const combined=activeCandidates.map((c,i)=>{
 const chosen=document.querySelector('input[name="cand_'+i+'"]:checked');
 return chosen?.value==='autocontrast'?c.autocontrast:chosen?.value==='padded'?c.padded:c.original;
 }).join('\n');
 $('#corrected').value=combined;$('#confirmText').checked=false;
 setStatus('#verifyStatus','Draft replaced by selected candidates. Now verify every word with the original image.');
});
async function showRecord(d){
  activeId=d.id;showCandidates(d);$('#ocrEmpty').hidden=true;$('#ocrResult').hidden=false;$('#savedImagePreview').src=d.image_url;
  text('#resultQuestion',`${d.question_id} · ${d.writer_code} · ${d.image_filename}`);
  text('#rawOcr',d.ocr_prediction);$('#corrected').value=d.verified_text || d.ocr_prediction;
  $('#confirmText').checked=!!d.transcription_verified;$('#verifyBtn').disabled=d.status==='approved';
  $('#corrected').readOnly=d.status==='approved';
  $('#approvalBox').hidden=!d.transcription_verified || d.status==='auto_scored';
  $('#overrideAuto').hidden=d.status!=='auto_scored';
  text('#statePill',d.status==='approved'?'TA approved':d.status==='auto_scored'?'Auto-scored · optional audit':d.transcription_verified?'Needs TA review':'Awaiting transcription');
  text('#maxScore',`(0 to ${d.max_score})`);$('#score').max=d.max_score;
  $('#score').value=d.final_score===null||d.final_score===undefined?(d.proposed_score===null||d.proposed_score===undefined?'':d.proposed_score):d.final_score;
  $('#reviewer').value=d.reviewer||'Demo TA';$('#comment').value=d.review_comment||'';
  $('#approveBtn').disabled=d.status==='approved';
  setStatus('#verifyStatus',d.transcription_verified?'Human transcription marked verified.':'Raw OCR must be checked before grading.');
  if(d.transcription_verified){$('#gradeAdvice').hidden=false;const label=d.decision==='needs_review'?'Needs TA review':d.decision;
     text('#gradeAdvice',`Decision: ${label}\nV2 proposed: ${d.proposed_score===null||d.proposed_score===undefined?'No automated score':d.proposed_score+'/'+d.max_score}\nReason: ${d.decision_reason}\nFinal TA score: ${d.final_score===null||d.final_score===undefined?'Not assigned':d.final_score}`);
  }else $('#gradeAdvice').hidden=true;
  if(d.status==='auto_scored') setStatus('#approveStatus',`✓ ${d.final_score}/${d.max_score} scored using V2 rules. Manual review is optional.`);
  if(d.status==='approved') setStatus('#approveStatus',`✓ Approved: ${d.final_score}/${d.max_score} by ${d.reviewer}`);
  else setStatus('#approveStatus','');
}
$('#runOcr').addEventListener('click',async()=>{
 if(!img||!file||!$('#confirmLines').checked){setStatus('#ocrStatus','Mark line boundaries and confirm before running.',true);return;}
 const button=$('#runOcr');button.disabled=true;
 setStatus('#ocrStatus',`Transcribing ${boundaries.length-1} line(s) on CPU. Keep this tab open…`);
 const data=new FormData();data.append('image',file);data.append('question_id',$('#question').value);
 data.append('writer_code',$('#writer').value.trim()||'ANON');data.append('boundaries',JSON.stringify(boundaries));data.append('comparison_mode',$('#comparisonMode').value);
 try {const response=await request('/api/v1/ocr/transcribe',{method:'POST',body:data});
   await showRecord(response);setStatus('#ocrStatus',`✓ ${response.line_count} lines completed. Now check every word of the transcription.`);await refresh();
 }catch(e){setStatus('#ocrStatus',String(e.message||e),true);}
 finally{button.disabled=!$('#confirmLines').checked;}
});
$('#verifyBtn').addEventListener('click',async()=>{
  if(!activeId)return;
  if(!$('#confirmText').checked){setStatus('#verifyStatus','Please check the verification box after comparing the handwriting.',true);return;}
  const body={corrected_text:$('#corrected').value,verified:true};
  $('#verifyBtn').disabled=true;
  try{const d=await request(`/api/v1/ocr/reviews/${encodeURIComponent(activeId)}/verify`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});await showRecord(d);await refresh();}
  catch(e){setStatus('#verifyStatus',String(e.message||e),true);}finally{$('#verifyBtn').disabled=false;}
});
$('#approveBtn').addEventListener('click',async()=>{
  if(!activeId)return;
  const val=$('#score').value.trim();const number=Number(val);
  if(!val||!Number.isFinite(number)){setStatus('#approveStatus','Enter a final score.',true);return;}
  const payload={reviewer:$('#reviewer').value.trim(),final_score:number,comment:$('#comment').value};
  if(payload.reviewer.length<2){setStatus('#approveStatus','Enter a reviewer alias.',true);return;}
  $('#approveBtn').disabled=true;
  try{const d=await request(`/api/v1/ocr/reviews/${encodeURIComponent(activeId)}/approve`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});await showRecord(d);await refresh();}
  catch(e){setStatus('#approveStatus',String(e.message||e),true);$('#approveBtn').disabled=false;}
});
async function refresh(){
  const host=$('#historyRows');host.replaceChildren();
  try{const d=await request('/api/v1/ocr/reviews');
    if(!d.reviews.length){host.textContent='No OCR reviews yet on this computer.';return;}
    for(const r of d.reviews){const row=document.createElement('div');row.className='review-row';
      const info=document.createElement('span');info.textContent=`${r.question_id} · ${r.writer_code} · ${r.status} · ${r.final_score===null?'not graded':'score '+r.final_score}`;
      const btn=document.createElement('button');btn.type='button';btn.className='ghost';btn.textContent='Open review';btn.onclick=async()=>{const full=await request(`/api/v1/ocr/reviews/${encodeURIComponent(r.id)}`);await showRecord(full);$('#ocrResult').scrollIntoView({behavior:'smooth',block:'start'});};
      row.append(info,btn);host.append(row);
    }
  }catch(e){host.textContent='Unable to read local queue: '+e.message;}
}
$('#refreshHistory').onclick=refresh;
let ocrInitialized=false;
async function loadOcrConfig(){if(ocrInitialized)return;ocrInitialized=true;
  try{const cfg=await request('/api/v1/ocr/config');qbank=cfg.question_ids;const select=$('#question');
    for(const q of qbank){const op=document.createElement('option');op.value=q.id;op.textContent=`${q.id} · ${q.type} · ${q.prompt}`;select.append(op);}
    select.value='E01';await refresh();
  }catch(e){ocrInitialized=false;setStatus('#ocrStatus','Could not load questions: '+e.message,true);}}
document.addEventListener('mentrix:authenticated',loadOcrConfig);
if(window.MENTRIX_AUTHENTICATED)loadOcrConfig();

$('#overrideAuto').onclick=()=>{$('#approvalBox').hidden=false;$('#overrideAuto').hidden=true;};
