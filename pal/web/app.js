'use strict';
const isInspect = location.pathname === '/inspect';
let previous = '';
let pending = null;
const uiSession=crypto.randomUUID();
const acknowledgements=[];
function receipt(){const target=document.getElementById('session-receipt');if(target)target.textContent=JSON.stringify({session_id:uiSession,accepted_turns:acknowledgements.length,acknowledgements},null,2);}
receipt();
function node(tag,text,className){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(className)n.className=className;return n;}
function artifactLink(id){const a=node('a','Open local draft');a.href='/api/artifact/'+encodeURIComponent(id);a.target='_blank';a.rel='noopener';return a;}
function render(data){
  document.getElementById('provider').textContent='Provider: '+data.provider+' · local drafts';
  if(isInspect){
    const root=document.getElementById('inspect');root.replaceChildren();
    for(const table of ['goals','attempts','outcomes','receipts','artifacts','rejections','records','notes','revisions','acceptances','events','approvals']){
      const d=node('details');d.open=['goals','attempts','outcomes','receipts'].includes(table);d.append(node('summary',table+' ('+data[table].length+')'),node('pre',JSON.stringify(data[table],null,2)));root.append(d);
    }
  } else {
    const root=document.getElementById('conversation');root.replaceChildren();
    for(const record of data.records){
      const card=node('article',undefined,record.role);card.append(node('strong',record.role+(record.usable?'':' · reference stopped')));
      if(record.source_event_id){
        let event;try{event=JSON.parse(record.content);}catch{event=null;}
        if(event){const labels={'goal.queued':'Work accepted.','attempt.claimed':'Preparing your draft…','goal.completed':'Your local draft is ready.','goal.cancel':'Work stopped.','goal.pause':'Work paused.','goal.resume':'Work resumed.','goal.correct':'Your correction was applied.','goal.input':'Your answer was accepted.','goal.waiting_input':'Your input is needed.','attempt.error':'Work failed. See Inspect for details.','attempt.fail':'The outcome did not pass its checks.','attempt.unverified':'The outcome is unverified.','attempt.abandoned':'Unfinished work recovered after restart.','reference.stopped':'Reference stopped.','goal.reference_stopped':'Work requires fresh context.'};card.append(node('p',labels[event.event]||'Work status updated.'));if(event.detail.artifact_id)card.append(artifactLink(event.detail.artifact_id));}
      }else card.append(node('p',record.content));
      root.append(card);
    }
    const work=document.getElementById('work');work.replaceChildren();
    for(const goal of data.goals.slice(-3)){const card=node('article');card.append(node('strong','Work: '+goal.state),node('p',goal.reason ? goal.reason.replaceAll('_',' ') : ''));work.append(card);}
  }
}
async function refresh(){try{const response=await fetch('/api/state');if(!response.ok)throw new Error('State unavailable');const data=await response.json();const signature=JSON.stringify(data);const error=document.getElementById('error');if(error.textContent==='State unavailable. Your recorded work is retained.')error.textContent='';if(signature!==previous){render(data);previous=signature;}}catch(error){document.getElementById('error').textContent='State unavailable. Your recorded work is retained.';}}
const form=document.getElementById('message');
if(form)form.addEventListener('submit',async event=>{
  event.preventDefault();const input=document.getElementById('text');const button=form.querySelector('button');button.disabled=true;document.getElementById('error').textContent='';
  if(!pending || pending.text!==input.value)pending={key:'ui:'+uiSession+':'+Date.now()+':'+crypto.randomUUID(),text:input.value};
  const payload=pending;
  try{const response=await fetch('/api/message',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});if(!response.ok)throw new Error('Message rejected');const ack=await response.json();acknowledgements.push({key:payload.key,record_id:ack.record_id,goal_id:ack.goal?ack.goal.id:null,intent:ack.intent,action:ack.action||null,accepted_at:new Date().toISOString()});receipt();input.value='';pending=null;await refresh();}catch(error){document.getElementById('error').textContent='Message could not be accepted. Keep your text and check Inspect.';}finally{button.disabled=false;}
});
refresh();setInterval(refresh,1000);
