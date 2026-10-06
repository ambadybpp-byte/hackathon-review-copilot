const state={items:[],queue:[],shortlist:null};
const $=id=>document.getElementById(id);
const api=async(url,opts={})=>{const r=await fetch(url,opts);if(!r.ok)throw new Error(await r.text());return r.json()};
function setStatus(t){$("statusText").textContent=t}
function renderQueue(){ $("queue").innerHTML=state.queue.map(f=>'<span class="chip">'+esc(f.name)+'</span>').join('') }
function esc(s){return String(s??'').replace(/[&<>"]/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;'}[c]))}
function renderFilters(){const vals=[...new Set(state.items.map(x=>x.classification?.primary).filter(Boolean))];$("problem").innerHTML='<option value="ALL">All problem statements</option>'+vals.map(v=>'<option>'+esc(v)+'</option>').join('')}
function render(){const q=$("search").value.toLowerCase(),p=$("problem").value,d=$("decision").value,s=$("sort").value;
let a=state.items.filter(x=>(!q||x.filename.toLowerCase().includes(q))&&(!p||p==="ALL"||x.classification?.primary===p)&&(!d||d==="ALL"||x.evaluation?.decision===d));
a.sort((x,y)=>s==="name"?x.filename.localeCompare(y.filename):s==="scoreAsc"?(x.evaluation.final_score-y.evaluation.final_score):(y.evaluation.final_score-x.evaluation.final_score));
$("count").textContent=state.items.length;$("strong").textContent=state.items.filter(x=>x.evaluation.final_score>=80).length;$("review").textContent=state.items.filter(x=>x.evaluation.decision==="REVIEW").length;
$("avg").textContent=state.items.length?(state.items.reduce((n,x)=>n+x.evaluation.final_score,0)/state.items.length).toFixed(1):"—";
$("finalists").textContent=(state.shortlist?.selected?.length||0)+" / 30";
if(!a.length){$("results").innerHTML='<div class="empty"><div class="empty-mark">◎</div><h3>No matching submissions</h3><p>Adjust the filters or analyze more submissions.</p></div>';return}
$("results").innerHTML=a.map((x,i)=>card(x,i)).join('')}
function card(x,i){const e=x.evaluation,c=x.classification,flags=e.flags||[];return '<article class="card" id="c'+i+'"><div class="card-main"><div><div class="name">'+esc(x.filename)+'</div><div class="sub">'+esc(c.primary_source||'classification')+' • confidence '+Math.round((c.primary_confidence||0)*100)+'%</div><button class="tag tag-button" onclick="toggleCard('c'+i,this)">'+esc(c.primary)+'</button></div><div><div class="score">'+e.final_score+'</div><div class="muted">/ 100</div></div><div><div class="band '+e.band.toLowerCase()+'">'+e.band+'</div><div class="muted">'+e.decision+'</div></div><div class="flags">'+(flags.length?flags.length+' flag'+(flags.length>1?'s':''):'No flags')+'</div><button class="expand" onclick="toggleCard(\'c'+i+'\',this)">⌄ View evidence</button></div><div class="detail">'+rubric(e.rubric)+evidence(e)+ '</div></article>'}
function toggleCard(id,btn){const card=document.getElementById(id);const open=card.classList.toggle('open');const buttons=card.querySelectorAll('.expand,.tag-button');buttons.forEach(b=>{if(b.classList.contains('tag-button'))b.textContent=open?'OPEN · evidence':'OPEN';else b.textContent=open?'⌃ Hide evidence':'⌄ View evidence'})}
function rubric(rs){return '<div class="rubric">'+rs.map(r=>{const points=(r.score*r.weight/100);return '<div class="criterion"><div class="n">'+esc(r.name)+' • '+r.weight+' points</div><strong>'+points.toFixed(1)+' / '+r.weight+'</strong><span class="muted"> ('+r.score+'%)</span><div class="bar"><i style="width:'+r.score+'%"></i></div></div>'}).join('')+'</div>'}
function evidence(e){let h='<div class="evidence"><h4>Judge evidence</h4>';for(const r of e.rubric){for(const ev of (r.evidence||[]).slice(0,1))h+='<div class="evidence-item"><b>'+esc(r.name)+' '+esc(ev.location)+'</b> · '+esc(ev.snippet)+'</div>'}for(const f of (e.flags||[]))h+='<div class="flag"><b>'+esc(f.type)+'</b> · '+esc(f.location)+' · '+esc(f.reason)+'</div>';return h+'</div>'}
async function analyze(){if(!state.queue.length){setStatus("Choose at least one submission first");return}await uploadAndAnalyze([...state.queue])}
async function uploadAndAnalyze(batch){
  setStatus("Uploading and analyzing "+batch.length+" submission"+(batch.length===1?"":"s")+"…");
  $("analyzeBtn").disabled=true;$("analyzeBtn").textContent="Uploading…";
  try{
    const fd=new FormData();batch.forEach(f=>fd.append("files",f,f.name));
    const r=await api("/api/analyze-batch",{method:"POST",body:fd});
    if(!r.success)throw new Error("Server did not accept the batch");
    state.items=r.ranked||[];state.shortlist=null;renderFilters();render();
    state.queue=[];renderQueue();$("analyzeBtn").disabled=true;$("analyzeBtn").textContent="Analyze submissions";
    setStatus((r.successful||0)+" submissions analyzed successfully");
  }catch(e){
    console.error(e);setStatus("Upload failed: "+(e.message||"server error"));
    $("analyzeBtn").disabled=false;$("analyzeBtn").textContent="Retry upload & analyze";
  }
}
async function buildShortlist(){if(!state.items.length){setStatus('Analyze submissions first');return}setStatus('Building evidence-weighted Top 30…');try{state.shortlist=await api('/api/shortlist',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({items:state.items,limit:30})});$("shortlistPanel").classList.remove('hidden');$("results").classList.add('hidden');renderShortlist();render()}catch(e){setStatus('Shortlist failed')}}
function renderShortlist(){const a=state.shortlist.allocation||{};$("allocation").innerHTML='<div class="allocation-grid">'+Object.entries(a).map(([k,v])=>'<div class="alloc"><span>'+esc(k)+'</span><strong>'+v+'</strong></div>').join('')+'</div><div class="final-table"><div class="final-row head"><div>#</div><div>Submission</div><div>Score</div><div>Problem</div><div>Status</div></div>'+state.shortlist.selected.map((x,i)=>'<div class="final-row"><div>'+(i+1)+'</div><div><b>'+esc(x.filename)+'</b></div><div>'+x.score+'</div><div>'+esc(x.problem)+'</div><div>'+esc(x.reason)+'</div></div>').join('')+'</div><p class="muted" style="margin-top:12px">'+esc(state.shortlist.rationale)+'</p>'}
async function addFiles(fileList){
  const incoming=Array.from(fileList||[]).filter(f=>/\.(pptx|pdf|zip)$/i.test(f.name));
  if(!incoming.length){setStatus("No PPTX, PDF or ZIP files selected");return}
  const existing=new Set(state.queue.map(f=>f.name+"|"+f.size));
  state.queue=[...state.queue,...incoming.filter(f=>!existing.has(f.name+"|"+f.size))];
  renderQueue();
  setStatus(state.queue.length+" file"+(state.queue.length===1?"":"s")+" selected. Starting upload…");
  await uploadAndAnalyze([...state.queue]);
}
$("fileInput").addEventListener("change",e=>{addFiles(e.target.files);e.target.value=""});
$("dropzone").addEventListener("click",e=>{
  if(e.target.closest("button,.file-picker")) return;
  $("fileInput").click();
});
$("analyzeBtn").onclick=analyze;$("shortlistBtn").onclick=buildShortlist;$("closeShortlist").onclick=()=>{$("shortlistPanel").classList.add('hidden');$("results").classList.remove('hidden')};["search","problem","decision","sort"].forEach(id=>$(id).oninput=render);
(async()=>{try{const r=await api('/api/results');if(r.items?.length){state.items=r.items;state.shortlist=r.shortlist;renderFilters();render()}}catch{} })();