"""Read-only soak measurement and verifier. No model or canonical-write capability."""
import hashlib
import json
import platform
import re
import sqlite3
import time
from pathlib import Path
from urllib.parse import quote

HOURS_72 = 72 * 60 * 60


def canonical(value):
    return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=False)


def digest(value):
    return hashlib.sha256(canonical(value).encode()).hexdigest()


def validate_chain(records):
    previous='0'*64
    for index,row in enumerate(records):
        body={key:value for key,value in row.items() if key!='sha256'}
        if row.get('seq')!=index+1 or row.get('previous')!=previous or digest(body)!=row.get('sha256'):
            raise RuntimeError('soak evidence chain invalid')
        previous=row['sha256']


class EvidenceLog:
    def __init__(self,path):
        self.path=Path(path)
        self.records=self.read(self.path)

    @staticmethod
    def read(path):
        if not Path(path).exists():
            return []
        records=[]
        previous='0'*64
        for line in Path(path).read_text().splitlines():
            row=json.loads(line)
            checksum=row.pop('sha256')
            if row.get('seq')!=len(records)+1 or row.get('previous')!=previous or digest(row)!=checksum:
                raise RuntimeError('soak evidence chain invalid')
            row['sha256']=checksum
            records.append(row)
            previous=checksum
        return records

    def append(self,event,data):
        import os
        row={'seq':len(self.records)+1,'previous':self.records[-1]['sha256'] if self.records else '0'*64,'utc':time.time(),'uptime_raw':time.clock_gettime(time.CLOCK_UPTIME_RAW),'event':event,'data':data}
        row['sha256']=digest(row)
        self.path.parent.mkdir(parents=True,exist_ok=True)
        with self.path.open('a') as stream:
            stream.write(canonical(row)+'\n')
            stream.flush()
            os.fsync(stream.fileno())
        self.records.append(row)
        return row


def baseline(repo,profile):
    repo=Path(repo)
    files=[p for p in (repo/'pal').rglob('*') if p.is_file() and p.suffix in ('.py','.js','.css','.html')]
    files.append(repo/'scripts'/'soak_monitor.py')
    return {'python':platform.python_version(),'profile':profile,'schema_version':1,'sqlite':sqlite3.sqlite_version,'files':{str(p.relative_to(repo)):hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(files)}}


def readonly_snapshot(path):
    path=Path(path).resolve()
    db=sqlite3.connect('file:'+quote(str(path),safe='/')+'?mode=ro',uri=True)
    db.row_factory=sqlite3.Row
    try:
        db.execute('PRAGMA query_only=ON')
        db.execute('BEGIN')
        integrity=db.execute('PRAGMA quick_check').fetchone()[0]
        if integrity!='ok':
            raise RuntimeError('canonical integrity check failed')
        names=('records','notes','goals','attempts','receipts','outcomes','acceptances','revisions','events','dedupe','approvals','rejections')
        result={name:[dict(r) for r in db.execute('SELECT * FROM '+name)] for name in names}
        blobs={r['id']:bytes(r['body']) for r in db.execute('SELECT id,body FROM artifacts')}
        result['db_inode']=path.stat().st_ino
        result['blob_checks']={k:{'hash':hashlib.sha256(v).hexdigest(),'size':len(v),'utf8':valid_utf8(v)} for k,v in blobs.items()}
        return result
    finally:
        db.close()


def valid_utf8(body):
    try:
        text=body.decode('utf-8',errors='strict')
        return bool(text.strip()) and '\x00' not in text and not text.startswith('\ufeff')
    except UnicodeError:
        return False


def check_snapshot(data,expected=None):
    records={r['id']:r for r in data['records']}
    goals={g['id']:g for g in data['goals']}
    attempts={a['id']:a for a in data['attempts']}
    criteria={a['id']:json.loads(a['criteria']) for a in data['acceptances']}
    receipts={r['id']:r for r in data['receipts']}
    if len([a for a in attempts.values() if a['status']=='running'])>1:
        raise RuntimeError('multiple active execution slots')
    for a in attempts.values():
        g=goals[a['goal_id']]
        if a['status']=='running' and (g['state']!='running' or a['revision']!=g['revision'] or a['epoch']!=g['epoch']):
            raise RuntimeError('stale active Attempt')
    for receipt in receipts.values():
        attempt=attempts[receipt['attempt_id']]
        blob=data['blob_checks'][receipt['artifact_id']]
        cap=criteria[attempt['acceptance_id']]['max_bytes']
        if not blob['utf8'] or blob['hash']!=receipt['hash'] or blob['size']!=receipt['size'] or blob['size']>cap or receipt['epoch']!=attempt['epoch'] or receipt['revision']!=attempt['revision']:
            raise RuntimeError('invalid host evidence binding')
    completion_events=[e['goal_id'] for e in data['events'] if e['kind']=='goal.completed']
    if len(completion_events)!=len(set(completion_events)):
        raise RuntimeError('duplicate completion event')
    completed=set()
    for outcome in data['outcomes']:
        if outcome['check_status']=='pass':
            attempt=attempts[outcome['attempt_id']]
            goal=goals[attempt['goal_id']]
            if attempt['status']!='pass' or goal['state']!='completed' or attempt['revision']!=goal['revision'] or attempt['epoch']!=goal['epoch'] or outcome['receipt_id'] not in receipts or receipts[outcome['receipt_id']]['attempt_id']!=attempt['id'] or goal['id'] in completed:
                raise RuntimeError('stale or duplicate completion')
            completed.add(goal['id'])
    source_events=[r['source_event_id'] for r in records.values() if r['source_event_id']]
    if len(source_events)!=len(set(source_events)):
        raise RuntimeError('duplicate local report')
    ops={}
    for operation in data['dedupe']:
        if operation['kind']!='ingress':
            continue
        value=json.loads(operation['result'])
        goal=value.get('goal')
        if value['record_id'] not in records or (goal and goal['id'] not in goals):
            raise RuntimeError('lost accepted ingress')
        ops[operation['key']]={'record_id':value['record_id'],'goal_id':goal['id'] if goal else None,'intent':value['intent'],'action':value.get('action')}
    passing={o['attempt_id'] for o in data['outcomes'] if o['check_status']=='pass'}
    if {a['id'] for a in attempts.values() if a['status']=='pass'}!=passing or {g['id'] for g in goals.values() if g['state']=='completed'}!=completed:
        raise RuntimeError('missing reverse completion evidence')
    if expected and any(key not in ops or ops[key]!=value for key,value in expected.items()):
        raise RuntimeError('lost or changed previously observed accepted operation')
    return {'ops':ops,'goal_states':{g['id']:g['state'] for g in goals.values()},'attempt_statuses':{a['id']:a['status'] for a in attempts.values()},'counts':{name:len(data[name]) for name in ('records','goals','attempts','receipts','outcomes','events')},'reports':len(source_events)}



def reconcile(previous,current):
    if previous is None:
        return
    if previous['db_inode']!=current['db_inode']:
        raise RuntimeError('canonical database replaced')
    for name in ('records','notes','goals','attempts','receipts','outcomes','acceptances','revisions','events','dedupe','approvals','rejections'):
        def identity(row):
            if name=='rejections':
                return row['seq']
            if name=='revisions':
                return (row['goal_id'],row['revision'])
            return row.get('id',row.get('key',row.get('attempt_id',row.get('seq'))))
        current_rows={identity(row):row for row in current[name]}
        for old in previous[name]:
            new=current_rows.get(identity(old))
            if new is None:
                raise RuntimeError('previous canonical row lost: '+name)
            mutable={'records':{'usable'},'notes':{'usable'},'events':{'delivered'},'goals':{'state','revision','acceptance_id','epoch','budget','total_claims','reason','question_id','ambiguity'},'attempts':{'status','error','external_intent'},'approvals':{'valid','consumed'}}.get(name,set())
            if {k:v for k,v in old.items() if k not in mutable}!={k:v for k,v in new.items() if k not in mutable}:
                raise RuntimeError('immutable canonical row changed: '+name)
            if name in ('records','notes') and new['usable']>old['usable'] or name=='events' and new['delivered']<old['delivered']:
                raise RuntimeError('reference/outbox flag reversed')
            if name=='goals' and (new['epoch']<old['epoch'] or new['revision']<old['revision'] or new['total_claims']<old['total_claims'] or old['state'] in ('completed','cancelled') and new['state']!=old['state']):
                raise RuntimeError('canonical Goal history reversed')
            if name=='attempts' and old['status']!='running' and new!=old:
                raise RuntimeError('terminal Attempt changed')
    if any(k not in current['blob_checks'] or current['blob_checks'][k]!=value for k,value in previous['blob_checks'].items()):
        raise RuntimeError('previous artifact changed or lost')


def cadence(manifest,log):
    measurements=[row for row in log if row['event']=='measurement']
    if not measurements or measurements[0]['utc']-manifest['started_at']>600:
        return False
    for previous,current in zip(measurements,measurements[1:]):
        wall=current['utc']-previous['utc']
        awake=current['uptime_raw']-previous['uptime_raw']
        if awake<0 or awake>600 or wall<0:
            return False
        if wall>600 or abs(wall-awake)>30:
            events=current['data'].get('sleep_wake',[])
            if not any(r['kind']=='Sleep' for r in events) or not any(r['kind'] in ('Wake','DarkWake') for r in events):
                return False
    return True

def human_counts(ops,attestation,observed_at=None):
    # Namespace is corroboration, not an assertion of humanity. Require direct user attestation.
    sessions=set(attestation.get('session_ids',[])) if attestation.get('source')=='direct_user_attestation' else set()
    turns=[]
    for key,value in ops.items():
        match=re.fullmatch(r'ui:([^:]+):(\d{13}):([^:]+)',key)
        if match and match.group(1) in sessions:
            timestamp=(observed_at or {}).get(key)
            if timestamp is not None:
                turns.append((match.group(1),timestamp,value))
    observed={s for s,_,_ in turns}
    first_times=[stamp['before'] for _,stamp,_ in turns]
    last_times=[stamp['after'] for _,stamp,_ in turns]
    return {'sessions':sorted(observed),'turns':len(turns),'goals':len({v['goal_id'] for _,_,v in turns if v['intent']=='draft' and v['goal_id']}),'cancel':sum(v['action']=='cancel' for _,_,v in turns),'correct_or_forget':sum(v['action'] in ('correct','forget') for _,_,v in turns),'first_at':min(first_times) if first_times else None,'last_at':max(last_times) if last_times else None}


def candidate(manifest,log,summary,attestation,now=None):
    now=time.time() if now is None else now
    if any(r['utc']>now+5 for r in log):
        raise RuntimeError('future evidence clock')
    if not log or log[0]['event']!='baseline' or log[0]['data']['manifest_hash']!=digest(manifest):
        raise RuntimeError('manifest/log baseline mismatch')
    if any(r['event'] in ('failure','reset_required') for r in log):
        return {'status':'FAIL','reason':'soak finding or reset recorded'}
    if manifest['mode']!='soak':
        return {'status':'PREFLIGHT_ONLY','can_satisfy_S0_13':False}
    observed_at={}
    for row in log:
        if row['event']=='ingress_observed':
            for key in row['data']['keys']:
                observed_at.setdefault(key,{'before':row['utc'],'after':row['data'].get('observed_after',row['utc'])})
    counts=human_counts(summary['ops'],attestation,observed_at)
    elapsed=now-manifest['started_at']
    span=(counts['last_at']-counts['first_at']) if counts['first_at'] is not None else 0
    restart=any(r['event']=='planned_restart_verified' and r['data'].get('key','').split(':')[1:2] in [[s] for s in counts['sessions']] for r in log)
    enough=counts['turns']>=20 and len(counts['sessions'])>=3 and counts['goals']>=5 and counts['cancel']>=1 and counts['correct_or_forget']>=1
    result={'status':'PENDING_HUMAN_OR_TIME','elapsed_seconds':elapsed,'required_seconds':HOURS_72,'human_session_span_seconds':span,'human':counts,'planned_restart_verified':restart,'manual_canonical_repairs':0,'live_provider_reliability_claim':False}
    if elapsed>=HOURS_72 and span>=HOURS_72 and enough and restart and cadence(manifest,log) and next(r for r in reversed(log) if r['event']=='measurement')['utc']>=now-600:
        result['status']='S0-13-CANDIDATE'
    return result


def historical_candidate(manifest,log):
    validate_chain(log)
    if any(row['event'] in ('failure','reset_required') for row in log):
        return {'status':'FAIL'}
    for index in range(len(log)-1,-1,-1):
        row=log[index]
        if row['event']!='soak_candidate':
            continue
        data=row['data']
        if data['log_head']!=row['previous'] or data['attestation_digest']!=digest(data['attestation']):
            raise RuntimeError('candidate anchor mismatch')
        result=candidate(manifest,log[:index],data['summary'],data['attestation'],row['utc'])
        if result['status']!='S0-13-CANDIDATE':
            raise RuntimeError('anchored candidate did not qualify')
        result['candidate_sha256']=row['sha256']
        audits=[r for r in log[index+1:] if r['event']=='controller_audit_complete' and r['data'].get('candidate_sha256')==row['sha256']]
        if audits:
            result['status']='FINAL_AUDIT_COMPLETE'
        return result
    return {'status':'PENDING_HUMAN_OR_TIME'}
