const $=id=>document.getElementById(id);
document.querySelectorAll('[data-query]').forEach(button=>button.addEventListener('click',()=>{
  $('question').value=button.dataset.query;
  document.querySelectorAll('[data-query]').forEach(b=>b.classList.toggle('selected',b===button));
}));
$('ask').addEventListener('click',async()=>{
  $('ask').disabled=true; $('ask').textContent='Retrieving…'; $('error').classList.add('hidden');
  try {
    const response=await fetch('/api/ask',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify({query:$('question').value,tenant:$('tenant').value,strategy:$('strategy').value})});
    const result=await response.json();
    if(!response.ok) throw new Error('Please check the question and collection.');
    $('empty').classList.add('hidden'); $('result').classList.remove('hidden');
    $('status').textContent=result.status; $('status').className='badge '+(result.status==='answered'?'':'warning');
    $('answer').textContent=result.answer; $('latency').textContent=result.elapsed_ms+' ms';
    $('sources').replaceChildren();
    result.retrieved.map(hit=>result.citations.find(c=>c.document_id===hit.document_id)||hit).forEach((hit,i)=>{
      const card=document.createElement('article');card.className='source-card';
      const title=document.createElement('div');title.className='source-title';title.textContent=(i===0&&result.citations.length?'[1] ':'')+hit.title;
      const meta=document.createElement('div');meta.className='source-meta';meta.textContent=hit.tenant.toUpperCase()+' · VERSION '+hit.version+' · '+(hit.active?'ACTIVE':'ARCHIVED')+' · SCORE '+hit.score.toFixed(3);
      const text=document.createElement('p');text.textContent=hit.text;
      const bar=document.createElement('div');bar.className='score-bar';const fill=document.createElement('i');fill.style.width=Math.max(0,Math.min(100,hit.score*100))+'%';bar.append(fill);
      card.append(title,meta,text,bar);$('sources').append(card);
    });
    $('raw').textContent=JSON.stringify(result,null,2);
  } catch(e) { $('error').textContent=e.message;$('error').classList.remove('hidden'); }
  finally { $('ask').disabled=false;$('ask').textContent='Find evidence ↗'; }
});
fetch('/health').then(r=>r.json()).then(()=>{$('connection').textContent='● Evidence index ready';}).catch(()=>{$('connection').textContent='API unavailable';});
fetch('/static/metrics.json').then(r=>r.json()).then(m=>{
  $('hitRate').textContent=(m.hit_at_1*100).toFixed(1)+'%';$('scaleCount').textContent=m.scale_documents.toLocaleString();
  $('scaleNote').textContent='Repeated templates · '+m.scale_p95_ms+' ms search P95';
}).catch(()=>{});
