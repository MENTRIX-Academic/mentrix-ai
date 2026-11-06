"use strict";
const gradeRoot=document.querySelector('#quizForm');
const choice=document.querySelector('#gradingQuestion');
const input=document.querySelector('#gradingAnswer');
const promptBox=document.querySelector('#questionPrompt');
const feedback=document.querySelector('#results');
const gradeBtn=document.querySelector('#gradeBtn');
let questionMap=new Map(),activeAttempt=null,initialized=false;
function el(tag,klass,content){const e=document.createElement(tag);if(klass)e.className=klass;if(content!==undefined)e.textContent=String(content);return e;}
async function api(url,options){const r=await fetch(url,options);const d=await r.json().catch(()=>({}));if(!r.ok)throw Error(d.detail||('Server error '+r.status));return d;}
function renderQuestion(){const q=questionMap.get(choice.value);promptBox.replaceChildren();if(!q){promptBox.textContent='Choose a question.';gradeBtn.disabled=true;return;}
  promptBox.append(el('strong','',`${q.id} · ${q.type} · ${q.points} point(s)`),el('p','',q.prompt));
  if(q.options) for(const [k,v] of Object.entries(q.options))promptBox.append(el('div','',`${k}: ${v}`));
  gradeBtn.disabled=false;input.value='';feedback.replaceChildren(el('p','empty-small','Enter an answer and click Check answer.'));
}
async function loadQuestions(){if(initialized)return;initialized=true;
  try{const d=await api('/api/v1/grading/questions?all=true');if(!Array.isArray(d.questions)||!d.questions.length)throw Error('Question list is empty.');
    questionMap=new Map(d.questions.map(q=>[q.id,q]));choice.replaceChildren(new Option('Select a question',''));
    for(const q of d.questions)choice.append(new Option(`${q.id} · ${q.type} · ${q.prompt.slice(0,58)}`,q.id));choice.addEventListener('change',renderQuestion);
    document.querySelector('#submitStatus').textContent='Questions loaded. Choose one to begin.';
  }catch(e){initialized=false;choice.replaceChildren(new Option('Cannot load questions',''));document.querySelector('#submitStatus').textContent='Cannot load questions: '+e.message;}
}
async function renderResult(a){activeAttempt=a.attempt_id;feedback.replaceChildren();for(const r of a.results){
  const card=el('div','graded-answer-card');const reason=el('p','',r.reason||r.decision_reason||'No reason provided');
  card.append(el('h3','',`${r.question_id}: ${r.decision==='needs_review'?'Staff review needed':r.decision==='correct'?'Correct by rules':'Incorrect by rules'}`),
    el('p','',`Suggested score: ${r.proposed_score==null?'Not available':r.proposed_score} / ${r.max_score}`),reason);
  if(r.approval_status==='auto_scored')card.append(el('p','autoscored','Rule-based score saved for this local attempt. You can check or change it.'));
  if(r.approval_status==='approved'){card.append(el('p','autoscored',`Staff approved: ${r.final_score}/${r.max_score}`));feedback.append(card);continue;}
  const open=el('button','ghost',r.approval_status==='auto_scored'?'Change score (optional)':'Review and save score');open.type='button';
  const form=el('div','grade-review-form');form.hidden=true;
  const score=el('input');score.type='number';score.min='0';score.max=String(r.max_score);score.step='0.5';score.placeholder='Final score';
  const reviewer=el('input');reviewer.value='TA reviewer';reviewer.maxLength=80;reviewer.placeholder='Reviewer name';
  const save=el('button','primary','Save reviewed score');save.type='button';form.append(el('label','',`Final score (0-${r.max_score})`),score,el('label','','Reviewer'),reviewer,save);
  open.onclick=()=>{form.hidden=!form.hidden;open.textContent=form.hidden?'Review or change score':'Close review';};
  save.onclick=async()=>{if(!score.value.trim()){alert('Enter the final score.');return;}const n=Number(score.value);if(!Number.isFinite(n)||n<0||n>r.max_score){alert('Enter a valid score.');return;}if(reviewer.value.trim().length<2){alert('Enter reviewer name.');return;}
    save.disabled=true;try{await api(`/api/v1/grading/attempts/${encodeURIComponent(activeAttempt)}/items/${encodeURIComponent(r.question_id)}/approve`,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({final_score:n,reviewer:reviewer.value.trim(),comment:'Reviewed in unified local workspace'})});renderResult(await api(`/api/v1/grading/attempts/${encodeURIComponent(activeAttempt)}`));}
    catch(e){alert(e.message);save.disabled=false;}};
  card.append(open,form);feedback.append(card);
}}
gradeRoot.addEventListener('submit',async(e)=>{e.preventDefault();if(!questionMap.has(choice.value))return;gradeBtn.disabled=true;
  document.querySelector('#submitStatus').textContent='Checking answer...';
  try{const d=await api('/api/v1/grading/evaluate',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({answers:[{question_id:choice.value,answer:input.value}]})});renderResult(d);document.querySelector('#submitStatus').textContent='Answer checked. Review the result on the right.';}
  catch(err){feedback.replaceChildren(el('p','error',err.message));document.querySelector('#submitStatus').textContent='Could not check the answer.';}
  finally{gradeBtn.disabled=false;}});
document.addEventListener('mentrix:authenticated',loadQuestions);
if(window.MENTRIX_AUTHENTICATED)loadQuestions();
