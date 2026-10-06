import copy
import importlib.util
import json
import tempfile
import time
import unittest
from pathlib import Path
from pal.soak import EvidenceLog,HOURS_72,candidate,check_snapshot,digest,human_counts,readonly_snapshot,reconcile,historical_candidate
from pal.store import Store


class SoakTests(unittest.TestCase):
    def setUp(self):
        self.temp=tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path=Path(self.temp.name)/'pal.db'
        self.store=Store(self.path)

    def test_readonly_probe_binds_ack_and_actual_host_bytes(self):
        ack=self.store.ingress('harness:test','Make a draft','draft')
        attempt=self.store.claim([])
        receipt=self.store.write_draft(attempt['id'],'Actual draft')
        self.store.complete(attempt['id'],receipt['id'])
        self.store.deliver()
        snapshot=readonly_snapshot(self.path)
        summary=check_snapshot(snapshot)
        self.assertEqual(summary['ops']['harness:test']['goal_id'],ack['goal']['id'])
        self.assertEqual(self.store.inspect()['goals'][0]['state'],'completed')
        forged=copy.deepcopy(snapshot)
        forged['blob_checks'][receipt['artifact_id']]['hash']='0'*64
        with self.assertRaisesRegex(RuntimeError,'evidence'):
            check_snapshot(forged)
        with self.assertRaisesRegex(RuntimeError,'lost or changed'):
            check_snapshot(snapshot,{'missing':{}})
        stale=copy.deepcopy(snapshot)
        stale['goals'][0]['epoch']+=1
        with self.assertRaisesRegex(RuntimeError,'stale'):
            check_snapshot(stale)

    def test_hash_chain_detects_edit_and_reorder(self):
        path=Path(self.temp.name)/'log.jsonl'
        log=EvidenceLog(path)
        log.append('baseline',{'x':1})
        log.append('measurement',{'x':2})
        self.assertEqual(len(EvidenceLog.read(path)),2)
        original=path.read_text()
        path.write_text(original.replace('"x":2','"x":3'))
        with self.assertRaisesRegex(RuntimeError,'chain invalid'):
            EvidenceLog.read(path)
        path.write_text('\n'.join(reversed(original.splitlines()))+'\n')
        with self.assertRaisesRegex(RuntimeError,'chain invalid'):
            EvidenceLog.read(path)

    def gate(self,mode='soak'):
        start=1000000
        manifest={'mode':mode,'started_at':start}
        ops={}; log=[{'utc':start,'event':'baseline','data':{'manifest_hash':digest(manifest)}}]
        for i in range(20):
            session=['a','b','c'][min(i//7,2)]
            # A forged client clock cannot establish host-observed human session span.
            key=f'ui:{session}:9999999999999:{i}'
            ops[key]={'intent':'draft' if i<5 else 'control','goal_id':str(i) if i<5 else None,'action':'cancel' if i==5 else 'correct' if i==6 else None}
            log.append({'utc':start+HOURS_72*i/19,'event':'ingress_observed','data':{'keys':[key]}})
        log.append({'utc':start+HOURS_72,'event':'planned_restart_verified','data':{'key':next(iter(ops))}})
        log.extend({'utc':start+offset,'uptime_raw':offset,'event':'measurement','data':{}} for offset in range(0,HOURS_72+1,300))
        log=[log[0]]+sorted(log[1:],key=lambda r:r['utc'])
        return manifest,log,{'ops':ops},{'source':'direct_user_attestation','session_ids':['a','b','c']},start+HOURS_72

    def test_no_fixture_unattested_or_client_clock_pass(self):
        manifest,log,summary,attestation,now=self.gate()
        self.assertEqual(candidate(manifest,log,summary,attestation,now)['status'],'S0-13-CANDIDATE')
        self.assertEqual(candidate(manifest,log,summary,{},now)['human']['turns'],0)
        self.assertEqual(human_counts(summary['ops'],attestation)['turns'],0)
        short=copy.deepcopy(log)
        for row in short[1:]:
            row['utc']=now
        self.assertEqual(candidate(manifest,short,summary,attestation,now)['status'],'PENDING_HUMAN_OR_TIME')
        fixture={'ops':{'harness:'+k:v for k,v in summary['ops'].items()}}
        self.assertEqual(candidate(manifest,log,fixture,attestation,now)['human']['turns'],0)

    def test_real_duration_clean_run_restart_and_fresh_probe_required(self):
        manifest,log,summary,attestation,now=self.gate()
        later_start=dict(manifest,started_at=manifest['started_at']+1)
        later_log=copy.deepcopy(log)
        later_log[0]['data']['manifest_hash']=digest(later_start)
        self.assertEqual(candidate(later_start,later_log,summary,attestation,now)['status'],'PENDING_HUMAN_OR_TIME')
        with self.assertRaisesRegex(RuntimeError,'future evidence'):
            candidate(manifest,log,summary,attestation,now-10)
        self.assertEqual(candidate(manifest,log,summary,attestation,now+601)['status'],'PENDING_HUMAN_OR_TIME')
        no_restart=[r for r in log if r['event']!='planned_restart_verified']
        self.assertEqual(candidate(manifest,no_restart,summary,attestation,now)['status'],'PENDING_HUMAN_OR_TIME')
        log.append({'utc':now,'event':'failure','data':{}})
        self.assertEqual(candidate(manifest,log,summary,attestation,now)['status'],'FAIL')
        manifest,log,summary,attestation,now=self.gate('preflight')
        self.assertEqual(candidate(manifest,log,summary,attestation,now)['status'],'PREFLIGHT_ONLY')
        manifest['started_at']-=1
        with self.assertRaisesRegex(RuntimeError,'baseline mismatch'):
            candidate(manifest,log,summary,attestation,now)

    def test_missing_reverse_evidence_and_immutable_row_history(self):
        ack=self.store.ingress('draft','Make a draft','draft')
        before=readonly_snapshot(self.path)
        attempt=self.store.claim([])
        receipt=self.store.write_draft(attempt['id'],'Draft')
        self.store.complete(attempt['id'],receipt['id'])
        self.store.deliver()
        after=readonly_snapshot(self.path)
        reconcile(before,after)
        missing=copy.deepcopy(after)
        missing['outcomes']=[]
        with self.assertRaisesRegex(RuntimeError,'reverse'):
            check_snapshot(missing)
        changed=copy.deepcopy(after)
        changed['records'][0]['content']='rewritten outside host'
        with self.assertRaisesRegex(RuntimeError,'immutable'):
            reconcile(before,changed)
        replaced=copy.deepcopy(after)
        replaced['db_inode']+=1
        with self.assertRaisesRegex(RuntimeError,'replaced'):
            reconcile(after,replaced)
        changed=copy.deepcopy(after)
        changed['attempts'][0]['status']='abandoned'
        with self.assertRaisesRegex(RuntimeError,'terminal'):
            reconcile(after,changed)

    def test_cadence_gap_cannot_be_hidden_by_recent_ingress(self):
        manifest,log,summary,attestation,now=self.gate()
        log=[r for r in log if r['event']!='measurement' or r['utc'] not in (manifest['started_at']+300,manifest['started_at']+600)]
        self.assertEqual(candidate(manifest,log,summary,attestation,now)['status'],'PENDING_HUMAN_OR_TIME')

    def test_historic_candidate_is_anchored_and_rederived(self):
        manifest,rows,summary,attestation,now=self.gate()
        chain=[]; previous='0'*64
        for row in rows:
            row=dict(row,seq=len(chain)+1,previous=previous)
            row['sha256']=digest(row)
            chain.append(row); previous=row['sha256']
        anchor={'seq':len(chain)+1,'previous':previous,'utc':now,'event':'soak_candidate','data':{'log_head':previous,'summary':summary,'attestation':attestation,'attestation_digest':digest(attestation)}}
        anchor['sha256']=digest(anchor)
        chain.append(anchor)
        audit={'seq':len(chain)+1,'previous':anchor['sha256'],'utc':now+1,'event':'controller_audit_complete','data':{'candidate_sha256':anchor['sha256']}}
        audit['sha256']=digest(audit)
        chain.append(audit)
        self.assertEqual(historical_candidate(manifest,chain)['status'],'FINAL_AUDIT_COMPLETE')
        chain[-2]['data']['attestation']['session_ids']=[]
        with self.assertRaisesRegex(RuntimeError,'chain|anchor'):
            historical_candidate(manifest,chain)

    def test_monitor_attestation_partial_save_is_pending_and_secret_fields_rejected(self):
        spec=importlib.util.spec_from_file_location('pal_soak_monitor',Path(__file__).resolve().parents[1]/'scripts'/'soak_monitor.py')
        monitor=importlib.util.module_from_spec(spec)
        spec.loader.exec_module(monitor)
        run=Path(self.temp.name)
        log=EvidenceLog(run/'events.jsonl')
        path=run/'human-attestation.json'
        path.write_text('{')
        self.assertEqual(monitor.attestation(run,log),{})
        self.assertEqual(log.records[-1]['event'],'attestation_parse_error')
        length=len(log.records)
        self.assertEqual(monitor.attestation(run,log),{})
        self.assertEqual(len(log.records),length)
        value={'source':'direct_user_attestation','session_ids':['synthetic-unit-session']}
        monitor.atomic_json(path,value)
        self.assertEqual(monitor.attestation(run,log),value)
        self.assertEqual(log.records[-1]['data']['digest'],digest(value))
        monitor.atomic_json(path,dict(value,password='arbitrary-extra-field'))
        self.assertEqual(monitor.attestation(run,log),{})
        self.assertNotIn('arbitrary-extra-field',json.dumps(log.records))
