'use strict';
const escapeHtml=s=>String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const style="\nbody{font:15px/1.45 \"Segoe UI\",Arial,sans-serif;color:#1e293b;background:#fff;margin:0;padding:28px;max-width:1200px;margin-inline:auto}\nh1{font-size:26px;margin:0 0 4px}p{color:#64748b;margin:0 0 24px}\nh2{font-size:18px;margin:26px 0 10px}.scroll{overflow-x:auto}\ntable{border-collapse:collapse;width:100%;font-variant-numeric:tabular-nums;white-space:nowrap}\nth,td{padding:7px 12px;text-align:right;border-bottom:1px solid #e2e8f0}th{background:#f1f5f9;font-size:13px}\nth:first-child,td:first-child,th:nth-child(2),td:nth-child(2){text-align:left}\ntr.delta td{border-bottom:2px solid #cbd5e1;color:#64748b}\nmark{background:#ffeb3b;color:#111827;font-weight:700;padding:3px 7px;border-radius:3px}\nfooter{margin-top:22px;color:#64748b;font-size:13px}\n@media print{body{padding:0;font-size:11px}h2{margin-top:16px}th,td{padding:4px 8px}mark{print-color-adjust:exact;-webkit-print-color-adjust:exact}section{break-inside:avoid}}\n";
const clean = s => s.replace(/<[^>]*>/g,' ').replace(/\s+/g,' ').trim();
const matches = (s,r) => [...s.matchAll(r)];
const empty = () => ({A:0,U:0,E:0});
const add = (a,b) => {for(const k of ['A','U','E']) a[k]+=b[k];};
const total = m => m.A+m.U+m.E;
const pct = (n,d) => d ? (100*n/d).toFixed(2)+'%' : 'N/A';
const metric = s => {if(s.trim()==='N/A') return empty(); if(!/\bA \d+ \(/.test(s)||!/\bE \d+ \(/.test(s)) throw Error('Missing classification counts: '+s); const m=empty(); for(const x of s.matchAll(/\b([AUE]) (\d+) \(/g)) m[x[1]]=Number(x[2]); return m;};
const regionNames = ['top-left','top-edge','top-right','left-edge','center','right-edge','bottom-left','bottom-edge','bottom-right'];
function convertReports(inputs) {
if(inputs.length!==3) throw Error('Select all three reports.');
const files=inputs.map(x=>x.name), titles=['Original spatial + original temporal','New spatial + original temporal','New spatial + new temporal'];
const results=[];
for(let i=0;i<files.length;i++) {
 const source=files[i];
 const html=inputs[i].html;
 const scopes=Object.fromEntries(['Overall','Finger','Palm'].map(s=>[s,Object.fromEntries(['S','T'].map(t=>[t,{metrics:empty(),regions:Object.fromEntries(['Corner','Edge','Center'].map(r=>[r,empty()]))}]))]));
 const chunks=html.split('<details class="file-detail">').slice(1);
 if (!chunks.length) throw Error('No recording details found in '+source);
 const identities=[];
 for(const chunk of chunks) {
  const gt=chunk.match(/Ground truth: (\w+)/)?.[1];
  if(!['finger','palm'].includes(gt)) throw Error('Unexpected ground truth '+gt);
  identities.push(clean(chunk.match(/<span class="file-summary">([\s\S]*?)<\/span>/)[1]));
  const summary=clean(chunk.slice(0,chunk.indexOf('</summary>')));
  const both=summary.match(/Spatial: (.*?) \| Temporal: (.*)/);
  const regionTable=chunk.match(/<table class="region-grid">([\s\S]*?)<\/table>/)[1];
  const cells=matches(regionTable,/<td>([\s\S]*?)<\/td>/g);
  if(cells.length!==9) throw Error('Expected nine regions');
  for(const scope of ['Overall',gt==='finger'?'Finger':'Palm']) {
   for(const [stage,raw] of [['S',both[1]],['T',both[2]]]) add(scopes[scope][stage].metrics,metric(raw));
   for(const cell of cells) {
    const txt=clean(cell[1]);
    const parts=txt.match(/^(\S+) S (.*?) T (.*)$/);
    if(!parts || !regionNames.includes(parts[1])) throw Error('Bad region '+txt);
    const bucket=parts[1]==='center'?'Center':parts[1].endsWith('-edge')?'Edge':'Corner';
    add(scopes[scope].S.regions[bucket],metric(parts[2]));
    add(scopes[scope].T.regions[bucket],metric(parts[3]));
   }
  }
 }
 const labelTable=html.split('<h2>Overall and Source Label</h2>')[1].split('</table>')[0];
 const labels={}; const settleLatency={};
 for(const row of matches(labelTable,/<tr>([\s\S]*?)<\/tr>/g)) {
  const cells=matches(row[1],/<td>([\s\S]*?)<\/td>/g).map(x=>clean(x[1]));
  if(!cells.length) continue;
  const nums=cells.slice(2,7).map(s=>{const m=s.match(/\((\d+)\/(\d+)\)/);return [+m[1],+m[2]];});
  const latency = cells[7]?.match(/^([\d.]+) ms median ([\d.]+) \/ p95 ([\d.]+) \/ max ([\d.]+) ms \(n=(\d+)\)$/);
  if (!latency) throw Error('Missing or malformed settle latency: '+files[i]+' '+cells[0]);
  settleLatency[cells[0]]={meanMs:+latency[1],medianMs:+latency[2],p95Ms:+latency[3],maxMs:+latency[4],touches:+latency[5]};
  labels[cells[0]]={S:{A:nums[0][0],U:nums[1][0],E:nums[2][0]},T:{A:nums[3][0],U:0,E:nums[4][0]}};
 }
 for(const scope of Object.keys(scopes)) for(const stage of ['S','T']) {
  const expected=empty();
  for(const label of scope==='Overall'?['all']:scope==='Finger'?['finger','thumb']:['palm']) add(expected,labels[label][stage]);
  if(JSON.stringify(expected)!==JSON.stringify(scopes[scope][stage].metrics)) throw Error('Summary mismatch '+files[i]+scope+stage);
  const regionSum=empty(); for(const r of Object.values(scopes[scope][stage].regions)) add(regionSum,r);
  if(JSON.stringify(regionSum)!==JSON.stringify(expected)) throw Error('Region mismatch '+files[i]+scope+stage);
 }
 const meta=clean(html.match(/<p class="meta">([\s\S]*?)<\/p>/)[1]);
 if(chunks.length!==Number(meta.match(/Files processed: (\d+)/)[1])) throw Error('File count mismatch');
 results.push({title:titles[i],source,meta,files:chunks.length,identities,scopes,settleLatency});
}
for(const result of results) if(JSON.stringify([...result.identities].sort())!==JSON.stringify([...results[0].identities].sort())) throw Error('Different input file sets');

let body='<h1>Spatial vs temporal</h1><p>Three configurations · Parsed from the supplied reports · Accuracy deltas highlighted in yellow</p>';
for(const [i,result] of results.entries()) {
 body+=`<section><h2>${i+1}. ${result.title}</h2><div class="scroll"><table><thead><tr>${['Scope','Stage','Frames','Accuracy','Error¹','Other¹','Corner','Edge','Center'].map(x=>`<th>${x}</th>`).join('')}</tr></thead><tbody>`;
 for(const [scope,data] of Object.entries(result.scopes)) {
  for(const stage of ['S','T']) {
   const m=data[stage].metrics,n=total(m);
   const values=[scope,stage==='S'?'Spatial':'Temporal',n.toLocaleString('en-US'),pct(m.A,n),pct(m.E,n),stage==='S'?pct(m.U,n):'—',...['Corner','Edge','Center'].map(r=>pct(data[stage].regions[r].A,total(data[stage].regions[r])))];
   body+='<tr>'+values.map(v=>`<td>${v}</td>`).join('')+'</tr>';
  }
  const delta=100*data.T.metrics.A/total(data.T.metrics)-100*data.S.metrics.A/total(data.S.metrics);
  body+=`<tr class="delta"><td>${scope}</td><td>Delta</td><td>—</td><td><mark>${delta>=0?'+':''}${delta.toFixed(2)} pp</mark></td>${'<td>—</td>'.repeat(5)}</tr>`;
 }
 body+='</tbody></table></div>';
 body+='<h3>Settle latency</h3><div class="scroll"><table><thead><tr>'+['Source label','Mean (ms)','Median (ms)','P95 (ms)','Maximum (ms)','Touches'].map(x=>`<th>${x}</th>`).join('')+'</tr></thead><tbody>';
 for (const label of ['all','finger','thumb','palm']) {
  const l=result.settleLatency[label];
  if (!l) throw Error('Missing latency label '+label);
  body+='<tr>'+[label==='all'?'Overall':label,l.meanMs.toFixed(1),l.medianMs.toFixed(1),l.p95Ms.toFixed(1),l.maxMs.toFixed(1),l.touches.toLocaleString('en-US')].map(v=>`<td>${v}</td>`).join('')+'</tr>';
 }
 if (result.settleLatency.all.touches !== ['finger','thumb','palm'].reduce((n,k)=>n+result.settleLatency[k].touches,0)) throw Error('Latency touch count mismatch');
 body+='</tbody></table></div><p class="latency-note">Latency statistics are copied from the source report. Finger and thumb are separate source labels here; the accuracy table above combines them. Counts are touches with a measured latency, not classification frames.</p></section>';
}
body+='<footer>¹ Spatial Error is the reported E (wrong classification); Other is U (unknown/other). Temporal Error is the report’s combined E = all non-accurate outcomes; a separate temporal Other count is not supplied.<br>Finger combines source labels finger and thumb (ground truth: finger). Corner combines the four corners; Edge combines the four non-corner edges. All percentages are calculated from summed counts, not averaged percentages. Delta = temporal accuracy − spatial accuracy, calculated before rounding; pp = percentage points.<br>Frame denominators differ across stages and configurations, so deltas are descriptive and are not a matched-frame comparison. Each report contains '+results[0].files+' processed files with matching file names. All aggregate and region counts were reconciled against the source-label summaries.</footer><details><summary>Source reports and metadata</summary><ul>';
for(const result of results) body+=`<li>${escapeHtml(result.source)}<p>${escapeHtml(result.meta)}</p></li>`;
body+='</ul></details>';

return {results, html:`<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><title>Spatial vs temporal comparison</title><style>${style}</style></head><body>${body}</body></html>`};
}
if(typeof module!=='undefined') module.exports={convertReports};
