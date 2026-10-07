// Shipped JS with synthetic DOM/HTTP; not browser, live model or human evidence.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
class Element {
 constructor(tag){this.tag=tag;this.children=[];this.listeners={};this.textContent='';this.value='';}
 append(...children){this.children.push(...children);}
 replaceChildren(...children){this.children=children;}
 addEventListener(event,callback){this.listeners[event]=callback;}
 querySelector(tag){return all(this,tag)[0];}
}
function all(root,tag){return [...(root.tag===tag?[root]:[]),...root.children.flatMap(c=>all(c,tag))];}
const elements=Object.fromEntries(['provider','conversation','work','error','session-receipt','message','text'].map(id=>[id,new Element(id)]));
elements.message.append(new Element('button'));
const posts=[];
const state={provider:'mock',records:[{id:'source',role:'user',content:'Friday',usable:1}],primary_turns:[],goals:[{id:'g',state:'paused',epoch:7,revision:2}],questions:[],revisions:[],selections:[]};
const context={console,JSON,Error,Map,Set,Date,encodeURIComponent,location:{pathname:'/'},crypto:{randomUUID:()=>String(Math.random())},setInterval:()=>{},document:{getElementById:id=>elements[id]||null,createElement:tag=>new Element(tag)},fetch:async(path,options)=>{
 if(options){const payload=JSON.parse(options.body);posts.push(payload);return {ok:true,json:async()=>({record_id:'r'+posts.length,goal:null,intent:payload.control?'control':'conversation',primary_status:payload.control?undefined:'pending'})};}
 return {ok:true,json:async()=>state};
}};
vm.createContext(context);vm.runInContext(fs.readFileSync('pal/web/app.js','utf8'),context);
(async()=>{
 await context.refresh();
 const button=all(elements.work,'button').find(b=>b.textContent.startsWith('Resume'));
 await button.listeners.click();
 assert.equal(posts[0].goal_id,'g');assert.equal(posts[0].control.action,'resume');assert.equal(posts[0].control.epoch,7);
 let form=all(elements.work,'form').find(f=>f.className==='correction-form');
 let input=all(form,'textarea')[0];input.value='A corrected draft';input.listeners.input();context.render(state);
 form=all(elements.work,'form').find(f=>f.className==='correction-form');input=all(form,'textarea')[0];assert.equal(input.value,'A corrected draft');
 await form.listeners.submit({preventDefault(){}});assert.equal(posts[1].control.action,'correct');assert.equal(posts[1].control.text,'A corrected draft');assert.equal(posts[1].control.epoch,7);
 const forget=all(elements.conversation,'button').find(b=>b.textContent.startsWith('Stop AI'));
 await forget.listeners.click();assert.equal(posts[2].control.source_id,'source');assert(!posts[2].goal_id);
 elements.text.value='A natural request';await elements.message.listeners.submit({preventDefault(){}});
 const key=posts.at(-1).key;let receipt=JSON.parse(elements['session-receipt'].textContent);const count=receipt.accepted_turns;
 assert.equal(receipt.acknowledgements.at(-1).primary_status,'pending');
 state.primary_turns=[{client_key:key,status:'complete',outcome:JSON.stringify({intent:'draft',goal:{id:'new-goal'}})}];
 await context.refresh();receipt=JSON.parse(elements['session-receipt'].textContent);
 assert.equal(receipt.accepted_turns,count);assert.equal(receipt.acknowledgements.at(-1).primary_status,'complete');assert.equal(receipt.acknowledgements.at(-1).goal_id,'new-goal');assert.equal(receipt.acknowledgements.at(-1).intent,'draft');
 console.log('PASS: direct epoch-bound controls, correction draft retention, source-reference stop, pending receipt updated from committed Primary outcome without duplicate input.');
})().catch(error=>{console.error(error);process.exitCode=1;});
