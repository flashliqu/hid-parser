'use strict';
const slots=[1,2,3].map(n=>({file:document.getElementById('file'+n),title:document.getElementById('title'+n)}));
const reportTitle=document.getElementById('reportTitle');
const generate=document.getElementById('generate'), download=document.getElementById('download'), status=document.getElementById('status'), preview=document.getElementById('preview');
let output=null, outputName='comparison.html';
const chosen=()=>slots.filter(slot=>slot.file.files.length===1);
const reset=()=>{output=null; download.disabled=true; preview.hidden=true; preview.removeAttribute('srcdoc');};
const refresh=()=>{
 const count=chosen().length;
 generate.disabled=count<2;
 status.textContent=count<2?`Select at least two reports (${count} selected).`:`Ready to generate from ${count} reports. Check that each report is in the right slot and named as you want it.`;
};
for(const slot of slots) {
 slot.file.addEventListener('change',()=>{reset(); refresh();});
 slot.title.addEventListener('input',reset);
}
reportTitle.addEventListener('input',reset);
const fileName=title=>(title.trim().toLowerCase().replace(/[^a-z0-9]+/g,'-').replace(/^-|-$/g,'')||'comparison')+'.html';
generate.addEventListener('click',async()=>{
 generate.disabled=true; download.disabled=true; output=null; preview.hidden=true;
 status.textContent='Reading and validating reports…';
 try{
  const selected=chosen();
  const reports=await Promise.all(selected.map(async(slot,i)=>({name:slot.file.files[0].name,title:slot.title.value.trim()||slot.title.placeholder||`Configuration ${i+1}`,html:await slot.file.files[0].text()})));
  const converted=convertReports(reports,{title:reportTitle.value});
  output=converted.html; outputName=fileName(reportTitle.value||'comparison');
  preview.srcdoc=output; preview.hidden=false; download.disabled=false;
  const stages=[...new Set(converted.results.flatMap(r=>r.stages))].length;
  status.textContent=`Comparison ready. Validated ${converted.results[0].files} matching recordings, ${stages} stages, accuracy counts, region totals, and latency touch counts across ${converted.results.length} configurations.`;
 }catch(error){status.textContent='Could not generate comparison: '+error.message;}
 finally{refresh();}
});
download.addEventListener('click',()=>{
 if(!output)return;
 const url=URL.createObjectURL(new Blob([output],{type:'text/html;charset=utf-8'}));
 const a=document.createElement('a');a.href=url;a.download=outputName;a.click();
 setTimeout(()=>URL.revokeObjectURL(url),1000);
});
refresh();
