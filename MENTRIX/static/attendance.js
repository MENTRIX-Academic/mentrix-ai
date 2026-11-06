'use strict';
const el=s=>document.querySelector(s);
async function call(path,options={}){
 const r=await fetch(path,options);const obj=await r.json().catch(()=>({}));
 if(!r.ok)throw Error(obj.detail||`Request failed ${r.status}`);return obj;
}
const json=(body)=>({method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});
function status(text,isError=false){const node=el('#attendanceStatus');node.textContent=text;node.style.color=isError?'#b33d3d':'#3a7953';}
export async function updateDashboard(){
 try{const d=await call('/api/v1/attendance/summary');
  for(const [id,key] of [['#statStudents','students'],['#statSessions','sessions'],['#statPresent','present_recorded'],['#statAbsent','absences_recorded']])el(id).textContent=String(d[key]);
 }catch(e){console.warn('Dashboard',e);}
}
export async function loadSessions(){
 try{
  const data=await call('/api/v1/attendance/sessions');const list=el('#sessionSelect');const previous=list.value;list.replaceChildren(new Option('Choose session / date',''));
  for(const row of data.sessions){const option=new Option(`${row.section_code} • ${row.session_date} ${row.topic||''}`,row.id);list.append(option);}
  if([...list.options].some(o=>o.value===previous))list.value=previous;
  if(list.value)await loadRegister();
 }catch(e){status(e.message,true);}
}
async function loadRegister(){
 const id=el('#sessionSelect').value;const host=el('#attendanceRegister');host.replaceChildren();
 if(!id){host.textContent='Choose a session from the list.';return;}
 try{
  const data=await call(`/api/v1/attendance/register/${encodeURIComponent(id)}`);
  const table=document.createElement('table');table.className='register-table';
  const thead=document.createElement('thead');thead.innerHTML='<tr><th>Student code</th><th>Name</th><th>Current status</th><th>Update</th></tr>';table.append(thead);
  const tbody=document.createElement('tbody');
  for(const student of data.register){
   const tr=document.createElement('tr');
   const c1=document.createElement('td'),c2=document.createElement('td'),c3=document.createElement('td'),c4=document.createElement('td');
   c1.textContent=student.student_code;c2.textContent=student.student_name||'—';
   const select=document.createElement('select');for(const [value,label] of [['','Not recorded'],['present','Present'],['absent','Absent'],['excused','Excused']])select.append(new Option(label,value));select.value=student.status||'';c3.append(select);
   const b=document.createElement('button');b.type='button';b.className='ghost';b.textContent='Save';b.disabled=!select.value;
   select.addEventListener('change',()=>{b.disabled=(!select.value && !student.status);b.textContent=select.value?'Save':'Clear mark';});
   b.addEventListener('click',async()=>{b.disabled=true;try{if(select.value){await call('/api/v1/attendance/mark',json({session_id:Number(id),student_code:student.student_code,status:select.value}));}else{await call(`/api/v1/attendance/mark/${encodeURIComponent(id)}/${encodeURIComponent(student.student_code)}`,{method:'DELETE'});}status(`✓ Updated attendance for ${student.student_code}`);await updateDashboard();}catch(e){status(e.message,true);}finally{b.disabled=(!select.value && !student.status);}});
   c4.append(b);tr.append(c1,c2,c3,c4);tbody.append(tr);
  }
  table.append(tbody);host.append(table);
  if(!data.register.length)host.textContent='No students in this section. Add students or import a CSV file.';
 }catch(e){status(e.message,true);}
}
function wireForm(formId,route,mapper){
 el(formId).addEventListener('submit',async(e)=>{e.preventDefault();const button=e.target.querySelector('button');button.disabled=true;
 try{await call(route,json(mapper()));status('✓ Saved on this computer.');await updateDashboard();await loadSessions();}catch(err){status(err.message,true);}finally{button.disabled=false;}});
}
wireForm('#studentForm','/api/v1/attendance/students',()=>({student_code:el('#studentCode').value,student_name:el('#studentName').value,section_code:el('#studentSection').value}));
wireForm('#sessionForm','/api/v1/attendance/sessions',()=>({section_code:el('#sessionSection').value,session_date:el('#sessionDate').value,topic:el('#sessionTopic').value}));
el('#sessionSelect').addEventListener('change',loadRegister);
el('#reloadAttendance').onclick=async()=>{await loadSessions();await updateDashboard();};
for(const [buttonId,inputId,url] of [['#importStudentsBtn','#importStudentsFile','/api/v1/attendance/import-students'],['#importAttendanceBtn','#importAttendanceFile','/api/v1/attendance/import-attendance']]){
 el(buttonId).onclick=async()=>{const file=el(inputId).files[0];if(!file){status('Choose a CSV file first.',true);return;}const btn=el(buttonId);btn.disabled=true;
 try{const form=new FormData();form.append('file',file);const d=await call(url,{method:'POST',body:form});status(`✓ Imported ${d.imported} records.`);await updateDashboard();await loadSessions();}catch(e){status(e.message,true);}finally{btn.disabled=false;}};
}
document.addEventListener('mentrix:authenticated',()=>{updateDashboard();loadSessions();});
if(window.MENTRIX_AUTHENTICATED){updateDashboard();loadSessions();}
