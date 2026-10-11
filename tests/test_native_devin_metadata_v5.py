"""Real _fresh_pin with metadata-only fixtures; no CLI/provider/ledger proof."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
from types import SimpleNamespace, ModuleType
import unittest
from unittest.mock import patch

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from tools import native_devin_text_v5 as wrapper


class DevinMetadataTests(unittest.TestCase):
    def setUp(self):
        self.tmp=tempfile.TemporaryDirectory();self.addCleanup(self.tmp.cleanup)
        self.root=Path(self.tmp.name).resolve();self.runtime=self.root/'runtime'
        source=self.runtime/'co_v4'/'task'/'select.py';source.parent.mkdir(parents=True)
        source.write_text('# inert runtime fixture\n');(self.runtime/'VERSION').write_text('0.4.5\n')
        self.executable=self.root/'devin';self.executable.write_bytes(b'inert official executable fixture')
        self.state=self.root/'state';self.state.mkdir()
        self.selection={'route':'devin','model':'swe-2-high','measurement_digest':'sha256:'+'1'*64,
                        'fixture_context':'local only'}
        self.selected=[];self.commands=[]
        owner=self
        class Candidates:
            def __init__(self,state):owner.assertEqual(Path(state),owner.state)
            def selection(self,role,focus,policy=None):
                owner.selected.append((role,focus,copy.deepcopy(policy)))
                return copy.deepcopy(owner.selection)
        Candidates.__module__='fixture_devin_metadata_owner'
        module=ModuleType(Candidates.__module__);module.__file__=str(source)
        self.addCleanup(patch.stopall)
        patch.dict(sys.modules,{Candidates.__module__:module}).start()
        self.api=SimpleNamespace(NativeCandidates=Candidates,launch_environment=lambda:{'PATH':'fixture'})
        self.version=b'devin 3000.11.3 (9c803229faa4)\n'
        self.transport_version=b'devin 3000.11.3 (9c803229faa4)\n'
        self.auth=b'Authenticated: fixture\n'
        self.catalog={'families':[{'variants':[{'model_uid':'swe-2-high','cost_tier':'Free'}]}]}
        self.metadata_error=None
        def metadata(executable,args,env):
            owner.assertEqual(Path(executable),owner.executable);owner.assertEqual(env,{'PATH':'fixture'})
            owner.commands.append(tuple(args))
            if owner.metadata_error:raise owner.metadata_error
            return {('--version',):owner.version,('version',):owner.transport_version,('auth','status'):owner.auth,
                    ('models','list','--format','json'):json.dumps(owner.catalog).encode()}[tuple(args)]
        patch.object(wrapper,'_metadata',side_effect=metadata).start()
        self.which=patch.object(wrapper.shutil,'which',return_value=str(self.executable)).start()
        # Any accidental subprocess bypass is a fixture error, never a CLI call.
        patch.object(subprocess,'Popen',side_effect=AssertionError('metadata fixture must not spawn')).start()
    def fresh(self):return wrapper._fresh_pin(self.api,self.state,self.executable)
    def refuse(self):
        with self.assertRaises(Exception):self.fresh()
    def test_observed_official_build_version_accepts_and_hashes_exact_sources(self):
        pin=self.fresh()
        self.assertEqual((pin['route'],pin['model'],pin['version'],pin['cost_tier']),
                         ('devin','swe-2-high','3000.11.3','Free'))
        self.assertEqual(self.selected,[('implement','coding',{'mode':'fixed','targets':{'implement':{'route':'devin','model':'swe-2-high'}}})])
        self.assertEqual(self.commands,[('--version',),('version',),('auth','status'),('models','list','--format','json')])
        self.assertEqual(pin['selection_digest'],'sha256:'+hashlib.sha256(json.dumps(self.selection,sort_keys=True,separators=(',',':'),ensure_ascii=False,allow_nan=False).encode()).hexdigest())
        for relative,digest in pin['runtime_hashes'].items():
            self.assertEqual(digest,hashlib.sha256((self.runtime/relative).read_bytes()).hexdigest())
        self.assertEqual(pin['executable_sha256'],hashlib.sha256(self.executable.read_bytes()).hexdigest())
        self.assertEqual(pin['wrapper_sha256'],hashlib.sha256(Path(wrapper.__file__).read_bytes()).hexdigest())
        for raw in (b'devin 3000.11.3 (otherbuild)',b'devin 3000.11.2 (9c803229faa4)',b'3000.11.3'):
            with self.subTest(transport_version=raw):
                self.transport_version=raw;self.commands.clear();self.refuse()
                self.assertEqual(self.commands,[('--version',),('version',)])
    def test_wrong_version_prefix_substring_and_malformed_build_refuse(self):
        for version in (b'devin 3000.11.2 (9c803229faa4)',b'garbage devin 3000.11.3 (9c803229faa4)',
                        b'devin 3000.11.3 (9c803229faa4) garbage',b'devin 3000.11.3 ()',
                        b'devin 3000.11.3 (NOT_HEX)',b'devin 3000.11.3 (9c803229faa4',
                        b'devin 3000.11.3 9c803229faa4)',b'devin 13000.11.3'):
            with self.subTest(version=version):
                self.version=version;self.commands.clear();self.refuse()
                self.assertEqual(self.commands,[('--version',)])
    def test_auth_requires_positive_and_rejects_negative_even_with_positive(self):
        self.version=b'devin 3000.11.3'
        for auth in (b'',b'Unknown status',b'Unauthenticated',b'Not logged in',
                     b'Authenticated: fixture\nNot authenticated',b'Logged in\nunauthenticated'):
            with self.subTest(auth=auth):
                self.auth=auth;self.commands.clear();self.refuse()
                self.assertNotIn(('models','list','--format','json'),self.commands)
    def test_catalog_requires_unique_exact_swe_high_free(self):
        self.version=b'devin 3000.11.3'
        variants=({'model_uid':'swe-2-high','cost_tier':'Paid'},
                  {'model_uid':'swe-2-high','cost_tier':'free'},
                  {'model_uid':'other','cost_tier':'Free'})
        for items in ([],*([v] for v in variants),[{'model_uid':'swe-2-high','cost_tier':'Free'}]*2):
            with self.subTest(items=items):
                self.catalog={'families':[{'variants':items}]};self.refuse()
    def test_nonofficial_executable_refuses_before_metadata(self):
        self.which.return_value=None;self.refuse();self.assertEqual(self.commands,[])
        other=self.root/'other';other.write_text('fixture');self.which.return_value=str(other)
        self.refuse();self.assertEqual(self.commands,[])
    def test_metadata_command_failure_never_falls_back(self):
        self.metadata_error=subprocess.CalledProcessError(1,['devin','--version'])
        self.refuse();self.assertEqual(self.commands,[('--version',)])


if __name__=='__main__':unittest.main()
