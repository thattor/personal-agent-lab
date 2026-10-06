'use strict';
const isInspect = location.pathname === '/inspect';
let previous = '';
let pending = null;
const uiSession=crypto.randomUUID();
const acknowledgements=[];
function receipt(){const target=document.getElementById('session-receipt');if(target)target.textContent=JSON.stringify({session_id:uiSession,accepted_turns:acknowledgements.length,acknowledgements},null,2);}
receipt();
function node(tag,text,className){const n=document.createElement(tag);if(text!==undefined)n.textContent=text;if(className)n.className=className;return n;}
function artifactLink(id){const a=node('a','Open local draft / 下書きを開く');a.href='/api/artifact/'+encodeURIComponent(id);a.target='_blank';a.rel='noopener';return a;}
function render(data){
  const access=data.provider_status||{mode:'mock'};
  document.getElementById('provider').textContent='Provider: '+data.provider+' · local drafts / ローカル下書き'+(access.mode==='mock'?' · Mock / 模擬応答':' · Official live / 公式実モデル · remaining / 残り '+access.calls_remaining+' · '+(access.authorized_now?'Proof valid / 利用証明有効':'Unavailable / 利用不可: '+access.unavailable_reason)+(access.last_error?' · '+access.last_error:''));
  if(isInspect){
    const root=document.getElementById('inspect');root.replaceChildren();
    for(const table of ['goals','attempts','outcomes','receipts','artifacts','rejections','records','notes','revisions','acceptances','events','approvals']){
      const d=node('details');d.open=['goals','attempts','outcomes','receipts'].includes(table);d.append(node('summary',table+' / '+({goals:'作業',attempts:'実行履歴',outcomes:'検証結果',receipts:'検証証拠',artifacts:'成果物',rejections:'拒否記録',records:'会話・履歴',notes:'記憶メモ',revisions:'改訂履歴',acceptances:'受入条件',events:'通知履歴',approvals:'承認'}[table])+' ('+data[table].length+')'),node('pre',JSON.stringify(data[table],null,2)));root.append(d);
    }
  } else {
    const root=document.getElementById('conversation');root.replaceChildren();
    for(const record of data.records){
      const card=node('article',undefined,record.role);card.append(node('strong',record.role+' / '+(record.role==='user'?'あなた':'アシスタント')+(record.usable?'':' · reference stopped / 参照停止')));
      if(record.source_event_id){
        let event;try{event=JSON.parse(record.content);}catch{event=null;}
        if(event){const labels={'goal.queued':'Work accepted. / 作業を受け付けました。','attempt.claimed':'Preparing your draft… / 下書きを作成中です。','goal.completed':'Your local draft is ready. / 下書きが完成しました。','goal.cancel':'Work stopped. / 作業を中止しました。','goal.pause':'Work paused. / 作業を一時停止しました。','goal.resume':'Work resumed. / 作業を再開しました。','goal.correct':'Your correction was applied. / 訂正を適用しました。','goal.input':'Your answer was accepted. / 回答を受け付けました。','goal.waiting_input':'Your input is needed. / 入力をお待ちしています。','attempt.error':'Work failed. See Inspect for details. / 作業に失敗しました。「状態を見る」で詳細を確認できます。','attempt.fail':'The outcome did not pass its checks. / 結果は検証に合格しませんでした。','attempt.unverified':'The outcome is unverified. / 結果は未検証です。','attempt.abandoned':'Unfinished work recovered after restart. / 再起動後、未完了の作業を復旧しました。','reference.stopped':'Reference stopped. / 履歴のAI参照を停止しました。','goal.reference_stopped':'Work requires fresh context. / 作業には新しい情報が必要です。'};card.append(node('p',labels[event.event]||'Work status updated. / 作業状況を更新しました。'));if(event.detail.artifact_id)card.append(artifactLink(event.detail.artifact_id));}
      }else card.append(node('p',record.content+(record.content==='I have recorded your message. This response uses the mock provider.'?' / メッセージを記録しました。この応答は模擬応答です。':'')));
      root.append(card);
    }
    const work=document.getElementById('work');work.replaceChildren();
    for(const goal of data.goals.slice(-3)){const card=node('article');card.append(node('strong','Work / 作業: '+goal.state+' / '+({queued:'待機中',running:'実行中',waiting_input:'入力待ち',paused:'一時停止',completed:'完了',cancelled:'中止',failed:'失敗',unknown:'結果不明'}[goal.state]||goal.state)),node('p',goal.reason ? goal.reason.replaceAll('_',' ') : ''));work.append(card);}
  }
}
async function refresh(){try{const response=await fetch('/api/state');if(!response.ok)throw new Error('State unavailable');const data=await response.json();const signature=JSON.stringify(data);const error=document.getElementById('error');if(error.textContent==='State unavailable. Your recorded work is retained. / 状態を取得できません。保存済みの作業は保持されています。')error.textContent='';if(signature!==previous){render(data);previous=signature;}}catch(error){document.getElementById('error').textContent='State unavailable. Your recorded work is retained. / 状態を取得できません。保存済みの作業は保持されています。';}}
const form=document.getElementById('message');
if(form)form.addEventListener('submit',async event=>{
  event.preventDefault();const input=document.getElementById('text');const button=form.querySelector('button');button.disabled=true;document.getElementById('error').textContent='';
  if(!pending || pending.text!==input.value)pending={key:'ui:'+uiSession+':'+Date.now()+':'+crypto.randomUUID(),text:input.value};
  const payload=pending;
  try{const response=await fetch('/api/message',{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)});if(!response.ok)throw new Error('Message rejected');const ack=await response.json();acknowledgements.push({key:payload.key,record_id:ack.record_id,goal_id:ack.goal?ack.goal.id:null,intent:ack.intent,action:ack.action||null,accepted_at:new Date().toISOString()});receipt();input.value='';pending=null;await refresh();}catch(error){document.getElementById('error').textContent='Message could not be accepted. Keep your text and check Inspect. / 入力を受け付けられませんでした。本文を残したまま「状態を見る」を確認してください。';}finally{button.disabled=false;}
});
refresh();setInterval(refresh,1000);
