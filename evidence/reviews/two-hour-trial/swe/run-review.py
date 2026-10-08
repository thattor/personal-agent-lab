from pathlib import Path
import datetime,hashlib,json,os,re,signal,subprocess,time
ROOT=Path('/private/tmp/personal-agent-lab-stable0-20261006')
OUT=Path(__file__).resolve().parent
assert not (OUT/'start.json').exists(), 'One call only'
a=subprocess.run(['devin','auth','status'],cwd=ROOT,capture_output=True,text=True,timeout=30)
m=subprocess.run(['devin','models','list'],cwd=ROOT,capture_output=True,text=True,timeout=30)
clean=lambda s:re.sub(r'\x1b\[[0-9;]*[A-Za-z]','',s)
logged='Logged in (via Devin).' in clean(a.stdout+a.stderr)
lines=[x for x in clean(m.stdout+m.stderr).splitlines() if re.match(r'^\s*swe-2-high\s',x)]
assert a.returncode==0 and logged and m.returncode==0 and len(lines)==1 and 'Free]' in lines[0]
access={'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'route':'installed_official_devin','authenticated':logged,'auth_command_exit':a.returncode,'model_command_exit':m.returncode,'standalone_free_model_line':lines,'model':'swe-2-high','paid_fallback':False,'trust_check':'respected; no override','scope':'one read-only supplied-source review; no code generation or repository writes','max_seconds':480,'retries':0}
(OUT/'access.json').write_text(json.dumps(access,indent=2)+'\n')
cmd=['devin','--model','swe-2-high','--permission-mode','auto','--sandbox','--print','--prompt-file',str(OUT/'question.txt')]
start=time.monotonic();timed_out=False
with (OUT/'swe-response.txt').open('wb') as stdout,(OUT/'swe-stderr.txt').open('wb') as stderr:
 p=subprocess.Popen(cmd,cwd=ROOT,stdin=subprocess.DEVNULL,stdout=stdout,stderr=stderr,start_new_session=True)
 (OUT/'start.json').write_text(json.dumps({'at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'pid':p.pid,'prompt_sha256':hashlib.sha256((OUT/'question.txt').read_bytes()).hexdigest()},indent=2)+'\n')
 try:p.wait(timeout=480)
 except subprocess.TimeoutExpired:
  timed_out=True;os.killpg(p.pid,signal.SIGTERM)
  try:p.wait(timeout=5)
  except subprocess.TimeoutExpired:os.killpg(p.pid,signal.SIGKILL);p.wait()
answer=(OUT/'swe-response.txt').read_bytes()
result={'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'elapsed_seconds':round(time.monotonic()-start,3),'exit_code':p.returncode,'timeout':timed_out,'response_bytes':len(answer),'stderr_bytes':(OUT/'swe-stderr.txt').stat().st_size,'response_sha256':hashlib.sha256(answer).hexdigest(),'response_complete':p.returncode==0 and not timed_out and b'REVIEW_COMPLETE' in answer,'attempts':1,'fallback':False,'retry':False}
(OUT/'completion.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result),flush=True)
