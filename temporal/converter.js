'use strict';
const escapeHtml=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const style="\nbody{font:15px/1.45 \"Segoe UI\",Arial,sans-serif;color:#1e293b;background:#fff;margin:0;padding:28px;max-width:1200px;margin-inline:auto}\nh1{font-size:26px;margin:0 0 4px}p{color:#64748b;margin:0 0 24px}\nh2{font-size:18px;margin:26px 0 10px}h3{font-size:15px;margin:20px 0 8px}.scroll{overflow-x:auto}\ntable{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums;white-space:nowrap}\nth,td{padding:7px 12px;text-align:right;border-bottom:1px solid #e2e8f0}th{background:#f1f5f9;font-size:13px}\nth:first-child,td:first-child,th:nth-child(2),td:nth-child(2){text-align:left}\ntr.delta td{border-bottom:2px solid #cbd5e1;color:#64748b}\ntr.scope-end td{border-bottom:2px solid #cbd5e1}\nmark{background:#ffeb3b;color:#111827;font-weight:700;padding:3px 7px;border-radius:3px}\nmark.down{background:#fecaca}\nfooter{margin-top:22px;color:#64748b;font-size:13px}\n@media print{body{padding:0;font-size:11px}h2{margin-top:16px}th,td{padding:4px 8px}mark{print-color-adjust:exact;-webkit-print-color-adjust:exact}section{break-inside:avoid}}\n";
const clean = s => s.replace(/<[^>]*>/g,' ').replace(/\s+/g,' ').trim();
const matches = (s,r) => [...s.matchAll(r)];
const empty = () => ({A:0,U:0,E:0});
const add = (a,b) => {for(const k of ['A','U','E']) a[k]+=b[k];};
const total = m => m.A+m.U+m.E;
const pct = (n,d) => d ? (100*n/d).toFixed(2)+'%' : 'N/A';
const rate = m => total(m) ? 100*m.A/total(m) : null;
const same = (a,b) => JSON.stringify(a)===JSON.stringify(b);
const metric = s => {const t=s.trim(); if(t===''||t==='N/A') return empty(); if(!/\bA \d+ \(/.test(t)||!/\bE \d+ \(/.test(t)) throw Error('Missing classification counts: '+t); const m=empty(); for(const x of t.matchAll(/\b([AUE]) (\d+) \(/g)) m[x[1]]=Number(x[2]); return m;};
const STAGES = ['S','T','EF'];
const STAGE_NAMES = {S:'Spatial',T:'Temporal',EF:'EdgeFilter'};
const BUCKETS = {'top-left':'Corner','top-edge':'Edge','top-right':'Corner','left-edge':'Edge','center':'Center','right-edge':'Edge','bottom-left':'Corner','bottom-edge':'Edge','bottom-right':'Corner'};
const BUCKET_ORDER = ['Corner','Edge','Center'];
const SUMMARY_COLUMNS = ['Overall','Center','Edge','Corner'];
const scopeName = label => label.charAt(0).toUpperCase()+label.slice(1);
const newStage = () => ({metrics:empty(),regions:Object.fromEntries(BUCKET_ORDER.map(r=>[r,empty()]))});
// Region cells and object-type summary cells list one metric per stage, each introduced by its label span.
const stageMetrics = html => {
 const out={};
 for(const part of html.matchAll(/<span class="metric-label">(\w+)<\/span>([\s\S]*?)(?=<span class="metric-label">|$)/g)) {
  if(!STAGES.includes(part[1])) throw Error('Unknown stage label '+part[1]);
  out[part[1]]=metric(clean(part[2]));
 }
 if(!Object.keys(out).length) throw Error('No stage metrics in '+clean(html));
 return out;
};

function parseReport(source, html) {
 const chunks=html.split('<details class="file-detail">').slice(1);
 if(!chunks.length) throw Error('No recording details found in '+source);
 const scopes={}, summaries={}, identities=[], stages=new Set();
 const bucketOf=name=>{const bucket=BUCKETS[name]; if(!bucket) throw Error('Bad region '+name+' in '+source); return bucket;};
 const slot=(scope,stage)=>{
  if(!scopes[scope]) {scopes[scope]={}; summaries[scope]={};}
  if(!scopes[scope][stage]) scopes[scope][stage]=newStage();
  return scopes[scope][stage];
 };
 for(const chunk of chunks) {
  const gt=chunk.match(/Ground truth: (\w+)/)?.[1];
  if(!['finger','palm'].includes(gt)) throw Error('Unexpected ground truth '+gt+' in '+source);
  const label=chunk.match(/Source label: (\w+)/)?.[1];
  if(!label) throw Error('Missing source label in '+source);
  identities.push(clean(chunk.match(/<span class="file-summary">([\s\S]*?)<\/span>/)[1]));
  const summary=clean(chunk.slice(0,chunk.indexOf('</summary>')));
  const both=summary.match(/Spatial: (.*?) \| Temporal: (.*)/);
  if(!both) throw Error('Missing spatial/temporal summary in '+source);
  const regionTable=chunk.match(/<table class="region-grid">([\s\S]*?)<\/table>/)?.[1];
  if(!regionTable) throw Error('Missing region grid in '+source);
  const cells=matches(regionTable,/<td>([\s\S]*?)<\/td>/g);
  if(cells.length!==9) throw Error('Expected nine regions in '+source);
  const targets=['Overall',scopeName(label)];
  for(const target of targets) {
   slot(target,'S'); slot(target,'T');
   for(const [stage,raw] of [['S',both[1]],['T',both[2]]]) {
    if(!summaries[target][stage]) summaries[target][stage]=empty();
    add(summaries[target][stage],metric(raw));
   }
  }
  for(const cell of cells) {
   const name=cell[1].match(/<strong>(.*?)<\/strong>/)?.[1];
   const bucket=bucketOf(name);
   for(const [stage,value] of Object.entries(stageMetrics(cell[1]))) {
    stages.add(stage);
    for(const target of targets) {const entry=slot(target,stage); add(entry.metrics,value); add(entry.regions[bucket],value);}
   }
  }
 }
 if(!stages.has('S')||!stages.has('T')) throw Error('Report '+source+' is missing spatial or temporal region metrics');

 const labelTable=html.split('<h2>Overall and Source Label</h2>')[1]?.split('</table>')[0];
 if(!labelTable) throw Error('Missing source-label summary in '+source);
 const labels={}, settleLatency={};
 for(const row of matches(labelTable,/<tr>([\s\S]*?)<\/tr>/g)) {
  const cells=matches(row[1],/<td>([\s\S]*?)<\/td>/g).map(x=>clean(x[1]));
  if(!cells.length) continue;
  const nums=cells.slice(2,7).map(s=>{const m=s.match(/\((\d+)\/(\d+)\)/); if(!m) throw Error('Malformed summary cell in '+source+': '+s); return [+m[1],+m[2]];});
  const latency=cells[7]?.match(/^([\d.]+) ms median ([\d.]+) \/ p95 ([\d.]+) \/ max ([\d.]+) ms \(n=(\d+)\)$/);
  if(!latency) throw Error('Missing or malformed settle latency: '+source+' '+cells[0]);
  settleLatency[cells[0]]={meanMs:+latency[1],medianMs:+latency[2],p95Ms:+latency[3],maxMs:+latency[4],touches:+latency[5]};
  labels[cells[0]]={S:{A:nums[0][0],U:nums[1][0],E:nums[2][0]},T:{A:nums[3][0],U:0,E:nums[4][0]}};
 }
 if(!labels.all) throw Error('Missing the "all" source label row in '+source);
 const scopeOrder=['Overall',...Object.keys(labels).filter(x=>x!=='all').map(scopeName)];
 for(const scope of scopeOrder) {
  if(!scopes[scope]) throw Error('No recordings for '+scope+' in '+source);
  const expected=labels[scope==='Overall'?'all':scope.toLowerCase()];
  for(const stage of ['S','T']) {
   if(!same(summaries[scope][stage],expected[stage])) throw Error('Summary mismatch '+source+' '+scope+' '+stage);
   if(!same(scopes[scope][stage].metrics,expected[stage])) throw Error('Region mismatch '+source+' '+scope+' '+stage);
  }
  for(const stage of Object.keys(scopes[scope])) {
   const regionSum=empty();
   for(const region of Object.values(scopes[scope][stage].regions)) add(regionSum,region);
   if(!same(regionSum,scopes[scope][stage].metrics)) throw Error('Region total mismatch '+source+' '+scope+' '+stage);
  }
 }

 // Newer reports publish an object-type region summary; reconcile every stage, including EdgeFilter, against it.
 const summaryTable=html.split('<h3>Region summary</h3>')[1]?.split('</table>')[0];
 let reconciled=false;
 if(summaryTable) {
  for(const row of matches(summaryTable,/<tr>([\s\S]*?)<\/tr>/g)) {
   const scope=row[1].match(/^<th>(\w+)<\/th>/)?.[1];
   if(!scope||!scopes[scope]) continue;
   const cells=matches(row[1],/<td>([\s\S]*?)<\/td>/g);
   if(cells.length!==SUMMARY_COLUMNS.length) throw Error('Unexpected region summary columns in '+source);
   cells.forEach((cell,i)=>{
    for(const [stage,value] of Object.entries(stageMetrics(cell[1]))) {
     const entry=scopes[scope][stage];
     if(!entry) throw Error('Region summary reports '+stage+' but recordings do not, in '+source);
     const found=SUMMARY_COLUMNS[i]==='Overall'?entry.metrics:entry.regions[SUMMARY_COLUMNS[i]];
     if(!same(found,value)) throw Error('Region summary mismatch '+source+' '+scope+' '+SUMMARY_COLUMNS[i]+' '+stage);
     reconciled=true;
    }
   });
  }
 }

 const meta=clean(html.match(/<p class="meta">([\s\S]*?)<\/p>/)[1]);
 const processed=Number(meta.match(/Files processed: (\d+)/)[1]);
 if(chunks.length!==processed) throw Error('File count mismatch in '+source);
 return {source,meta,files:chunks.length,identities,scopes,scopeOrder,stages:STAGES.filter(s=>stages.has(s)),labelOrder:Object.keys(labels),settleLatency,reconciled};
}

const deltaCell = value => value===null?'<td>—</td>':`<td><mark${value<0?' class="down"':''}>${value>=0?'+':''}${value.toFixed(2)} pp</mark></td>`;

function convertReports(inputs, options) {
 if(!Array.isArray(inputs)||inputs.length<2) throw Error('Select at least two reports.');
 const results=inputs.map((input,i)=>({title:(input.title||'').trim()||`Configuration ${i+1}`,...parseReport(input.name,input.html)}));
 for(const result of results) {
  if(!same([...result.identities].sort(),[...results[0].identities].sort())) throw Error('Different input file sets');
  if(!same(result.scopeOrder,results[0].scopeOrder)) throw Error('Different source labels in '+result.source);
 }
 const scopeOrder=results[0].scopeOrder;
 const stages=STAGES.filter(stage=>results.some(r=>r.stages.includes(stage)));
 const reportTitle=(options&&options.title||'').trim()||'Spatial vs temporal';

 let body=`<h1>${escapeHtml(reportTitle)}</h1><p>${results.length} configurations · Parsed from the supplied reports · Accuracy differences highlighted</p>`;
 body+='<section><h2>Accuracy by configuration</h2><div class="scroll"><table><thead><tr>'+['Scope','Stage',...results.map(r=>escapeHtml(r.title))].map(x=>`<th>${x}</th>`).join('')+'</tr></thead><tbody>';
 for(const scope of scopeOrder) for(const [i,stage] of stages.entries()) {
  const cells=results.map((result,j)=>{
   const entry=result.scopes[scope]?.[stage];
   if(!entry) return '<td>—</td>';
   const value=rate(entry.metrics);
   if(value===null) return '<td>N/A</td>';
   const base=rate(results[0].scopes[scope]?.[stage]?.metrics||empty());
   const shift=j&&base!==null?` <mark${value<base?' class="down"':''}>${value>=base?'+':''}${(value-base).toFixed(2)} pp</mark>`:'';
   return `<td>${value.toFixed(2)}%${shift}</td>`;
  });
  body+=`<tr${i===stages.length-1?' class="scope-end"':''}><td>${scope}</td><td>${STAGE_NAMES[stage]}</td>${cells.join('')}</tr>`;
 }
 body+='</tbody></table></div><p>Each configuration column shows its own accuracy; the highlighted value is the difference from the first configuration, in percentage points.</p></section>';

 for(const [i,result] of results.entries()) {
  body+=`<section><h2>${i+1}. ${escapeHtml(result.title)}</h2><div class="scroll"><table><thead><tr>${['Scope','Stage','Frames','Accuracy','Error¹','Other¹',...BUCKET_ORDER].map(x=>`<th>${x}</th>`).join('')}</tr></thead><tbody>`;
  for(const scope of scopeOrder) {
   const data=result.scopes[scope];
   for(const stage of result.stages) {
    const m=data[stage].metrics,n=total(m);
    const values=[scope,STAGE_NAMES[stage],n.toLocaleString('en-US'),pct(m.A,n),pct(m.E,n),stage==='S'?pct(m.U,n):'—',...BUCKET_ORDER.map(r=>pct(data[stage].regions[r].A,total(data[stage].regions[r])))];
    body+='<tr>'+values.map(v=>`<td>${v}</td>`).join('')+'</tr>';
   }
   const steps=[['Temporal − Spatial','S','T']];
   if(result.stages.includes('EF')) steps.push(['EdgeFilter − Temporal','T','EF']);
   for(const [name,from,to] of steps) {
    const before=rate(data[from].metrics),after=rate(data[to].metrics);
    body+=`<tr class="delta"><td>${scope}</td><td>${name}</td><td>—</td>${deltaCell(before===null||after===null?null:after-before)}${'<td>—</td>'.repeat(5)}</tr>`;
   }
  }
  body+='</tbody></table></div>';
  body+='<h3>Settle latency</h3><div class="scroll"><table><thead><tr>'+['Source label','Mean (ms)','Median (ms)','P95 (ms)','Maximum (ms)','Touches'].map(x=>`<th>${x}</th>`).join('')+'</tr></thead><tbody>';
  for(const label of ['all',...result.labelOrder.filter(x=>x!=='all')]) {
   const l=result.settleLatency[label];
   if(!l) throw Error('Missing latency label '+label);
   body+='<tr>'+[label==='all'?'Overall':label,l.meanMs.toFixed(1),l.medianMs.toFixed(1),l.p95Ms.toFixed(1),l.maxMs.toFixed(1),l.touches.toLocaleString('en-US')].map(v=>`<td>${v}</td>`).join('')+'</tr>';
  }
  const parts=result.labelOrder.filter(x=>x!=='all');
  if(result.settleLatency.all.touches!==parts.reduce((n,k)=>n+result.settleLatency[k].touches,0)) throw Error('Latency touch count mismatch in '+result.source);
  body+='</tbody></table></div><p>Latency statistics are copied from the source report. Source labels stay separate here; the accuracy tables above report each label as its own scope. Counts are touches with a measured latency, not classification frames.</p></section>';
 }
 body+='<footer>¹ Spatial Error is the reported E (wrong classification); Other is U (unknown/other). Temporal and EdgeFilter Error is the report’s combined E = all non-accurate outcomes; a separate Other count is not supplied for those stages.<br>Scopes follow the report’s source labels, so finger and thumb are counted separately. Corner combines the four corners; Edge combines the four non-corner edges. All percentages are calculated from summed counts, not averaged percentages. Differences are calculated before rounding; pp = percentage points.<br>EdgeFilter counts come from reports that record the stage after EdgeFilter_process; configurations without it show —. Frame denominators differ across stages and configurations, so differences are descriptive and are not a matched-frame comparison. Each report contains '+results[0].files+' processed files with matching file names. All aggregate and region counts were reconciled against the source-label summaries'+(results.every(r=>r.reconciled)?' and the object-type region summary':'')+'.</footer><details><summary>Source reports and metadata</summary><ul>';
 for(const result of results) body+=`<li>${escapeHtml(result.title)} — ${escapeHtml(result.source)}<p>${escapeHtml(result.meta)}</p></li>`;
 body+='</ul></details>';

 return {results, html:`<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>${escapeHtml(reportTitle)}</title><style>${style}</style></head><body>${body}</body></html>`};
}
if(typeof module!=='undefined') module.exports={convertReports};
