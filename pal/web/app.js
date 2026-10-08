'use strict';
const isInspect = location.pathname === '/inspect';
let previous = '';
let pending = null;
const uiSession=crypto.randomUUID();
const acknowledgements=[];
const choiceRequests=new Map();
const choicesInFlight=new Set();
const answerDrafts=new Map();
const answerRequests=new Map();
const answersInFlight=new Set();
const controlRequests=new Map();
const controlsInFlight=new Set();
const correctionDrafts=new Map();
function receipt(){const target=document.getElementById('session-receipt');if(target)target.textContent=JSON.stringify({session_id:uiSession,accepted_turns:acknowledgements.length,acknowledgements},null,2);}
receipt();
function node(tag,text,className){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(className)n.className=className;return n;}
async function applyControl(identity,text,control,goal_id){
  if(controlsInFlight.has(identity))return false;
  controlsInFlight.add(identity);
  const old=controlRequests.get(identity);
  if(!old||old.text!==text)controlRequests.set(identity,{key:'ui:'+uiSession+':'+crypto.randomUUID(),text,control,...(goal_id?{goal_id}:{})});
  const payload=controlRequests.get(identity);
  try{
    const response=await fetch('/api/message',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    if(!response.ok)throw new Error('Control rejected');const ack=await response.json();
    if(!acknowledgements.some(a=>a.key===payload.key))acknowledgements.push({key:payload.key,record_id:ack.record_id,goal_id:ack.goal?ack.goal.id:null,intent:ack.intent,action:ack.action,accepted_at:new Date().toISOString()});
    receipt();document.getElementById('error').textContent='';return true;
  }catch(error){document.getElementById('error').textContent='Control not confirmed. Check the current work before retrying. / 操作を確認できません。現在の作業を確認してから再試行してください。';return false;}
  finally{controlsInFlight.delete(identity);await refresh();}
}
function workControls(goal){
  const root=node('div');
  const actions=goal.state==='paused'?['resume','cancel']:['queued','running'].includes(goal.state)?['pause','cancel']:['waiting_input','failed','unknown'].includes(goal.state)?['cancel']:[];
  for(const action of actions){
    const identity=goal.id+':'+goal.epoch+':'+action;
    const button=node('button',({pause:'Pause / 一時停止',resume:'Resume / 再開',cancel:'Stop / 中止'})[action]);button.type='button';button.disabled=controlsInFlight.has(identity);
    button.addEventListener('click',()=>applyControl(identity,action,{action,epoch:goal.epoch},goal.id));root.append(button);
  }
  if(['queued','running','paused','waiting_input','failed'].includes(goal.state)){
    const identity=goal.id+':'+goal.epoch+':correct';const details=node('details');details.append(node('summary','Correct work / 作業を訂正'));
    const form=node('form');form.className='correction-form';const label=node('label','Revised request / 訂正後の依頼');const input=node('textarea');input.maxLength=12000;input.required=true;input.value=correctionDrafts.get(identity)||'';input.addEventListener('input',()=>correctionDrafts.set(identity,input.value));label.append(input);
    const button=node('button','Apply correction / 訂正を適用');button.type='submit';button.disabled=controlsInFlight.has(identity);form.append(label,button);details.append(form);root.append(details);
    form.addEventListener('submit',async event=>{event.preventDefault();if(!input.value.trim())return;const text=input.value;if(await applyControl(identity,text,{action:'correct',text,epoch:goal.epoch},goal.id)){correctionDrafts.delete(identity);input.value='';}});
  }
  return root;
}
function artifactLink(id){
  const a=node('a','Open local artifact / 成果物を開く');a.href='/api/artifact/'+encodeURIComponent(id);a.target='_blank';a.rel='noopener';
  fetch('/api/artifact_status/'+encodeURIComponent(id)).then(response=>{if(!response.ok)throw new Error('Status unavailable');return response.json();}).then(status=>{
    a.textContent=(status.role==='preview'?'Open incomplete preview / 未完成の下書きを開く':'Open local draft / 下書きを開く')+(status.stale?' · reference stopped / AI参照停止':'');
  }).catch(()=>{a.textContent+=' · status unavailable / 状態確認不可';});return a;
}
function answerForm(goal,question){
  const identity=goal.id+':'+question.id+':'+goal.epoch;
  const form=node('form');form.className='answer-form';const label=node('label','Your answer / 回答');const input=node('textarea');
  input.maxLength=12000;input.required=true;input.value=answerDrafts.get(identity)||'';label.append(input);
  input.addEventListener('input',()=>answerDrafts.set(identity,input.value));
  const button=node('button','Send answer / 回答を送信');button.type='submit';button.disabled=answersInFlight.has(identity);form.append(label,button);
  form.addEventListener('submit',async event=>{
    event.preventDefault();if(answersInFlight.has(identity)||!input.value.trim())return;
    answersInFlight.add(identity);button.disabled=true;
    const old=answerRequests.get(identity);
    if(!old||old.text!==input.value)answerRequests.set(identity,{key:'ui:'+uiSession+':'+crypto.randomUUID(),text:input.value,goal_id:goal.id,control:{action:'input',text:input.value,question_id:question.id,epoch:goal.epoch}});
    const payload=answerRequests.get(identity);
    try{
      const response=await fetch('/api/message',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
      if(!response.ok)throw new Error('Answer rejected');const ack=await response.json();
      if(!acknowledgements.some(a=>a.key===payload.key))acknowledgements.push({key:payload.key,record_id:ack.record_id,goal_id:ack.goal?ack.goal.id:null,intent:ack.intent,action:ack.action,accepted_at:new Date().toISOString()});
      answerDrafts.delete(identity);answerRequests.delete(identity);input.value='';receipt();document.getElementById('error').textContent='';answersInFlight.delete(identity);await refresh();
    }catch(error){document.getElementById('error').textContent='Answer not confirmed. Your text is retained; check the current question before retrying. / 回答を確認できません。本文は保持しています。現在の質問を確認して再試行してください。';}
    finally{answersInFlight.delete(identity);button.disabled=false;}
  });return form;
}
async function selectWork(selection, choice){
  if(choicesInFlight.has(selection.selection_id))return;
  choicesInFlight.add(selection.selection_id);
  const identity=selection.selection_id+':'+choice.goal_id;
  if(!choiceRequests.has(identity))choiceRequests.set(identity,{key:'ui:'+uiSession+':'+crypto.randomUUID(),text:'Select work target',control:{action:'select',selection_id:selection.selection_id,source_key:selection.source_key,target_id:choice.goal_id}});
  const payload=choiceRequests.get(identity);
  try{
    const response=await fetch('/api/message',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});
    if(!response.ok)throw new Error('Choice rejected');
    const ack=await response.json();
    if(!acknowledgements.some(a=>a.key===payload.key))acknowledgements.push({key:payload.key,record_id:ack.record_id,goal_id:ack.goal?ack.goal.id:null,intent:ack.intent,action:ack.action,accepted_at:new Date().toISOString()});
    receipt();document.getElementById('error').textContent='';await refresh();
  }catch(error){document.getElementById('error').textContent='Choice not confirmed. Check current state before retrying. / 選択を確認できません。状態を確認してから再試行してください。';}
  finally{choicesInFlight.delete(selection.selection_id);}
}
function render(data){
  for(const ack of acknowledgements){
    const turn=(data.primary_turns||[]).find(t=>t.client_key===ack.key);
    if(turn){ack.primary_status=turn.status;if(turn.outcome){const outcome=JSON.parse(turn.outcome);ack.intent=outcome.intent;ack.goal_id=outcome.goal?outcome.goal.id:null;ack.action=outcome.action||null;}}
  }
  receipt();
  const access=data.provider_status||{mode:'mock'};
  document.getElementById('provider').textContent='Provider: '+data.provider+' · local drafts / ローカル下書き'+(access.mode==='mock'?' · Mock / 模擬応答':' · Official live / 公式実モデル · remaining / 残り '+access.calls_remaining+' · '+(access.authorized_now?'Proof valid / 利用証明有効':'Unavailable / 利用不可: '+access.unavailable_reason)+(Number.isFinite(access.expires_at)?' · New requests until / 新規依頼の利用期限: '+new Date(access.expires_at*1000).toLocaleString(undefined,{timeZoneName:'short'}):'')+(access.last_error?' · '+access.last_error:''));
  if(isInspect){
    const root=document.getElementById('inspect');root.replaceChildren();
    for(const table of ['goals','attempts','outcomes','receipts','artifacts','rejections','records','notes','revisions','acceptances','events','approvals','questions','primary_turns']){
      const rows=data[table]||[];const d=node('details');d.open=['goals','attempts','outcomes','receipts'].includes(table);d.append(node('summary',table+' / '+({goals:'作業',attempts:'実行履歴',outcomes:'検証結果',receipts:'検証証拠',artifacts:'成果物',rejections:'拒否記録',records:'会話・履歴',notes:'記憶メモ',revisions:'改訂履歴',acceptances:'受入条件',events:'通知履歴',approvals:'承認',questions:'質問・回答履歴',primary_turns:'会話の処理履歴'}[table])+' ('+rows.length+')'),node('pre',JSON.stringify(rows,null,2)));root.append(d);
    }
  } else {
    const root=document.getElementById('conversation');root.replaceChildren();
    for(const record of data.records){
      const card=node('article',undefined,record.role);card.append(node('strong',record.role+' / '+(record.role==='user'?'あなた':'アシスタント')+(record.usable?'':' · reference stopped / 参照停止')));
      if(record.source_event_id){
        let event;try{event=JSON.parse(record.content);}catch{event=null;}
        if(event){const labels={'goal.incomplete_preview':'Incomplete preview retained; work is not complete. / 未完成の下書きを保存しました。作業は完了していません。','goal.queued':'Work accepted. / 作業を受け付けました。','attempt.claimed':'Preparing your draft… / 下書きを作成中です。','goal.completed':'Your local draft is ready. / 下書きが完成しました。','goal.cancel':'Work stopped. / 作業を中止しました。','goal.pause':'Work paused. / 作業を一時停止しました。','goal.resume':'Work resumed. / 作業を再開しました。','goal.correct':'Your correction was applied. / 訂正を適用しました。','goal.input':'Your answer was accepted. / 回答を受け付けました。','goal.waiting_input':'Your input is needed. / 入力をお待ちしています。','attempt.error':'Work failed. See Inspect for details. / 作業に失敗しました。「状態を見る」で詳細を確認できます。','attempt.fail':'The outcome did not pass its checks. / 結果は検証に合格しませんでした。','attempt.unverified':'The outcome is unverified. / 結果は未検証です。','attempt.abandoned':'Unfinished work recovered after restart. / 再起動後、未完了の作業を復旧しました。','reference.stopped':'Reference stopped. / 履歴のAI参照を停止しました。','goal.reference_stopped':'Work requires fresh context. / 作業には新しい情報が必要です。'};card.append(node('p',labels[event.event]||'Work status updated. / 作業状況を更新しました。'));if(event.detail.artifact_id)card.append(artifactLink(event.detail.artifact_id));}
      }else card.append(node('p',record.content+(record.content==='I have recorded your message. This response uses the mock provider.'?' / メッセージを記録しました。この応答は模擬応答です。':'')));
      if(record.role==='user'&&record.usable){const forget=node('button','Stop AI reference / AI参照を停止');forget.type='button';forget.addEventListener('click',()=>applyControl('forget:'+record.id,'Stop reference',{source_id:record.id}));card.append(forget);}
      root.append(card);
    }
    const work=document.getElementById('work');work.replaceChildren();
    for(const turn of data.primary_turns||[])if(turn.status==='pending')work.append(node('p','Interpreting your message… / メッセージの意図を確認しています…'));
    const visible=new Set(data.goals.slice(-3).map(g=>g.id));for(const goal of data.goals)if(!['completed','cancelled'].includes(goal.state))visible.add(goal.id);
    for(const goal of data.goals.filter(g=>visible.has(g.id))){
      const card=node('article');card.append(node('strong','Work / 作業: '+goal.state+' / '+({queued:'待機中',running:'実行中',waiting_input:'入力待ち',paused:'一時停止',completed:'完了',cancelled:'中止',failed:'失敗',unknown:'結果不明'}[goal.state]||goal.state)));
      const revision=(data.revisions||[]).find(r=>r.goal_id===goal.id&&r.revision===goal.revision);if(revision)card.append(node('p',revision.specification));
      const question=(data.questions||[]).find(q=>q.id===goal.question_id&&q.goal_id===goal.id&&q.status==='open'&&q.epoch===goal.epoch&&q.revision===goal.revision);
      card.append(node('p',question?question.prompt:(goal.reason?goal.reason.replaceAll('_',' '):'')));
      if(goal.state==='waiting_input'&&question)card.append(answerForm(goal,question));card.append(workControls(goal));work.append(card);
    }
    for(const selection of data.selections||[]){
      const card=node('article');card.append(node('strong','Choose work / 対象を選択: '+selection.status));
      for(const choice of selection.choices){const button=node('button',choice.label);button.type='button';button.addEventListener('click',()=>selectWork(selection,choice));card.append(button);}
      if(selection.status==='stale'||selection.status==='unavailable')card.append(node('p','Send a new request with a specific target. / 対象を明示して、改めて依頼してください。'));
      work.append(card);
    }
  }
}
async function refresh(){try{const response=await fetch('/api/state');if(!response.ok)throw new Error('State unavailable');const data=await response.json();const signature=JSON.stringify(data);const error=document.getElementById('error');if(error.textContent==='State unavailable. Your recorded work is retained. / 状態を取得できません。保存済みの作業は保持されています。')error.textContent='';if(signature!==previous){render(data);previous=signature;}}catch(error){document.getElementById('error').textContent='State unavailable. Your recorded work is retained. / 状態を取得できません。保存済みの作業は保持されています。';}}
const form=document.getElementById('message');
if(form)form.addEventListener('submit',async event=>{
  event.preventDefault();const input=document.getElementById('text');const button=form.querySelector('button');button.disabled=true;document.getElementById('error').textContent='';
  if(!pending || pending.text!==input.value)pending={key:'ui:'+uiSession+':'+Date.now()+':'+crypto.randomUUID(),text:input.value};
  const payload=pending;
  try{const response=await fetch('/api/message',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});if(!response.ok)throw new Error('Message rejected');const ack=await response.json();if(!acknowledgements.some(a=>a.key===payload.key))acknowledgements.push({key:payload.key,record_id:ack.record_id,goal_id:ack.goal?ack.goal.id:null,intent:ack.intent,action:ack.action||null,primary_status:ack.primary_status||null,accepted_at:new Date().toISOString()});receipt();input.value='';pending=null;await refresh();}catch(error){document.getElementById('error').textContent='Message could not be accepted. Keep your text and check Inspect. / 入力を受け付けられませんでした。本文を残したまま「状態を見る」を確認してください。';}finally{button.disabled=false;}
});
refresh();setInterval(refresh,1000);
