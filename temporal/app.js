'use strict';
const inputs=['original','old','new'].map(id=>document.getElementById(id));
const generate=document.getElementById('generate'), download=document.getElementById('download'), status=document.getElementById('status'), preview=document.getElementById('preview');
let output=null;
for(const input of inputs) input.addEventListener('change',()=>{
 output=null; download.disabled=true; preview.hidden=true; preview.removeAttribute('srcdoc');
 generate.disabled=!inputs.every(x=>x.files.length===1);
 status.textContent=generate.disabled?'Select one report for each configuration.':'Ready to generate. Check that each file is assigned to the correct configuration.';
});
generate.addEventListener('click',async()=>{
 generate.disabled=true; download.disabled=true; output=null; preview.hidden=true;
 status.textContent='Reading and validating reports…';
 try{
  const files=inputs.map(x=>x.files[0]);
  const reports=await Promise.all(files.map(async f=>({name:f.name,html:await f.text()})));
  const converted=convertReports(reports);
  output=converted.html; preview.srcdoc=output; preview.hidden=false; download.disabled=false;
  status.textContent=`Comparison ready. Validated ${converted.results[0].files} matching recordings, accuracy counts, region totals, and latency touch counts.`;
 }catch(error){status.textContent='Could not generate comparison: '+error.message;}
 finally{generate.disabled=!inputs.every(x=>x.files.length===1);}
});
download.addEventListener('click',()=>{
 if(!output)return;
 const url=URL.createObjectURL(new Blob([output],{type:'text/html;charset=utf-8'}));
 const a=document.createElement('a');a.href=url;a.download='temporal-filter-tables-updated.html';a.click();
 setTimeout(()=>URL.revokeObjectURL(url),1000);
});
