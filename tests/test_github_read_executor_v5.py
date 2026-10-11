"""Tests for pal.github_read_executor_v5 (PAL v5 EXE-02 leaf).

Fake-gh and inert-child tests only: every child is a ``sys.executable -c``
program spawned through an injected Popen factory (or one executable test
script for the default-factory path). No real gh, network, credential or
provider is ever invoked.
"""

import ast
import base64
import json
import os
import pathlib
import signal
import subprocess
import sys
import tempfile
import time
import unittest

import pal.bounded_payload_v5 as bounded_module
import pal.github_file_payload_v5 as file_module
import pal.github_read_executor_v5 as executor
import pal.github_issue_payload_v5 as issue_module
import pal.github_read_request_v5 as request_module
from pal.github_read_executor_v5 import (
    ReadOutcome,
    SubprocessRunner,
    read,
)

REPO = "thattor/personal-agent-lab"
SHA = "a" * 40
BLOB_SHA = "b" * 40
FILE_CAP = "github.file.read"
ISSUE_CAP = "github.issue.read"
FIXED_NOW = "2026-10-11T00:00:00Z"
SENTINEL = "S3NT1NEL-do-not-echo"
SLEEP_CHILD = "import time;time.sleep(60)"
CONFIG_DIR = tempfile.gettempdir()
EXPECTED_ENV = {
    "GH_CONFIG_DIR": CONFIG_DIR,
    "GH_PROMPT_DISABLED": "1",
    "GH_NO_UPDATE_NOTIFIER": "1",
    "NO_COLOR": "1",
    "LC_ALL": "C",
}


def issue_args(number=42):
    return {"repository": REPO, "number": number}


def file_args(path="README.md", ref=SHA):
    return {"repository": REPO, "path": path, "ref": ref}


def file_payload(data=b"hello pal\n", sha=BLOB_SHA):
    return json.dumps(
        {
            "type": "file",
            "encoding": "base64",
            "size": len(data),
            "sha": sha,
            "content": base64.b64encode(data).decode("ascii"),
            "name": "README.md",
            "path": "README.md",
        }
    ).encode("utf-8")


def issue_payload(number=42, **over):
    obj = {
        "number": number,
        "title": "t",
        "state": "open",
        "body": "text",
        "updated_at": "2026-10-10T01:02:03Z",
        "id": 7,
        "url": "https://api.example.invalid/x?token=" + SENTINEL,
        "user": {"login": "u"},
    }
    obj.update(over)
    return json.dumps(obj).encode("utf-8")


def emit_script(payload):
    return "import sys;sys.stdout.buffer.write(%r)" % payload


def make_popen(script):
    """Popen factory that runs ``script`` as fake gh via sys.executable."""

    def factory(argv, **kwargs):
        return subprocess.Popen(
            [sys.executable, "-c", script, *argv[1:]], **kwargs
        )

    return factory


class RecordingPopen:
    """Popen factory recording (argv, kwargs) and the spawned children."""

    def __init__(self, script):
        self.script = script
        self.calls = []
        self.children = []

    def __call__(self, argv, **kwargs):
        self.calls.append((list(argv), dict(kwargs)))
        child = subprocess.Popen(
            [sys.executable, "-c", self.script, *argv[1:]], **kwargs
        )
        self.children.append(child)
        return child


class UnreapableChild:
    """Wraps a real Popen but never confirms death: ``poll`` claims the
    child is still running and ``wait`` always times out. Group signals
    still reach the real process; the test reaps it afterwards."""

    def __init__(self, real):
        self._real = real

    @property
    def pid(self):
        return self._real.pid

    @property
    def returncode(self):
        return self._real.returncode

    @property
    def stdin(self):
        return self._real.stdin

    @property
    def stdout(self):
        return self._real.stdout

    @property
    def stderr(self):
        return self._real.stderr

    def poll(self):
        return None

    def wait(self, timeout=None):
        raise subprocess.TimeoutExpired(self._real.pid, timeout or 0)


class InterruptibleChild:
    """Wraps a real Popen; the first ``wait`` raises KeyboardInterrupt
    (simulating a cancellation landing mid-wait) and later calls delegate
    to the real process. Used to prove a propagated ``BaseException``
    still gets bounded owned termination."""

    def __init__(self, real):
        self._real = real
        self._interrupted = False

    @property
    def pid(self):
        return self._real.pid

    @property
    def returncode(self):
        return self._real.returncode

    @property
    def stdin(self):
        return self._real.stdin

    @property
    def stdout(self):
        return self._real.stdout

    @property
    def stderr(self):
        return self._real.stderr

    def poll(self):
        return self._real.poll()

    def wait(self, timeout=None):
        if not self._interrupted:
            self._interrupted = True
            raise KeyboardInterrupt
        return self._real.wait(timeout=timeout)


SIGTERM_RESISTANT_GRANDCHILD = (
    "import signal,time;"
    "signal.signal(signal.SIGTERM,signal.SIG_IGN);"
    "time.sleep(60)"
)


def grandchild_script(pidfile, tail):
    """Child script: spawn a SIGTERM-ignoring grandchild in the same
    process group with DEVNULL stdio, record its pid, then run ``tail``."""
    return (
        "import subprocess,sys;"
        "g=subprocess.Popen([sys.executable,'-c',%r],"
        "stdin=subprocess.DEVNULL,stdout=subprocess.DEVNULL,"
        "stderr=subprocess.DEVNULL);"
        "open(%r,'w').write(str(g.pid));" % (SIGTERM_RESISTANT_GRANDCHILD, pidfile)
        + tail
    )


def runner_for(
    script=None, popen=None, clock=lambda: FIXED_NOW, config_dir=CONFIG_DIR
):
    if popen is None:
        popen = make_popen(script or emit_script(issue_payload()))
    return SubprocessRunner(
        gh_path=sys.executable,
        config_dir=config_dir,
        clock=clock,
        popen=popen,
    )


def do_read(runner, capability=ISSUE_CAP, arguments=None, **kw):
    args = {
        "operation_id": "op-1",
        "capability": capability,
        "arguments": issue_args() if arguments is None else arguments,
        "timeout_seconds": 5,
        "max_bytes": 65536,
        "runner": runner,
    }
    args.update(kw)
    return read(**args)


def assert_failed(test, outcome):
    test.assertIs(type(outcome), ReadOutcome)
    test.assertEqual(outcome.status, "failed")
    test.assertIsNone(outcome.body)
    test.assertIsNone(outcome.media_type)
    test.assertIsNone(outcome.locator)
    test.assertIsNone(outcome.observed_at)
    test.assertIsNone(outcome.version)
    test.assertIsNone(outcome.blob_sha)
    test.assertIs(type(outcome.error), str)
    test.assertTrue(outcome.error)
    test.assertTrue(outcome.error.isascii())
    test.assertNotIn(SENTINEL, outcome.error)


class ValidationFailureTests(unittest.TestCase):
    """Scenario 1: invalid capability/arguments/repository/limits fail
    before any spawn."""

    def test_invalid_requests_fail_without_spawn(self):
        cases = (
            {"capability": "github.issue.write"},
            {"capability": None},
            {"capability": ISSUE_CAP, "arguments": file_args()},
            {"capability": ISSUE_CAP, "arguments": "not a dict"},
            {
                "capability": ISSUE_CAP,
                "arguments": {"repository": "other/repo", "number": 1},
            },
            {
                "capability": ISSUE_CAP,
                "arguments": {"repository": REPO, "number": 0},
            },
            {
                "capability": FILE_CAP,
                "arguments": file_args("../escape", "x" * 40),
            },
            {"timeout_seconds": 0},
            {"timeout_seconds": 31},
            {"timeout_seconds": "5"},
            {"max_bytes": 0},
            {"max_bytes": 1048577},
            {"operation_id": None},
            {"operation_id": 42},
        )
        for patch in cases:
            with self.subTest(patch=patch):
                recorder = RecordingPopen(emit_script(issue_payload()))
                runner = runner_for(popen=recorder)
                outcome = do_read(runner, **patch)
                assert_failed(self, outcome)
                self.assertEqual(recorder.calls, [])
                self.assertEqual(recorder.children, [])

    def test_wrong_runner_type_fails_without_spawn(self):
        for bad in (None, 42, "runner", object()):
            outcome = do_read(bad)
            assert_failed(self, outcome)

    def test_runner_subclass_cannot_spoof_success(self):
        class SpoofRunner(SubprocessRunner):
            def capture(self, request):
                return (issue_payload(), FIXED_NOW)

        runner = SpoofRunner(
            gh_path=sys.executable, config_dir=CONFIG_DIR
        )
        outcome = do_read(runner)
        assert_failed(self, outcome)

    def test_runner_requires_absolute_path(self):
        for bad in ("gh", "bin/gh", "./gh", "", "gh\x00x", 42, None):
            with self.assertRaises(ValueError):
                SubprocessRunner(gh_path=bad, config_dir=CONFIG_DIR)
        runner = SubprocessRunner(
            gh_path=sys.executable, config_dir=CONFIG_DIR
        )
        self.assertEqual(runner.gh_path, sys.executable)
        self.assertEqual(runner.config_dir, CONFIG_DIR)

    def test_runner_requires_absolute_config_dir(self):
        for bad in ("cfg", "etc/gh", "./gh-config", "", "gh\x00x", 42, None):
            with self.assertRaises(ValueError):
                SubprocessRunner(
                    gh_path=sys.executable, config_dir=bad
                )

    def test_runner_requires_callable_clock_and_popen(self):
        with self.assertRaises(TypeError):
            SubprocessRunner(
                gh_path=sys.executable, config_dir=CONFIG_DIR, clock=42
            )
        with self.assertRaises(TypeError):
            SubprocessRunner(
                gh_path=sys.executable, config_dir=CONFIG_DIR, popen="x"
            )


class SuccessTests(unittest.TestCase):
    """Scenarios 2 and 3: file and issue success outcomes."""

    def test_file_success(self):
        data = "héllo 世界\n".encode("utf-8")
        recorder = RecordingPopen(emit_script(file_payload(data)))
        runner = runner_for(popen=recorder)
        outcome = do_read(
            runner,
            capability=FILE_CAP,
            arguments=file_args("docs/a b.md"),
        )
        self.assertEqual(outcome.status, "succeeded")
        self.assertEqual(outcome.body, data)
        self.assertEqual(outcome.media_type, "text/plain; charset=utf-8")
        self.assertEqual(outcome.locator, "docs/a b.md@" + SHA)
        self.assertEqual(outcome.observed_at, FIXED_NOW)
        self.assertEqual(outcome.version, SHA)
        self.assertEqual(outcome.blob_sha, BLOB_SHA)
        self.assertIsNone(outcome.error)
        self.assertEqual(len(recorder.calls), 1)
        argv, kwargs = recorder.calls[0]
        self.assertEqual(
            argv[-1],
            "repos/thattor/personal-agent-lab/contents/docs/a%20b.md"
            "?ref=" + SHA,
        )

    def test_file_version_is_requested_pin_not_provider(self):
        # The payload blob_sha is provider metadata; version must equal the
        # requested ref even when the blob sha differs.
        recorder = RecordingPopen(
            emit_script(file_payload(b"x", sha="c" * 40))
        )
        outcome = do_read(
            runner_for(popen=recorder),
            capability=FILE_CAP,
            arguments=file_args(),
        )
        self.assertEqual(outcome.status, "succeeded")
        self.assertEqual(outcome.version, SHA)
        self.assertEqual(outcome.blob_sha, "c" * 40)

    def test_issue_success(self):
        recorder = RecordingPopen(
            emit_script(issue_payload(number=42, body=None))
        )
        runner = runner_for(popen=recorder)
        outcome = do_read(runner)
        self.assertEqual(outcome.status, "succeeded")
        self.assertEqual(outcome.media_type, "application/json")
        self.assertEqual(outcome.locator, "issues/42")
        self.assertEqual(outcome.observed_at, FIXED_NOW)
        self.assertEqual(outcome.version, "2026-10-10T01:02:03Z")
        self.assertIsNone(outcome.error)
        parsed = json.loads(outcome.body)
        self.assertEqual(
            parsed,
            {
                "number": 42,
                "title": "t",
                "state": "open",
                "body": None,
                "updated_at": "2026-10-10T01:02:03Z",
            },
        )
        expected = json.dumps(
            parsed, sort_keys=True, separators=(",", ":"), ensure_ascii=False
        ).encode("utf-8")
        self.assertEqual(outcome.body, expected)
        self.assertNotIn(SENTINEL.encode(), outcome.body)
        self.assertNotIn(b"url", outcome.body)

    def test_default_popen_executable_script(self):
        payload = file_payload(b"via real exec\n")
        with tempfile.TemporaryDirectory() as tmp:
            script = pathlib.Path(tmp) / "gh"
            script.write_text(
                "#!" + sys.executable + "\n" + emit_script(payload) + "\n"
            )
            script.chmod(0o700)
            runner = SubprocessRunner(
                gh_path=str(script),
                config_dir=tmp,
                clock=lambda: FIXED_NOW,
            )
            outcome = do_read(
                runner, capability=FILE_CAP, arguments=file_args()
            )
        self.assertEqual(outcome.status, "succeeded")
        self.assertEqual(outcome.body, b"via real exec\n")


class BoundedTerminationTests(unittest.TestCase):
    """Scenarios 4 and 5: overflow/timeout kill+reap and unconfirmed reap."""

    def test_stdout_overflow_kills_and_reaps(self):
        recorder = RecordingPopen(
            "import sys;sys.stdout.buffer.write(b'x' * 300000);"
            "sys.stdout.flush();import time;time.sleep(60)"
        )
        runner = runner_for(popen=recorder)
        outcome = do_read(runner, max_bytes=64)
        assert_failed(self, outcome)
        self.assertIn("limit", outcome.error)
        self.assertEqual(len(recorder.children), 1)
        child = recorder.children[0]
        self.assertIsNotNone(child.returncode)
        self.assertNotEqual(child.returncode, 0)

    def test_timeout_confirmed_reap_is_failed(self):
        recorder = RecordingPopen(SLEEP_CHILD)
        runner = runner_for(popen=recorder)
        outcome = do_read(runner, timeout_seconds=1)
        assert_failed(self, outcome)
        self.assertIn("timeout", outcome.error)
        child = recorder.children[0]
        self.assertIsNotNone(child.returncode)
        self.assertNotEqual(child.returncode, 0)

    def test_unconfirmed_reap_is_unknown(self):
        reals = []

        def factory(argv, **kwargs):
            real = subprocess.Popen(
                [sys.executable, "-c", SLEEP_CHILD], **kwargs
            )
            reals.append(real)
            return UnreapableChild(real)

        runner = runner_for(popen=factory)
        outcome = do_read(runner, timeout_seconds=1)
        self.assertEqual(outcome.status, "unknown")
        self.assertIsNone(outcome.body)
        self.assertIs(type(outcome.error), str)
        self.assertNotIn(SENTINEL, outcome.error)
        # The group signals still reached the real owned child.
        real = reals[0]
        self.assertIsNotNone(real.wait(timeout=10))
        for stream in (real.stdin, real.stdout, real.stderr):
            if stream is not None:
                stream.close()

    def test_stderr_overflow_kills_and_reaps(self):
        recorder = RecordingPopen(
            "import sys;sys.stderr.buffer.write(b'e' * 5000);"
            "sys.stderr.flush();import time;time.sleep(60)"
        )
        outcome = do_read(runner_for(popen=recorder))
        assert_failed(self, outcome)
        self.assertIn("limit", outcome.error)
        child = recorder.children[0]
        self.assertIsNotNone(child.returncode)
        self.assertNotEqual(child.returncode, 0)

    def test_wait_interrupt_inside_pump_failed_cleanup_propagates(self):
        # The first wait() raises KeyboardInterrupt from inside the
        # ``except _PumpFailed`` cleanup path (the interrupt lands during
        # ``_terminate``'s reap in ``_settle_group``, not in capture's
        # ``except BaseException`` branch). The interrupt must still
        # propagate, and the already-signaled real child is confirmed
        # dead by SIGTERM.
        reals = []

        def factory(argv, **kwargs):
            real = subprocess.Popen(
                [
                    sys.executable,
                    "-c",
                    "import os,time;os.close(1);os.close(2);time.sleep(60)",
                ],
                **kwargs,
            )
            reals.append(real)
            return InterruptibleChild(real)

        runner = runner_for(popen=factory)
        with self.assertRaises(KeyboardInterrupt):
            do_read(runner, timeout_seconds=1)
        real = reals[0]
        self.assertEqual(real.wait(timeout=10), -signal.SIGTERM)
        for stream in (real.stdin, real.stdout, real.stderr):
            if stream is not None:
                stream.close()

    def test_pump_base_exception_propagates_after_owned_termination(self):
        # ``_pump`` itself raises KeyboardInterrupt, so capture's
        # ``except BaseException`` branch runs: the interruption
        # propagates only after a bounded owned termination has
        # confirmed the child dead by SIGTERM and the group empty.
        reals = []

        def factory(argv, **kwargs):
            real = subprocess.Popen(
                [sys.executable, "-c", SLEEP_CHILD], **kwargs
            )
            reals.append(real)
            return real

        def interrupting_pump(self, child, request, deadline):
            raise KeyboardInterrupt

        runner = runner_for(popen=factory)
        saved_pump = SubprocessRunner._pump
        SubprocessRunner._pump = interrupting_pump
        try:
            with self.assertRaises(KeyboardInterrupt):
                do_read(runner, timeout_seconds=30)
        finally:
            SubprocessRunner._pump = saved_pump
        real = reals[0]
        self.assertEqual(real.returncode, -signal.SIGTERM)
        self.assertEqual(real.wait(timeout=10), -signal.SIGTERM)
        with self.assertRaises(ProcessLookupError):
            os.killpg(real.pid, 0)
        for stream in (real.stdin, real.stdout, real.stderr):
            if stream is not None:
                stream.close()

    def test_missing_waitid_peek_fails_closed_unknown(self):
        # Documented platform gap: without a non-reaping waitid the leaf
        # cannot prove leader exit while the PID pins the group, so it
        # must fail closed unknown rather than fake a cleanup.
        reals = []

        def factory(argv, **kwargs):
            real = subprocess.Popen(
                [sys.executable, "-c", SLEEP_CHILD], **kwargs
            )
            reals.append(real)
            return real

        saved = executor._HAS_WAITID_PEEK
        executor._HAS_WAITID_PEEK = False
        try:
            outcome = do_read(runner_for(popen=factory), timeout_seconds=1)
        finally:
            executor._HAS_WAITID_PEEK = saved
            for real in reals:
                real.kill()
                real.wait()
                for stream in (real.stdin, real.stdout, real.stderr):
                    if stream is not None:
                        stream.close()
        self.assertEqual(outcome.status, "unknown")
        self.assertIsNone(outcome.body)
        self.assertIs(type(outcome.error), str)


class FailureKindTests(unittest.TestCase):
    """Scenario 6: nonzero exit, not-found shape, invalid JSON, duplicate
    keys and wrong type all fail with fixed errors and no stderr leak."""

    def test_nonzero_exit_no_stderr_leak(self):
        recorder = RecordingPopen(
            "import sys;sys.stderr.write(%r);sys.exit(3)" % SENTINEL
        )
        outcome = do_read(runner_for(popen=recorder))
        assert_failed(self, outcome)
        self.assertEqual(len(recorder.calls), 1)
        self.assertNotIn(SENTINEL, outcome.error)
        self.assertEqual(recorder.children[0].returncode, 3)

    def test_not_found_shape_fails(self):
        recorder = RecordingPopen(
            emit_script(
                json.dumps(
                    {"message": "Not Found", "documentation_url": SENTINEL}
                ).encode("utf-8")
            )
        )
        outcome = do_read(runner_for(popen=recorder))
        assert_failed(self, outcome)

    def test_invalid_json_fails(self):
        outcome = do_read(runner_for(script="import sys;sys.stdout.write('not json')"))
        assert_failed(self, outcome)

    def test_duplicate_keys_fail(self):
        raw = (
            b'{"number":42,"number":43,"title":"t","state":"open",'
            b'"body":null,"updated_at":"2026-10-10T01:02:03Z"}'
        )
        outcome = do_read(runner_for(script=emit_script(raw)))
        assert_failed(self, outcome)

    def test_non_file_type_fails(self):
        raw = json.dumps(
            {
                "type": "symlink",
                "target": SENTINEL,
                "encoding": "base64",
                "size": 1,
                "sha": BLOB_SHA,
                "content": "eA==",
            }
        ).encode("utf-8")
        outcome = do_read(
            runner_for(script=emit_script(raw)),
            capability=FILE_CAP,
            arguments=file_args(),
        )
        assert_failed(self, outcome)

    def test_pull_request_payload_fails(self):
        outcome = do_read(
            runner_for(script=emit_script(issue_payload(pull_request={})))
        )
        assert_failed(self, outcome)

    def test_issue_number_mismatch_fails(self):
        outcome = do_read(
            runner_for(script=emit_script(issue_payload(number=43)))
        )
        assert_failed(self, outcome)

    def test_empty_stdout_fails(self):
        outcome = do_read(runner_for(script="import sys;sys.exit(0)"))
        assert_failed(self, outcome)


class GroupDescendantTests(unittest.TestCase):
    """Scenario 7b: a process-group descendant that ignores SIGTERM must
    still be killed and proved gone before cessation is reported. The
    leader exit is observed without reaping so its PID pins the group id
    while SIGKILL is delivered; signal-0 probes then prove the group is
    empty. Functional checks use real synthetic grandchildren."""

    def _await_dead(self, pid):
        deadline = time.monotonic() + 10
        while True:
            try:
                os.kill(pid, 0)
            except ProcessLookupError:
                return
            self.assertLess(
                time.monotonic(), deadline, "descendant survived"
            )
            time.sleep(0.05)

    def _run_grandchild(self, tail, **kw):
        with tempfile.TemporaryDirectory() as tmp:
            pidfile = os.path.join(tmp, "grandchild.pid")
            script = grandchild_script(pidfile, tail)
            outcome = do_read(runner_for(script=script), **kw)
            with open(pidfile) as handle:
                gpid = int(handle.read().strip())
            self._await_dead(gpid)
        return outcome

    def test_descendant_killed_after_leader_exit_zero(self):
        outcome = self._run_grandchild(
            emit_script(issue_payload()),
            timeout_seconds=10,
        )
        self.assertEqual(outcome.status, "succeeded")

    def test_descendant_killed_after_leader_nonzero(self):
        outcome = self._run_grandchild(
            "import sys;sys.exit(3)",
            timeout_seconds=10,
        )
        assert_failed(self, outcome)

    def test_descendant_killed_on_timeout(self):
        # The leader sleeps holding the pipes open; the pump times out,
        # SIGTERM kills only the leader (grandchild ignores it), and the
        # zombie-pinned group SIGKILL then reaps the descendant.
        outcome = self._run_grandchild(
            "import time;time.sleep(60)",
            timeout_seconds=1,
        )
        assert_failed(self, outcome)
        self.assertIn("timeout", outcome.error)


class ObservationAndDecodeTests(unittest.TestCase):
    """Scenario 7c: post-cessation observation/decoding failures are
    total functions returning fixed errors, never raw exceptions or
    input bytes."""

    def test_clock_exception_is_failed_without_leak(self):
        def bad_clock():
            raise RuntimeError(SENTINEL)

        outcome = do_read(runner_for(clock=bad_clock))
        assert_failed(self, outcome)

    def test_clock_invalid_value_is_failed(self):
        for bad in (None, 42, b"x", "not a timestamp", "2026-10-11"):
            with self.subTest(bad=bad):
                outcome = do_read(runner_for(clock=lambda v=bad: v))
                assert_failed(self, outcome)

    def test_file_decode_unexpected_error_is_failed_without_leak(self):
        original = executor.decode_file

        def bad_decode(raw, *, max_bytes):
            raise UnicodeDecodeError(
                "utf-8", SENTINEL.encode("utf-8"), 0, 1, "boom"
            )

        executor.decode_file = bad_decode
        try:
            outcome = do_read(
                runner_for(script=emit_script(file_payload())),
                capability=FILE_CAP,
                arguments=file_args(),
            )
        finally:
            executor.decode_file = original
        assert_failed(self, outcome)

    def test_issue_decode_unexpected_error_is_failed_without_leak(self):
        original = executor.decode_issue

        def bad_decode(raw, *, max_bytes):
            raise ValueError(SENTINEL)

        executor.decode_issue = bad_decode
        try:
            outcome = do_read(
                runner_for(script=emit_script(issue_payload()))
            )
        finally:
            executor.decode_issue = original
        assert_failed(self, outcome)


class ProvenanceTests(unittest.TestCase):
    """Scenario 7d: locator/version/number consistency comes from the
    validated request snapshot, not from a re-read of caller state."""

    def test_arguments_dict_subclass_rejected(self):
        class ShiftingDict(dict):
            def __getitem__(self, key):
                if key == "ref":
                    return "c" * 40
                return super().__getitem__(key)

        recorder = RecordingPopen(emit_script(file_payload()))
        outcome = do_read(
            runner_for(popen=recorder),
            capability=FILE_CAP,
            arguments=ShiftingDict(file_args()),
        )
        assert_failed(self, outcome)
        self.assertEqual(recorder.calls, [])

    def test_provenance_matches_argv_not_mutated_arguments(self):
        args = file_args()
        calls = []

        def mutating_clock():
            calls.append(1)
            args["ref"] = "c" * 40
            args["path"] = "evil.sh"
            return FIXED_NOW

        recorder = RecordingPopen(emit_script(file_payload()))
        outcome = do_read(
            runner_for(popen=recorder, clock=mutating_clock),
            capability=FILE_CAP,
            arguments=args,
        )
        self.assertEqual(outcome.status, "succeeded")
        self.assertEqual(calls, [1])
        self.assertEqual(outcome.version, SHA)
        self.assertEqual(outcome.locator, "README.md@" + SHA)

    def test_provenance_matches_argv_after_validation_time_mutation(self):
        # Module prepare_read is patched to mutate the ORIGINAL caller
        # dict after it validates. read() must have snapshotted the
        # arguments into a private real dict before validation, so the
        # returned version/locator and the spawned argv all still carry
        # the originally validated path and pinned ref.
        args = file_args()
        saved_prepare = executor.prepare_read
        real_prepare = request_module.prepare_read

        def mutating_prepare(capability, arguments, **kw):
            request = real_prepare(capability, arguments, **kw)
            args["ref"] = "c" * 40
            args["path"] = "evil.sh"
            args["repository"] = "other/repo"
            return request

        recorder = RecordingPopen(emit_script(file_payload()))
        executor.prepare_read = mutating_prepare
        try:
            outcome = do_read(
                runner_for(popen=recorder),
                capability=FILE_CAP,
                arguments=args,
            )
        finally:
            executor.prepare_read = saved_prepare
        self.assertEqual(outcome.status, "succeeded")
        self.assertEqual(outcome.version, SHA)
        self.assertEqual(outcome.locator, "README.md@" + SHA)
        self.assertEqual(len(recorder.calls), 1)
        argv, _kwargs = recorder.calls[0]
        self.assertEqual(
            argv[-1],
            "repos/thattor/personal-agent-lab/contents/README.md?ref=" + SHA,
        )


class SpawnContractTests(unittest.TestCase):
    """Scenario 7: exact argv, no shell, fixed env, exactly one spawn."""

    def test_argv_env_and_single_spawn(self):
        os.environ["PAL_TEST_TOKEN_SENTINEL"] = SENTINEL
        try:
            recorder = RecordingPopen(emit_script(issue_payload()))
            runner = runner_for(popen=recorder)
            outcome = do_read(runner)
        finally:
            os.environ.pop("PAL_TEST_TOKEN_SENTINEL", None)
        self.assertEqual(outcome.status, "succeeded")
        self.assertEqual(len(recorder.calls), 1)
        argv, kwargs = recorder.calls[0]
        self.assertEqual(
            argv,
            [
                sys.executable,
                "api",
                "--method",
                "GET",
                "--hostname",
                "github.com",
                "repos/thattor/personal-agent-lab/issues/42",
            ],
        )
        self.assertNotIn("shell", kwargs)
        self.assertIs(kwargs["stdin"], subprocess.DEVNULL)
        self.assertIs(kwargs["stdout"], subprocess.PIPE)
        self.assertIs(kwargs["stderr"], subprocess.PIPE)
        self.assertIs(kwargs["start_new_session"], True)
        self.assertEqual(kwargs["cwd"], os.path.abspath(os.sep))
        env = kwargs["env"]
        self.assertEqual(env, EXPECTED_ENV)
        self.assertNotIn("PAL_TEST_TOKEN_SENTINEL", env)
        for key in env:
            self.assertNotIn("TOKEN", key.upper())
        self.assertNotIn(SENTINEL, repr(env))

    def test_failed_read_does_not_retry(self):
        recorder = RecordingPopen("import sys;sys.exit(7)")
        outcome = do_read(runner_for(popen=recorder))
        assert_failed(self, outcome)
        self.assertEqual(len(recorder.calls), 1)

    def test_spawn_failure_is_failed(self):
        def bad_factory(argv, **kwargs):
            raise OSError("cannot spawn")

        outcome = do_read(runner_for(popen=bad_factory))
        assert_failed(self, outcome)


class ModuleHygieneTests(unittest.TestCase):
    """Scenario 8: no sqlite3/socket/urllib imports and no PATH search."""

    def _imports(self, path):
        tree = ast.parse(path.read_text())
        roots = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                roots.update(
                    alias.name.split(".")[0] for alias in node.names
                )
            elif isinstance(node, ast.ImportFrom):
                roots.add((node.module or "").split(".")[0])
        return roots

    def test_forbidden_imports_absent(self):
        for module in (
            executor,
            issue_module,
            bounded_module,
            file_module,
        ):
            path = pathlib.Path(module.__file__)
            imports = self._imports(path)
            self.assertFalse(
                imports & {"sqlite3", "socket", "urllib", "shutil", "http"},
                (module.__name__, imports),
            )
            source = path.read_text()
            self.assertNotIn("which(", source)
            self.assertNotIn("defpath", source)

    def test_request_module_imports_only_pure_urllib_parse(self):
        # github_read_request_v5 legitimately uses urllib.parse.quote for
        # path encoding; no other urllib (or any network/DB module) may
        # appear in the request leaf.
        path = pathlib.Path(request_module.__file__)
        tree = ast.parse(path.read_text())
        full_names = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                full_names.update(alias.name for alias in node.names)
            elif isinstance(node, ast.ImportFrom):
                full_names.add(node.module or "")
        urllib_like = {n for n in full_names if n.split(".")[0] == "urllib"}
        self.assertEqual(urllib_like, {"urllib.parse"})
        roots = {n.split(".")[0] for n in full_names}
        self.assertFalse(
            roots & {"sqlite3", "socket", "shutil", "http"},
            roots,
        )

    def test_no_socket_or_sqlite_at_runtime(self):
        code = (
            "import sys\n"
            "import pal.github_read_executor_v5\n"
            "import pal.github_issue_payload_v5\n"
            "print('socket' in sys.modules, 'sqlite3' in sys.modules)\n"
        )
        proc = subprocess.run(
            [sys.executable, "-E", "-s", "-B", "-c", code],
            capture_output=True,
            text=True,
            cwd=pathlib.Path(executor.__file__).parents[1],
            timeout=30,
        )
        self.assertEqual(proc.returncode, 0, proc.stderr)
        self.assertEqual(proc.stdout.strip(), "False False")


if __name__ == "__main__":
    unittest.main()
