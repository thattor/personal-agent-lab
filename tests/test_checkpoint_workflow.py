"""Frozen controller-authored workflow probes; stdlib, inert children only."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import tempfile
import unittest

WORKFLOW = Path(os.environ.get('CHECKPOINT_WORKFLOW',
    Path(__file__).resolve().parents[1] / '.github/workflows/pal-checkpoints.yml'))
TEXT = WORKFLOW.read_text()


def steps():
    result = {}
    for chunk in TEXT.split('      - name: ')[1:]:
        name = chunk.splitlines()[0]
        script = []
        recording = False
        for line in chunk.splitlines()[1:]:
            if line == '        run: |':
                recording = True
                continue
            if recording and (line.startswith('          ') or not line.strip()):
                script.append(line[10:] if line.startswith('          ') else '')
            elif recording:
                break
            elif line.startswith('        run: '):
                script.append(line[len('        run: '):])
                break
        result[name] = (chunk, '\n'.join(script) + '\n')
    return result

STEPS = steps()
CHECKS = (
    ('Complete PAL regression suite', 'python -E -s -B -m unittest discover -s tests -v', 'unittest'),
    ('Exercise saved question and answer mock flow', 'python -E -s -B scripts/demo_ask_v5.py', 'ask'),
    ('Exercise revision replacement mock flow', 'python -E -s -B scripts/demo_change_v5.py', 'change'),
    ('Exercise saved result readback mock flow', 'python -E -s -B scripts/demo_readback_v5.py', 'readback'),
)
COLLECTOR = 'Bind all observed results to retained source'


class CheckpointWorkflowTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.env = dict(os.environ, RUNNER_TEMP=str(self.root), GITHUB_SHA='fixture-commit',
                        GITHUB_RUN_ID='fixture-run', GITHUB_RUN_ATTEMPT='1')

    def execute(self, script):
        return subprocess.run(['bash', '--noprofile', '--norc', '-eo', 'pipefail', '-c', script],
                              env=self.env, text=True, capture_output=True, timeout=15)

    def collect(self):
        self.assertIn(COLLECTOR, STEPS)
        result = self.execute(STEPS[COLLECTOR][1])
        path = self.root / 'pal-verification.json'
        self.assertTrue(path.is_file(), result.stderr)
        return result, json.loads(path.read_text())

    def complete_fixture(self):
        (self.root/'pal-source.tar.gz').write_bytes(b'inert-source-fixture')
        (self.root/'pal-environment.log').write_text('fixture-environment\n')
        for _, _, slug in CHECKS:
            (self.root/f'pal-{slug}.log').write_text(
                'test_a (fixture) ... ok\ntest_b (fixture) ... skipped \'optional fixture\'\n'
                '\nRan 2 tests in 0.001s\n\nOK (skipped=1)\n' if slug == 'unittest' else 'fixture success\n')
            for suffix in ('', '-log'):
                (self.root/f'pal-{slug}{suffix}.exit').write_text('0\n')

    def test_validation_steps_continue_but_require_fixture_guard(self):
        for name, _, _ in CHECKS:
            with self.subTest(name=name):
                condition = STEPS[name][0]
                self.assertIn('!cancelled()', condition)
                self.assertIn("steps.source.outcome == 'success'", condition)
                self.assertIn("steps.fixture_guard.outcome == 'success'", condition)

    def test_original_failure_and_exit_code_are_preserved_for_all_checks(self):
        for name, command, slug in CHECKS:
            with self.subTest(name=name):
                script = STEPS[name][1].replace(command, 'python -c "print(123); raise SystemExit(7)"')
                result = self.execute(script)
                self.assertEqual(result.returncode, 7, result.stderr)
                exit_path = self.root/f'pal-{slug}.exit'
                self.assertTrue(exit_path.is_file())
                self.assertEqual(exit_path.read_text(), '7\n')
                self.assertEqual((self.root/f'pal-{slug}-log.exit').read_text(), '0\n')
                self.assertIn('123', (self.root/f'pal-{slug}.log').read_text())

    def test_log_writer_failure_is_not_hidden_by_successful_test(self):
        binary = self.root/'bin'; binary.mkdir()
        tee = binary/'tee'; tee.write_text('#!/bin/sh\ncat >/dev/null\nexit 9\n'); tee.chmod(0o755)
        self.env['PATH'] = str(binary)+os.pathsep+self.env['PATH']
        name, command, slug = CHECKS[0]
        result = self.execute(STEPS[name][1].replace(command, 'python -c "print(123)"'))
        self.assertEqual(result.returncode, 9, result.stderr)
        self.assertTrue((self.root/f'pal-{slug}.exit').is_file())
        self.assertEqual((self.root/f'pal-{slug}.exit').read_text(), '0\n')
        self.assertEqual((self.root/f'pal-{slug}-log.exit').read_text(), '9\n')

    def test_success_binds_hashes_and_retains_skip_reason_without_acceptance(self):
        self.complete_fixture()
        result, receipt = self.collect()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(receipt['source_fixture_pass'])
        self.assertEqual(receipt['results']['unittest']['discovered'], 2)
        self.assertEqual(len(receipt['results']['unittest']['skip_reasons']), 1)
        self.assertEqual(receipt['independent_review'], 'NOT_RUN')
        self.assertEqual(receipt['product_acceptance'], 'NOT_MET')
        for name, digest in receipt['sha256'].items():
            self.assertEqual(digest, hashlib.sha256((self.root/name).read_bytes()).hexdigest())

    def test_failure_keeps_other_results_and_returns_nonzero(self):
        self.complete_fixture()
        (self.root/'pal-unittest.exit').write_text('7\n')
        (self.root/'pal-unittest.log').write_text('Ran 2 tests in 0.001s\nFAILED (failures=1)\n')
        result, receipt = self.collect()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(receipt['source_fixture_pass'])
        self.assertEqual(receipt['results']['unittest']['status'], 'FAIL')
        self.assertTrue(all(receipt['results'][n]['status']=='PASS' for n in ('ask','change','readback')))

    def test_missing_exit_is_unknown_not_pass(self):
        self.complete_fixture(); (self.root/'pal-ask.exit').unlink()
        result, receipt = self.collect()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(receipt['evidence_complete'])
        self.assertFalse(receipt['source_fixture_pass'])
        self.assertEqual(receipt['results']['ask']['status'], 'UNKNOWN')

    def test_zero_exit_with_incomplete_unittest_log_is_not_pass(self):
        self.complete_fixture(); (self.root/'pal-unittest.log').write_text('incomplete\n')
        result, receipt = self.collect()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(receipt['source_fixture_pass'])
        self.assertEqual(receipt['results']['unittest']['status'], 'UNKNOWN')

    def test_missing_source_is_not_pass(self):
        self.complete_fixture(); (self.root/'pal-source.tar.gz').unlink()
        result, receipt = self.collect()
        self.assertNotEqual(result.returncode, 0)
        self.assertFalse(receipt['source_fixture_pass'])
        self.assertIsNone(receipt['sha256']['pal-source.tar.gz'])

    def test_evidence_collection_and_upload_survive_failure(self):
        self.assertIn(COLLECTOR, STEPS)
        self.assertIn('if: always()', STEPS[COLLECTOR][0])
        upload = STEPS['Retain source and original test outcome, including failures'][0]
        self.assertIn('if: always()', upload)
        for item in ('pal-*.exit', 'pal-ask.log', 'pal-change.log', 'pal-readback.log', 'pal-verification.json'):
            self.assertIn(item, upload)


if __name__ == '__main__':
    unittest.main(verbosity=2)
