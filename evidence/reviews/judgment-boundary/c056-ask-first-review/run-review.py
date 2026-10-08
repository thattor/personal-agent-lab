from pathlib import Path
import datetime
import hashlib
import json
import os
import signal
import subprocess
import time

ROOT=Path('/private/tmp/personal-agent-lab-stable0-20261006')
OUT=Path(__file__).resolve().parent
CLI='/Users/hattoritoshiyasu/.local/bin/claude'
assert not (OUT/'start.json').exists(), 'This recorded one-call consultation has already started'
env=dict(os.environ)
for key in ['ANTHROPIC_API_KEY','ANTHROPIC_AUTH_TOKEN','ANTHROPIC_BASE_URL','CLAUDE_CODE_OAUTH_TOKEN','CLAUDE_CODE_USE_BEDROCK','CLAUDE_CODE_USE_VERTEX','CLAUDE_CODE_USE_FOUNDRY']:
    env.pop(key,None)
auth=subprocess.run([CLI,'auth','status'],cwd=ROOT,env=env,capture_output=True,timeout=30)
data=json.loads(auth.stdout)
assert auth.returncode == 0 and data.get('loggedIn') and data.get('authMethod')=='claude.ai' and data.get('apiProvider')=='firstParty' and data.get('subscriptionType')=='pro'
access={'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'auth':'existing official Claude Pro / claude.ai / firstParty','fresh_ui_source':'CUA Chrome tab172833127, claude.ai/new#settings/usage, observed in this consultation before call','usage_ui':{'plan':'Pro','session_used_percent':10,'weekly_used_percent':27,'extra_usage_switch':0,'extra_usage_amount':'$0','auto_reload':'OFF'},'tools':[],'mcpServers':{},'safe_mode':True,'max_turns':1,'max_seconds':240,'paid_fallback':False,'retries':0,'authority':'PAL development authorized coordination request for one small official Opus design consultation under current owner operating instruction and AGENTS consultation rule'}
(OUT/'access.json').write_text(json.dumps(access,ensure_ascii=False,indent=2)+'\n')
cmd=[CLI,'-p','--model','opus','--permission-mode','plan','--safe-mode','--tools','','--strict-mcp-config','--mcp-config','{"mcpServers":{}}','--disable-slash-commands','--max-turns','1','--no-session-persistence','--output-format','text']
started=time.monotonic()
timeout=False
with (OUT/'question.txt').open('rb') as stdin,(OUT/'opus-response.txt').open('wb') as stdout,(OUT/'opus-stderr.txt').open('wb') as stderr:
    process=subprocess.Popen(cmd,cwd=ROOT,env=env,stdin=stdin,stdout=stdout,stderr=stderr,start_new_session=True)
    (OUT/'start.json').write_text(json.dumps({'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pid':process.pid,'prompt_sha256':hashlib.sha256((OUT/'question.txt').read_bytes()).hexdigest()},indent=2)+'\n')
    try:process.wait(timeout=240)
    except subprocess.TimeoutExpired:
        timeout=True
        os.killpg(process.pid,signal.SIGTERM)
        try:process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid,signal.SIGKILL)
            process.wait()
answer=(OUT/'opus-response.txt').read_bytes()
result={'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'elapsed_seconds':round(time.monotonic()-started,3),'exit_code':process.returncode,'timeout':timeout,'response_bytes':len(answer),'stderr_bytes':(OUT/'opus-stderr.txt').stat().st_size,'response_sha256':hashlib.sha256(answer).hexdigest(),'response_complete':process.returncode==0 and not timeout and answer.rstrip().endswith(b'REVIEW_COMPLETE'),'attempts':1,'fallback':False,'retry':False}
(OUT/'completion.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result),flush=True)
