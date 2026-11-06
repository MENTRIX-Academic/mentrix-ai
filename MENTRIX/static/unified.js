'use strict';
function goto(page){
 for(const view of document.querySelectorAll('[data-page]'))view.hidden=view.dataset.page!==page;
 for(const link of document.querySelectorAll('[data-view]')){link.classList.toggle('active',link.dataset.view===page);link.setAttribute('aria-current',link.dataset.view===page?'page':'false');}
 history.replaceState(null,'','#'+page);
 window.scrollTo({top:0,behavior:'instant'});
}
for(const btn of document.querySelectorAll('[data-view],[data-goto]')){
 btn.onclick=()=>goto(btn.dataset.view||btn.dataset.goto);
}
let initPage=location.hash.slice(1);if(!['overview','attendance','grading','assistant'].includes(initPage))initPage='overview';goto(initPage);
const gate=document.querySelector('#authGate'),login=document.querySelector('#loginForm');
async function check(){
 try{const response=await fetch('/api/auth/session');const data=await response.json();
  gate.hidden=!!data.authenticated;
  window.MENTRIX_AUTHENTICATED=!!data.authenticated;
  if(data.authenticated)document.dispatchEvent(new Event('mentrix:authenticated'));
  if(!data.configured)document.querySelector('#loginStatus').textContent='Start MENTRIX with START_MENTRIX_UNIFIED.bat and set a PIN of at least 6 characters.';
 }catch{gate.hidden=false;document.querySelector('#loginStatus').textContent='Cannot reach the server. Run START_MENTRIX_UNIFIED.bat first.';}
}
login.addEventListener('submit',async(e)=>{
 e.preventDefault();const submit=login.querySelector('button');submit.disabled=true;
 try{const res=await fetch('/api/auth/login',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({pin:document.querySelector('#staffPin').value})});const data=await res.json();if(!res.ok)throw Error(data.detail||'Login failed');
  location.reload();
 }catch(err){document.querySelector('#loginStatus').textContent=err.message;submit.disabled=false;}
});
document.querySelector('#logoutBtn').onclick=async()=>{await fetch('/api/auth/logout',{method:'POST'});location.reload();};
check();
