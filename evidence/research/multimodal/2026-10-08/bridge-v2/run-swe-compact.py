from pathlib import Path
import datetime
import hashlib
import json
import os
import signal
import subprocess
import tempfile
import time

ROOT = Path('/private/tmp/personal-agent-lab-stable0-20261006')
OUT = Path(__file__).resolve().parent / 'reviews' / 'swe-compact'
CLI = '/Users/hattoritoshiyasu/.local/bin/devin'
MODEL = 'swe-2-high'

def now():
    return datetime.datetime.now(datetime.timezone.utc).isoformat()

def execute(*args):
    return subprocess.run([CLI, *args], cwd=ROOT, capture_output=True, timeout=60)

# Account values are used only by the installed first-party client and are never retained here.
auth = execute('auth', 'status')
assert auth.returncode == 0 and b'Logged in (via Devin)' in auth.stdout + auth.stderr, 'Existing first-party authentication not confirmed'
models = execute('models', 'list', '--format', 'json')
assert models.returncode == 0, 'Model catalog unavailable'
catalog = json.loads(models.stdout)
entries = [v for f in catalog['families'] for v in f['variants'] if v['model_uid'] == MODEL]
assert entries and all(v.get('cost_tier') == 'Free' for v in entries), 'SWE-2 High Free unavailable'
for path in [ROOT/'.devin/config.json', ROOT/'.devin/config.local.json', ROOT/'.devin/mcp_config.json', ROOT/'.devin/mcp_config.local.json', Path('/Users/hattoritoshiyasu/.config/devin/mcp_config.json')]:
    assert not path.exists(), f'Unexpected additional config: {path}'
original = json.loads(Path('/Users/hattoritoshiyasu/.config/devin/config.json').read_text())
rules = ['read','grep','glob','write','edit','exec','fetch','Read(/**)','Write(/**)','Exec(*)','Fetch(*)','mcp__*','run_subagent','read_subagent']
config = {'version': original.get('version'), 'devin': original.get('devin', {}), 'agent': {'model': MODEL}, 'shell': original.get('shell', {}), 'hooks': {}, 'permissions': {'allow': [], 'deny': rules, 'ask': []}, 'subagents_enabled': False, 'auto_update': False, 'notify': 'never', 'read_config_from': {k: False for k in ['agents_standard','cursor','windsurf','claude','copilot','opencode','zed']}}
access = {'at': now(), 'auth': 'existing Devin first-party login confirmed', 'model': MODEL, 'cost_tier': 'Free', 'catalog_entries': len(entries), 'workspace_trust': 'respect=true; no override', 'tool_policy': config['permissions'], 'subagents': False, 'hooks': 'disabled for this process only', 'paid_fallback': False, 'limit_seconds': 480, 'authority': 'Owner 2026-10-08 explicitly asked to continue incomplete multimodal review; prior scoped approval and repository consultation rule apply; not an inherited one-time receipt'}
(OUT/'swe-access.json').write_text(json.dumps(access,ensure_ascii=False,indent=2)+'\n')
started = time.monotonic()
timed_out = False
with tempfile.TemporaryDirectory(prefix='pal-mm-swe-private-config-') as private:
    cfg = Path(private)/'config.json'
    cfg.write_text(json.dumps(config))
    cfg.chmod(0o600)
    cmd = [CLI,'--config',str(cfg),'--model',MODEL,'--permission-mode','auto','--sandbox','--respect-workspace-trust','true','--prompt-file',str(OUT/'swe-question.txt'),'-p']
    with (OUT/'swe-response.txt').open('wb') as stdout, (OUT/'swe-stderr.txt').open('wb') as stderr:
        process = subprocess.Popen(cmd,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,start_new_session=True)
        (OUT/'swe-start.json').write_text(json.dumps({'at':now(),'pid':process.pid,'prompt_sha256':hashlib.sha256((OUT/'swe-question.txt').read_bytes()).hexdigest()},indent=2)+'\n')
        while process.poll() is None:
            if time.monotonic()-started > 480 or (OUT/'swe-response.txt').stat().st_size > 65536:
                timed_out = True
                os.killpg(process.pid,signal.SIGTERM)
                try: process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    os.killpg(process.pid,signal.SIGKILL)
                    process.wait()
                break
            time.sleep(0.5)
answer=(OUT/'swe-response.txt').read_bytes()
complete=process.returncode == 0 and not timed_out and answer.rstrip().endswith(b'REVIEW_COMPLETE')
result={'at':now(),'elapsed_seconds':round(time.monotonic()-started,3),'exit_code':process.returncode,'bounded_stop':timed_out,'response_bytes':len(answer),'response_sha256':hashlib.sha256(answer).hexdigest(),'stderr_bytes':(OUT/'swe-stderr.txt').stat().st_size,'terminal_marker':answer.rstrip().endswith(b'REVIEW_COMPLETE'),'response_complete':complete,'attempts':1,'retry':False,'fallback':False,'private_config_removed':not Path(private).exists()}
(OUT/'swe-completion.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
print(json.dumps(result),flush=True)
