// Run the actual UI refresh function with deterministic transport recovery.
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync('pal/web/app.js','utf8');
const refreshSource=source.slice(source.indexOf('async function refresh()'),source.indexOf('const form='));
const elements={error:{textContent:''}};
let mode='ok',renders=0;
const state={provider:'mock',records:[],goals:[]};
const context={document:{getElementById:id=>elements[id]},JSON,Error,
 render:()=>{renders++},fetch:async()=>{
 if(mode==='transport')throw new Error('offline');
 if(mode==='http')return {ok:false};
 if(mode==='json')return {ok:true,json:async()=>{throw new Error('bad JSON')}};
 return {ok:true,json:async()=>state};
}};
vm.createContext(context);vm.runInContext("let previous='';"+refreshSource,context);
(async()=>{
 await context.refresh();assert.equal(renders,1);
 for(const failure of ['transport','http','json']){
 mode=failure;await context.refresh();assert.match(elements.error.textContent,/State unavailable/);
 mode='ok';await context.refresh();assert.equal(elements.error.textContent,'','recovered unchanged state must clear stale warning');
 }
 // Recovery must not erase a separate message-submission failure.
 elements.error.textContent='Message could not be accepted. Keep your text and check Inspect.';
 await context.refresh();assert.match(elements.error.textContent,/Message could not be accepted/);
 assert.equal(renders,1,'unchanged data need not rerender');
 console.log('PASS: actual refresh clears recovered state warnings for transport/HTTP/JSON failures, preserves message failures, handles unchanged state.');
})().catch(e=>{console.error(e.message);process.exitCode=1});
