"""C083 local diagnostic fixtures: no native call or retrospective authority."""
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'tests'))
import test_native_devin_text_v5 as fixtures

FULL_VERSION='devin 3000.11.3 (9c803229faa4)'


class DevinDiagnosticsTests(unittest.TestCase):
    def fixture(self):
        case=fixtures.NativeDevinTextTests(methodName='runTest');case.setUp()
        self.addCleanup(case.doCleanups);return case
    def file(self,case,name):
        paths=list(case.attempt_root.rglob(name))
        self.assertEqual(len(paths),1,name+' original observation missing')
        self.assertEqual(paths[0].stat().st_mode & 0o777,0o600)
        data=json.loads(paths[0].read_text())
        if name=='diagnostic.json':
            self.assertEqual(set(data),{'attempt_ref','last_status','protocol_diagnostic','host_observation'})
        return data
    def unknown(self,case):
        case.unknown();self.assertEqual(case.owners.pool.executions,1)
        self.assertEqual(case.owners.log.count('pool_stop'),1)
    def failing_loop(self,case,*,diagnostic_error=False):
        parent=case.owners.api.PooledAdapter;counts={'events':0,'status':0,'diagnostic':0}
        class Pool(parent):
            def events(self,ref,after=None):
                counts['events']+=1
                if counts['events']>1:raise RuntimeError('PRIVATE_EVENT_CANARY')
                return ()
            def status(self,ref):
                counts['status']+=1
                if counts['status']>1:raise AssertionError('diagnosis must not pump status')
                case.owners.host.observation={'fixture':'PRIVATE_HOST_CANARY'}
                return fixtures.StatusEvent(ref,'cached-running',fixtures.State.RUNNING,'fixture:observed')
        case.owners.api.PooledAdapter=Pool
        parent_adapter=case.owners.api.DevinAdapter
        class Adapter(parent_adapter):
            def protocol_diagnostic(self,ref):
                counts['diagnostic']+=1
                if diagnostic_error:raise RuntimeError('PRIVATE_DIAGNOSTIC_ERROR_CANARY')
                return {'fixture':'PRIVATE_PROTOCOL_CANARY'}
        case.owners.api.DevinAdapter=Adapter
        return counts
    def test_original_host_config_uses_full_exact_transport_version(self):
        case=self.fixture();case.invoke()
        self.assertEqual(case.owners.host.config.expected_version,FULL_VERSION)
    def test_nonaccepted_execute_reply_retained_before_single_stop(self):
        case=self.fixture();parent=case.owners.api.PooledAdapter
        class Pool(parent):
            def execute(self,request):
                super().execute(request)
                return fixtures.OperationReply(request.ref,fixtures.OperationStatus.UNAVAILABLE,'fixture transport unavailable')
        case.owners.api.PooledAdapter=Pool;self.unknown(case)
        saved=self.file(case,'execute.json')
        self.assertEqual(saved,{'attempt_ref':dict(case.entered[0]),'status':'unavailable',
                              'reason':'fixture transport unavailable','never_started_evidence_ref':None})
        diagnostic=self.file(case,'diagnostic.json');self.assertIsNone(diagnostic['last_status'])
    def test_failure_saves_cached_status_without_pumping_and_original_observations(self):
        case=self.fixture();counts=self.failing_loop(case);self.unknown(case)
        saved=self.file(case,'diagnostic.json')
        self.assertEqual(saved['attempt_ref'],dict(case.entered[0]))
        self.assertEqual(saved['last_status'],{'attempt_ref':dict(case.entered[0]),'event_id':'cached-running',
                                             'state':'running','evidence_ref':'fixture:observed'})
        self.assertEqual(saved['protocol_diagnostic'],{'fixture':'PRIVATE_PROTOCOL_CANARY'})
        self.assertEqual(saved['host_observation'],{'fixture':'PRIVATE_HOST_CANARY'})
        self.assertEqual(counts,{'events':2,'status':1,'diagnostic':1})
    def test_protocol_diagnostic_exception_is_fixed_unavailable(self):
        case=self.fixture();counts=self.failing_loop(case,diagnostic_error=True);self.unknown(case)
        saved=self.file(case,'diagnostic.json')
        self.assertEqual(saved['protocol_diagnostic'],{'status':'unavailable'})
        self.assertNotIn('PRIVATE_DIAGNOSTIC_ERROR_CANARY',json.dumps(saved))
        self.assertEqual(counts['status'],1);self.assertEqual(counts['diagnostic'],1)
    def test_execute_journal_write_failure_still_stops_once_without_poll(self):
        case=self.fixture();original=case.module._write;events=[]
        parent=case.owners.api.PooledAdapter
        class Pool(parent):
            def events(self,*args,**kw):events.append('events');raise AssertionError('must not pump')
            def status(self,*args,**kw):events.append('status');raise AssertionError('must not pump')
        case.owners.api.PooledAdapter=Pool
        def write(path,data):
            if Path(path).name=='execute.json':raise OSError('PRIVATE_WRITE_CANARY')
            return original(path,data)
        with patch.object(case.module,'_write',side_effect=write):self.unknown(case)
        self.assertEqual(events,[])
    def test_diagnostic_write_failure_keeps_unknown_single_supported_cleanup(self):
        case=self.fixture();counts=self.failing_loop(case);original=case.module._write;attempted=[]
        def write(path,data):
            if Path(path).name=='diagnostic.json':
                attempted.append(1);raise OSError('PRIVATE_WRITE_CANARY')
            return original(path,data)
        with patch.object(case.module,'_write',side_effect=write):self.unknown(case)
        self.assertEqual(attempted,[1]);self.assertEqual(counts['status'],1)
        stop=self.file(case,'stop.json');self.assertEqual(stop['status'],'unconfirmed')


if __name__=='__main__':unittest.main()
