"""Supplemental runtime/metadata fixtures; imports do not qualify native execution."""
import hashlib
import os
import pwd
from pathlib import Path
import sys
import tempfile
from types import ModuleType
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'tests'))
from pal.contracts_v5 import dumps
from tools import native_devin_text_v5 as wrapper
import test_native_devin_text_v5 as fixtures

RUNTIME = Path(os.environ.get('PAL_CO_RUNTIME',
    str(Path(pwd.getpwuid(os.getuid()).pw_dir) / 'Documents/PAL/co-runtime/common-orchestration-v0.4.5')))
INSTALLED_RUNTIME = (RUNTIME / 'VERSION').is_file()


class RuntimeBoundaryTests(unittest.TestCase):
    def fixture(self):
        # Delegate only setup/cleanup; do not inherit or expose another TestCase
        # class to discovery. All native/capacity owners here remain doubles.
        case = fixtures.NativeDevinTextTests(methodName='runTest')
        case.setUp()
        self.addCleanup(case.doCleanups)
        return case

    @unittest.skipUnless(INSTALLED_RUNTIME, 'Optional installed CO runtime is absent')
    def test_installed_namespace_package_has_valid_runtime_origin(self):
        api = wrapper._load_runtime(RUNTIME)
        namespace = sys.modules['co_v4.adapters']
        self.assertIsNone(namespace.__file__)
        self.assertTrue(namespace.__path__)
        self.assertTrue(all(Path(p).resolve().is_relative_to(RUNTIME)
                            for p in namespace.__path__))
        self.assertEqual(api.DevinAdapter.__module__, 'co_v4.adapters.devin')
        self.assertEqual(api.DevinTextHost.__module__, 'co_v4.devin_host')
        # Loading public symbols is metadata-only: no API invocation/ledger SQL.

    @unittest.skipUnless(INSTALLED_RUNTIME, 'Optional installed CO runtime is absent')
    def test_foreign_or_mixed_namespace_origin_refuses(self):
        with tempfile.TemporaryDirectory() as foreign:
            for locations in ([foreign], [str(RUNTIME / 'co_v4/adapters'), foreign]):
                with self.subTest(locations=len(locations)):
                    namespace = ModuleType('co_v4.adapters')
                    namespace.__file__ = None
                    namespace.__path__ = locations
                    with patch.dict(sys.modules, {'co_v4.adapters': namespace}):
                        with self.assertRaises((RuntimeError, TypeError)):
                            wrapper._load_runtime(RUNTIME)

    def test_uid_owned_single_link_0644_credential_preflight_uses_metadata_only(self):
        case = self.fixture()
        case.credential.chmod(0o644)
        original_bytes, original_text = Path.read_bytes, Path.read_text
        def read_bytes(path):
            self.assertNotEqual(path, case.credential, 'Credential contents must not be read')
            return original_bytes(path)
        def read_text(path, *args, **kwargs):
            self.assertNotEqual(path, case.credential, 'Credential contents must not be read')
            return original_text(path, *args, **kwargs)
        with patch.object(Path, 'read_bytes', read_bytes), patch.object(Path, 'read_text', read_text), \
                patch.object(wrapper, '_metadata', side_effect=AssertionError('No auth/provider CLI in fixture')):
            self.assertEqual(case.provider.preflight(), case.owners.pin)
        self.assertEqual(case.credential.stat().st_mode & 0o777, 0o644)
        self.assertEqual(case.ledger.stat().st_mode & 0o777, 0o600)
        self.assertNotIn('execute', case.owners.log)
        self.assertNotIn('reserve', case.owners.log)
        self.assertFalse(case.entered)

    def test_public_lease_run_id_matches_canonical_fresh_workspace_cwd(self):
        case = self.fixture()
        result = case.invoke()
        request = case.owners.adapter.request
        workspace = Path(request.conditions.workspace)
        expected = 'task-cwd:' + hashlib.sha256(str(workspace.resolve(strict=True)).encode()).hexdigest()
        self.assertEqual(request.ref.run_id, expected)
        self.assertEqual(case.entered[0]['run_id'], expected)
        self.assertEqual(request.job.run_id, expected)
        self.assertTrue(workspace.is_relative_to(case.attempt_root))
        self.assertEqual(workspace.stat().st_mode & 0o777, 0o700)
        self.assertEqual(list(workspace.iterdir()), [])
        self.assertEqual(case.owners.log.count('execute'), 1)
        self.assertEqual(result.validate(request_sha256=hashlib.sha256(dumps(case.request).encode()).hexdigest(),
                         profile=case.profile)['evidence_kind'], 'fixture')


if __name__ == '__main__':
    unittest.main()
