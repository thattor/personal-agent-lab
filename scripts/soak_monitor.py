#!/usr/bin/env python3
"""Owned loopback mock host + readonly, wall-clock soak measurements. No model calls."""
import argparse
import fcntl
import datetime
import hashlib
import json
import os
import re
import signal
import sqlite3
import subprocess
import sys
import time
import urllib.request
import uuid
from pathlib import Path
from urllib.parse import quote

REPO=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(REPO))
from pal.soak import EvidenceLog,baseline,canonical,candidate,check_snapshot,digest,readonly_snapshot,reconcile


def request_once(base,path,body=None):
    data=canonical(body).encode() if body is not None else None
    req=urllib.request.Request(base+path,data=data,headers={'Origin':base,'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=5) as response:
        return json.load(response)



def request(base,path,body=None):
    for attempt in range(2):
        try:
            return request_once(base,path,body)
        except OSError:
            if attempt:
                raise
            time.sleep(.2)


def snapshot(path):
    for attempt in range(2):
        try:
            return readonly_snapshot(path)
        except sqlite3.OperationalError as error:
            if attempt or 'locked' not in str(error).lower():
                raise
            time.sleep(.2)


def atomic_json(path,value):
    temporary=path.with_suffix(path.suffix+'.tmp')
    with temporary.open('w') as stream:
        stream.write(canonical(value)+'\n')
        stream.flush()
        os.fsync(stream.fileno())
    os.replace(temporary,path)


def attestation(run,log):
    path=run/'human-attestation.json'
    if not path.exists():
        return {}
    try:
        value=json.loads(path.read_text())
        if not isinstance(value,dict) or set(value)!={'source','session_ids'} or value['source']!='direct_user_attestation' or not isinstance(value.get('session_ids'),list) or not all(isinstance(s,str) and 0<len(s)<=100 for s in value['session_ids']):
            raise ValueError('invalid session list')
    except (OSError,ValueError):
        # Never turn a partial evidence-file write into a product-state failure or PASS.
        prior=next((r for r in reversed(log.records) if r['event']=='attestation_parse_error'),None)
        bad_digest=hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else 'absent'
        if not prior or prior['data'].get('digest')!=bad_digest:
            log.append('attestation_parse_error',{'status':'pending_valid_direct_user_attestation','digest':bad_digest})
        return {}
    fingerprint=digest(value)
    previous=next((r for r in reversed(log.records) if r['event']=='attestation'),None)
    if not previous or previous['data']['digest']!=fingerprint:
        log.append('attestation',{'digest':fingerprint,'value':value})
    return value

def boot_time():
    return subprocess.check_output(['/usr/sbin/sysctl','-n','kern.boottime'],text=True).strip()


def sleep_events(started_at):
    # Store only relevant power-event timestamps/labels, never general host history.
    text=subprocess.check_output(['/usr/bin/pmset','-g','log'],text=True,timeout=20)
    rows=[]
    for line in text.splitlines():
        match=re.match(r'^(\d{4}-\d\d-\d\d \d\d:\d\d:\d\d [+-]\d{4})\s+(Sleep|Wake|DarkWake)\s',line)
        if match:
            stamp=datetime.datetime.strptime(match.group(1),'%Y-%m-%d %H:%M:%S %z').timestamp()
            if stamp>=started_at:
                rows.append({'utc':stamp,'kind':match.group(2)})
    return rows


def start_app(run,port):
    stream=(run/'app.log').open('ab')
    app=subprocess.Popen([sys.executable,'-m','pal.server','--db',str(run/'pal.db'),'--port',str(port),'--mock-task-delay','10'],cwd=str(REPO),stdout=stream,stderr=stream)
    stream.close()
    base=f'http://127.0.0.1:{port}'
    for _ in range(100):
        if app.poll() is not None:
            raise RuntimeError('owned host failed startup; inspect app.log')
        try:
            health=request(base,'/api/health')
            if health['pid']!=app.pid:
                raise RuntimeError('port belongs to another process')
            return app,health
        except OSError:
            time.sleep(.1)
    app.terminate()
    app.wait(timeout=10)
    raise RuntimeError('host startup timed out')


def stop_app(app):
    if app and app.poll() is None:
        app.send_signal(signal.SIGTERM)
        app.wait(timeout=15)


def planned_restart(app,run,port,log,summary,attested):
    data=snapshot(run/'pal.db')
    active=next((a for a in data['attempts'] if a['status']=='running'),None)
    if not active:
        return app,None
    key=next((k for k,v in summary['ops'].items() if v['intent']=='draft' and v['goal_id']==active['goal_id'] and (k.split(':')[1:2] in [[s] for s in attested.get('session_ids',[])] and attested.get('source')=='direct_user_attestation' or log.records[0]['data']['mode']=='preflight')),None)
    if not key:
        return app,None
    record_id=summary['ops'][key]['record_id']
    text=next(r['content'] for r in data['records'] if r['id']==record_id)
    base=f'http://127.0.0.1:{port}'
    original=request(base,'/api/operation/'+quote(key,safe=''))['result']
    log.append('planned_restart_intent',{'key':key,'attempt_id':active['id'],'goal_id':active['goal_id'],'epoch':active['epoch'],'pid':app.pid})
    stop_app(app)
    stopped=snapshot(run/'pal.db')
    old=next(a for a in stopped['attempts'] if a['id']==active['id'])
    app,health=start_app(run,port)
    if old['status']!='running':
        log.append('planned_restart_race',{'reason':'Attempt ended before shutdown; not qualifying','key':key})
        return app,health
    replay=request(base,'/api/message',{'key':key,'text':text})
    if replay!=original:
        raise RuntimeError('restart replay ACK changed')
    recovered=snapshot(run/'pal.db')
    for _ in range(20):
        running=[a for a in recovered['attempts'] if a['goal_id']==active['goal_id'] and a['status']=='running' and a['id']!=active['id']]
        if len(running)==1:
            break
        time.sleep(.1)
        recovered=snapshot(run/'pal.db')
    if len(running)!=1:
        raise RuntimeError('restart did not resume a new Attempt')
    old=next(a for a in recovered['attempts'] if a['id']==active['id'])
    goal=next(g for g in recovered['goals'] if g['id']==active['goal_id'])
    if old['status']!='abandoned' or goal['epoch']<=active['epoch'] or len([g for g in recovered['goals'] if g['id']==goal['id']])!=1:
        raise RuntimeError('unfinished restart did not fence/resume same Goal')
    check_snapshot(recovered,summary['ops'])
    log.append('planned_restart_verified',{'key':key,'old_attempt':active['id'],'old_epoch':active['epoch'],'new_epoch':goal['epoch'],'same_goal':goal['id'],'new_attempt_id':running[0]['id'],'original_ack_digest':digest(original),'replayed_ack_digest':digest(replay),'old_status':old['status'],'new_host':health})
    return app,health


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--run',required=True,help='fresh run directory inside repository runtime/')
    parser.add_argument('--mode',choices=('soak','preflight'),default='soak')
    parser.add_argument('--port',type=int,default=58500)
    parser.add_argument('--preflight-seconds',type=int,default=25)
    args=parser.parse_args()
    run=Path(args.run).resolve()
    if REPO/'runtime' not in run.parents or run.exists():
        parser.error('run must be a fresh directory inside repository runtime/')
    profile={'provider':'mock','task_delay_seconds':10,'bind':'127.0.0.1','port':args.port}
    if args.mode=='soak':
        if subprocess.check_output(['git','status','--porcelain'],cwd=str(REPO)).strip():
            parser.error('soak requires a clean committed baseline')
        acceptance=(REPO/'ACCEPTANCE.md').read_text()
        for number in range(1,13):
            row=next((line for line in acceptance.splitlines() if line.startswith(f'| S0-{number:02d} |')),'')
            if not row.endswith('| PASS |'):
                parser.error('S0-01 through S0-12 must all be PASS')
    run.mkdir(parents=True)
    lock=(run/'monitor.lock').open('w')
    fcntl.flock(lock,fcntl.LOCK_EX|fcntl.LOCK_NB)
    app=None
    log=EvidenceLog(run/'measurements.jsonl')
    stopping=False
    def stop(*_):
        nonlocal stopping
        stopping=True
    signal.signal(signal.SIGTERM,stop)
    signal.signal(signal.SIGINT,stop)
    try:
        app,health=start_app(run,args.port)
        manifest={'mode':args.mode,'started_at':time.time(),'git_head':subprocess.check_output(['git','rev-parse','HEAD'],cwd=str(REPO),text=True).strip(),'baseline':baseline(REPO,profile),'boot_time':boot_time(),'initial_host':health}
        atomic_json(run/'manifest.json',manifest)
        log.append('baseline',{'manifest_hash':digest(manifest),'mode':args.mode})
        base=f'http://127.0.0.1:{args.port}'
        canary='sk-'+uuid.uuid4().hex+uuid.uuid4().hex
        request(base,'/api/message',{'key':'harness:canary','text':'Synthetic sanitation canary: '+canary})
        if args.mode=='preflight':
            request(base,'/api/message',{'key':'harness:restart','text':'Make a draft about synthetic monitoring, do not send.'})
        print(canonical({'url':base,'run':str(run),'mode':args.mode,'human_minimums':'20 turns, 3 attested sessions across 72h, 5 Goals, cancel, correction/reference-stop'}),flush=True)
        previous=None
        previous_snapshot=None
        expected={}
        checked_at=manifest['started_at']
        last_probe=0
        restart_done=False
        final_audit=False
        while not stopping:
            now=time.time()
            if args.mode=='preflight' and now-manifest['started_at']>=args.preflight_seconds:
                break
            if app.poll() is not None:
                raise RuntimeError('unexpected app exit')
            observed=snapshot(run/'pal.db')
            reconcile(previous_snapshot,observed)
            previous_snapshot=observed
            summary=check_snapshot(observed,expected)
            new_keys=sorted(set(summary['ops'])-set(expected))
            if new_keys:
                log.append('ingress_observed',{'keys':new_keys,'observed_after':checked_at})
                expected=summary['ops']
            checked_at=now
            human=attestation(run,log)
            if not restart_done:
                app,new_health=planned_restart(app,run,args.port,log,summary,human)
                if new_health:
                    health=new_health
                restart_done=any(r['event']=='planned_restart_verified' and (args.mode=='preflight' or r['data']['key'].split(':')[1:2] in [[s] for s in human.get('session_ids',[])]) for r in log.records)
            if now-last_probe>=300 or last_probe==0:
                current=request(base,'/api/health')
                if current['pid']!=app.pid or current['started_at']!=health['started_at'] or current['worker_error'] or not current['worker_alive']:
                    raise RuntimeError('host identity/worker failure')
                if baseline(REPO,profile)!=manifest['baseline'] or boot_time()!=manifest['boot_time']:
                    raise RuntimeError('baseline or boot changed; reset required')
                raw=time.clock_gettime(time.CLOCK_UPTIME_RAW)
                power=[]
                if previous:
                    wall=now-previous['utc']; awake=raw-previous['raw']
                    if awake>600:
                        raise RuntimeError('awake measurement cadence exceeded ten minutes')
                    if wall<0 or awake<0:
                        raise RuntimeError('clock moved backward')
                    if abs(wall-awake)>30 or wall>900:
                        power=sleep_events(previous['utc'])
                        if not any(r['kind']=='Sleep' for r in power) or not any(r['kind'] in ('Wake','DarkWake') for r in power):
                            raise RuntimeError('unexplained clock/gap discontinuity')
                for path in run.iterdir():
                    if path.is_file() and path.name!='monitor.lock' and canary.encode() in path.read_bytes():
                        raise RuntimeError('secret canary leak')
                observed=snapshot(run/'pal.db')
                reconcile(previous_snapshot,observed)
                previous_snapshot=observed
                summary=check_snapshot(observed,expected)
                row=log.append('measurement',{'summary':summary,'host':current,'boot_time':manifest['boot_time'],'sleep_wake':power,'canary_scan':'PASS','canary_hash':hashlib.sha256(canary.encode()).hexdigest()})
                previous={'utc':row['utc'],'raw':row['uptime_raw']}
                last_probe=now
                result=candidate(manifest,log.records,summary,human)
                if result['status']=='S0-13-CANDIDATE':
                    prior=next((r for r in reversed(log.records) if r['event']=='soak_candidate'),None)
                    if not prior or prior['data']['attestation_digest']!=digest(human):
                        row=log.append('soak_candidate',{'log_head':log.records[-1]['sha256'],'attestation':human,'attestation_digest':digest(human),'summary':summary,'verdict':result})
                atomic_json(run/'candidate.json',dict(result,log_seq=row['seq'],log_sha256=row['sha256']))
            if (run/'controller-complete.json').exists():
                human=attestation(run,log)
                audit=json.loads((run/'controller-complete.json').read_text())
                if args.mode=='soak' and audit.get('final_full_suite')=='PASS' and audit.get('acceptance_audit')=='PASS' and candidate(manifest,log.records,summary,human)['status']=='S0-13-CANDIDATE':
                    anchor=next(r for r in reversed(log.records) if r['event']=='soak_candidate')
                    if anchor['data']['attestation_digest']!=digest(human):
                        raise RuntimeError('final attestation changed after candidate anchor')
                    test_path=(REPO/audit['test_log']).resolve()
                    if REPO not in test_path.parents or hashlib.sha256(test_path.read_bytes()).hexdigest()!=audit['test_log_sha256']:
                        raise RuntimeError('final test evidence mismatch')
                    log.append('controller_audit_complete',dict(audit,candidate_sha256=anchor['sha256']))
                    final_audit=True
                    break
                raise RuntimeError('completion marker before qualifying final audit')
            # Fine polling only until the required unfinished restart; measurements stay 5 min.
            time.sleep(1 if not restart_done or args.mode=='preflight' else 5)
        final_summary=check_snapshot(snapshot(run/'pal.db'),expected)
        log.append('final_snapshot',{'summary':final_summary})
        log.append('monitor_stopped',{'mode':args.mode,'intentional':True})
        if args.mode=='soak' and not final_audit:
            log.append('reset_required',{'reason':'continuous monitor stopped before final controller audit'})
        print(canonical({'status':'PREFLIGHT_COMPLETE' if args.mode=='preflight' else ('FINAL_AUDIT_COMPLETE' if final_audit else 'STOPPED_RESET_REQUIRED'),'log_head':log.records[-1]['sha256']}),flush=True)
    except Exception as error:
        log.append('failure',{'type':type(error).__name__,'reason':str(error)})
        raise
    finally:
        try:
            stop_app(app)
        except Exception as error:
            log.append('failure',{'type':type(error).__name__,'reason':'owned host shutdown failed'})
        lock.close()


if __name__=='__main__':
    main()
