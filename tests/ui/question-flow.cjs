// Actual shipped UI, synthetic DOM/HTTP: not human or live-browser evidence.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
class Element {
  constructor(tag){this.tag=tag;this.children=[];this.listeners={};this.textContent='';this.value='';}
  append(...children){this.children.push(...children);}
  replaceChildren(...children){this.children=children;}
  addEventListener(event,callback){this.listeners[event]=callback;}
}
const elements=Object.fromEntries(['provider','conversation','work','error','session-receipt'].map(id=>[id,new Element(id)]));
const posts=[];
const state={provider:'mock',records:[],goals:[],questions:[],receipts:[],selections:[]};
for(let i=0;i<5;i++){
 state.goals.push({id:'g'+i,state:'waiting_input',question_id:'q'+i,epoch:2,revision:1,reason:'Question '+i});
 state.questions.push({id:'q'+i,goal_id:'g'+i,status:'open',epoch:2,revision:1,prompt:'Question '+i});
}
state.goals.push({id:'diagnostic',state:'waiting_input',question_id:'phantom',epoch:1,revision:1,reason:'reference_stopped'});
const context={console,JSON,Error,Map,Set,encodeURIComponent,location:{pathname:'/'},
 crypto:{randomUUID:()=>String(Math.random())},setInterval:()=>{},
 document:{getElementById:id=>elements[id]||null,createElement:tag=>new Element(tag)},
 fetch:async(path,options)=>{
  if(options){posts.push(JSON.parse(options.body));return {ok:true,json:async()=>({record_id:'accepted',goal:{id:posts.at(-1).goal_id},intent:'control',action:'input'})};}
  if(path.startsWith('/api/artifact_status/'))return {ok:true,json:async()=>({role:'preview',reason:'incomplete_template',stale:true})};
  return {ok:true,json:async()=>state};
 }};
vm.createContext(context);vm.runInContext(fs.readFileSync('pal/web/app.js','utf8'),context);
function all(root,tag){return [...(root.tag===tag?[root]:[]),...root.children.flatMap(c=>all(c,tag))];}
(async()=>{
 await context.refresh();
 let forms=all(elements.work,'form').filter(f=>f.className==='answer-form');assert.equal(forms.length,5,'all waiting questions, not last3; no phantom form');
 let input=all(forms[0],'textarea')[0];input.value='Saturday';input.listeners.input();
 context.render(state);forms=all(elements.work,'form').filter(f=>f.className==='answer-form');input=all(forms[0],'textarea')[0];
 assert.equal(input.value,'Saturday','polling preserves answer draft');
 await forms[0].listeners.submit({preventDefault(){}});
 assert.equal(posts.length,1);
 assert.equal(posts[0].goal_id,'g0');assert.equal(posts[0].control.question_id,'q0');assert.equal(posts[0].control.epoch,2);assert.equal(posts[0].control.text,'Saturday');
 state.questions[0].epoch=99;context.render(state);assert.equal(all(elements.work,'form').filter(f=>f.className==='answer-form').length,4,'stale binding has no answer form');
 const link=context.artifactLink('artifact');await new Promise(resolve=>setImmediate(resolve));
 assert.match(link.textContent,/preview|未完成/i);assert.match(link.textContent,/stopped|参照停止/i);
 console.log('PASS: shipped UI renders five bound questions, tolerates diagnostic wait, preserves drafts, posts exact binding and labels stale preview.');
})().catch(error=>{console.error(error);process.exitCode=1;});
