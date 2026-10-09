'use strict';
const $ = id => document.getElementById(id);
let pendingKey = null, turnId = null, previousWorker = null;
const answerKeys = new Map();
const key = () => crypto.randomUUID();
const labels = {pending:'処理待ち',committed:'会話を保存しました',failed:'処理できませんでした',interrupted:'中断しました',held:'終了確認を待っています',idle:'待機中',running:'処理中',closing:'終了中',closed:'終了しました',queued:'作業待ち',waiting_input:'回答待ち',paused:'一時停止中',cancelled:'中止済み',completed:'保存・構造確認済み'};
async function api(path, data) {
  const response = await fetch(path, data === undefined ? {} : {method:'POST', headers:{'Content-Type':'application/json'}, body:JSON.stringify(data)});
  const result = await response.json();
  if (!response.ok || result.ok === false) throw new Error(result.error?.message || '操作できませんでした');
  return result.ok === true ? result.value : result;
}
function text(parent, content) { const node = document.createElement('pre'); node.textContent = content; parent.appendChild(node); }
function button(parent, label, action) { const node = document.createElement('button'); node.textContent=label; node.addEventListener('click', () => action().catch(showError)); parent.appendChild(node); }
function showError(error) { $('error').textContent=error.message; }
async function refresh() {
  const status=await api('/api/status'); previousWorker=status.worker_status; $('status').textContent='テスト用mock — '+(labels[status.worker_status] || '状態不明')+'。実モデルは利用できません。';
  if (turnId) {
    const turn=await api('/api/turns?turn_id='+encodeURIComponent(turnId));
    $('turn').textContent=(labels[turn.status] || '状態不明')+'\n'+(turn.reply || turn.error?.message || '');
  }
  const works=await api('/api/works'); $('works').replaceChildren();
  for (const work of works.works) {
    const block=document.createElement('article'); $('works').appendChild(block);
    text(block,(work.brief_summary || '本文を参照できない作業')+'\n'+(labels[work.state] || '状態不明'));
    for (const [command,label] of [['pause','一時停止'],['resume','再開'],['cancel','中止']]) button(block,label,async()=>{await api('/api/controls',{key:key(),work_ref:work.work_ref,command});await refresh();});
    for (const question of work.open_questions || []) {
      text(block,question.text || '不足情報への回答を入力してください。');
      const answer=document.createElement('input'); answer.placeholder='回答（例: 10月12日 午後2時）'; block.appendChild(answer);
      button(block,'この質問に回答',async()=>{
        if (!answerKeys.has(question.id)) answerKeys.set(question.id,{client_key:key(),text:answer.value});
        const original=answerKeys.get(question.id);
        if (original.text!==answer.value) throw new Error('前の回答の保存確認を待ってから変更してください。');
        const receipt=await api('/api/turns',original);
        turnId=receipt.turn_id;answerKeys.delete(question.id);await refresh();
      });
    }
    for (const ref of work.dependency_refs || []) button(block,'この資料のAI参照を停止',async()=>{await api('/api/source-stop',{key:key(),source_ref:ref});await refresh();});
  }
  const inspection=await api('/api/inspection'); $('results').replaceChildren();
  for (const item of inspection.items) for (const read of item.reads || []) if (read.ref.kind==='artifact') {
    text($('results'),read.result.ok ? read.result.value.content : read.result.error.message);
  }
}
$('submit').addEventListener('submit',async event=>{event.preventDefault();pendingKey=pendingKey || {client_key:key(),text:$('text').value};try {const receipt=await api('/api/turns',pendingKey);turnId=receipt.turn_id;pendingKey=null;await refresh();}catch(error){showError(error);}});
$('refresh').addEventListener('click',()=>refresh().catch(showError));
refresh().catch(showError);
setInterval(async()=>{try {const status=await api('/api/status');if(previousWorker!==status.worker_status) await refresh();}catch(error){showError(error);}},1500);
