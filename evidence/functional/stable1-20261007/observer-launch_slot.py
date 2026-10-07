"""Frozen D025 host-slot launcher; requires immediately preceding operator UI check."""
import json,pathlib,subprocess,time,sys,os
from pal.native import native_environment
slot=sys.argv[1]; percent=int(sys.argv[2]); contract=json.loads(pathlib.Path('tests/fixtures/stable1_real_ui_v3.json').read_text())
assert slot in contract['host_limits'] and sum(contract['host_limits'].values())==32
run_name=sys.argv[3] if len(sys.argv)>3 else 'stable1-ui-20261007'
assert run_name in ('stable1-ui-20261007','stable1-ui-20261007-run2')
root=pathlib.Path('runtime')/run_name/slot; root.mkdir(parents=True,exist_ok=True); assert not (root/'state.db').exists()
evidence=pathlib.Path('evidence/functional')/('stable1-20261007-run2' if run_name.endswith('-run2') else 'stable1-20261007')/slot; evidence.mkdir(parents=True,exist_ok=True)
r=subprocess.run(['/Users/hattoritoshiyasu/.local/bin/claude','auth','status'],capture_output=True,text=True,env=native_environment(),timeout=15); value=json.loads(r.stdout); safe={k:value.get(k) for k in ('loggedIn','authMethod','subscriptionType')}
assert r.returncode==0 and safe=={'loggedIn':True,'authMethod':'claude.ai','subscriptionType':'pro'}
access={'verified_at':time.time(),'auth':safe,'usage_ui':{'url':'https://claude.ai/settings/usage','plan':'Pro','session_percent':percent,'week_percent':15,'credits_enabled':False,'purchased':'$0','month':'$0.00','auto_reload':'OFF'},'limit':contract['host_limits'][slot]}
(evidence/'access.json').write_text(json.dumps(access,indent=2)+'\n'); proof=root/'proof.json'; proof.write_text(json.dumps({'verified_at':access['verified_at'],'no_extra_charge':True,'route':'official_claude_pro'})+'\n')
os.execv(sys.executable,[sys.executable,'-m','pal.server','--db',str(root/'state.db'),'--port','0','--provider','official_claude_pro','--access-proof',str(proof),'--native-call-limit',str(access['limit'])])
