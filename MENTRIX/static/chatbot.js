'use strict';
const log=document.querySelector('#chat'),form=document.querySelector('#chatForm'),field=document.querySelector('#message'),send=document.querySelector('#send');
function bubble(message,role,sources=[]){
 const b=document.createElement('div');b.className='bubble '+role;
 const head=document.createElement('strong');head.textContent=role==='bot'?'MENTRIX':'You';
 const p=document.createElement('p');p.textContent=message;b.append(head,p);
 if(sources.length){const refs=document.createElement('div');refs.className='refs';for(const s of sources){const chip=document.createElement('span');chip.textContent='Source: '+s.title;refs.append(chip);}b.append(refs);}
 log.append(b);log.scrollTop=log.scrollHeight;
}
async function ask(value){const message=(value||'').trim();if(!message)return;
 bubble(message,'user');field.value='';send.disabled=true;send.textContent='Checking...';
 try{const res=await fetch('/api/v1/chatbot/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({message,section:document.querySelector('#section').value,engine:document.querySelector('#engine').value})});
  const d=await res.json();if(!res.ok)throw new Error(d.detail||'Server error');
  bubble(d.answer+(d.warning?'\n\n⚠️ '+d.warning:''),'bot',d.sources||[]);
 }catch(e){bubble('Could not answer: '+String(e.message||e),'bot');}
 finally{send.disabled=false;send.textContent='Send';field.focus();}
}
form.addEventListener('submit',e=>{e.preventDefault();ask(field.value);});
for(const b of document.querySelectorAll('[data-q]'))b.addEventListener('click',()=>ask(b.dataset.q));
field.addEventListener('keydown',e=>{if(e.key==='Enter'&&!e.shiftKey){e.preventDefault();form.requestSubmit();}});
