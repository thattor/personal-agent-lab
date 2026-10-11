"""EXE-02 single GitHub read executor leaf (PAL v5).

Trusted post-reservation leaf only: EXE-01 owns authorization, C15
reservation, operation_id issuance, grants, retry_index, persistent
observation, source hashing and receipts. A direct call to ``read`` is not
itself permission; this module issues no IDs, grants, receipts or records,
performs no retries and no CLI fallback, and touches no database, model,
network API or credential store by itself. It runs exactly one owned
``gh api`` child per call.

The executable path and the ``gh`` configuration directory are explicitly
injected by the trusted host as absolute ``gh_path`` and ``config_dir``
strings on ``SubprocessRunner``. There is no PATH search, no default
runner and no caller-passed shell: the child always runs with
``shell=False``, ``/dev/null`` stdin, ``cwd`` at the filesystem root (so
no caller working-directory or repository context leaks in), and a fixed
minimal allowlist environment that never inherits caller variables or
tokens: ``GH_CONFIG_DIR`` plus ``GH_PROMPT_DISABLED=1``,
``GH_NO_UPDATE_NOTIFIER=1``, ``NO_COLOR=1`` and ``LC_ALL=C``.

``ReadOutcome.version`` for ``github.file.read`` is the pinned REQUESTED
immutable commit SHA used in the successful contents query (the validated
``ref`` argument). It is explicitly not an independently confirmed API
commit field. The provider-returned blob SHA is preserved separately in
``ReadOutcome.blob_sha`` as metadata only; it is not commit provenance.
For ``github.issue.read`` ``version`` is the provider ``updated_at``
timestamp at second granularity; edits within the same second are not
distinguished.

stderr is consumed under a fixed bound and discarded: it is never returned
or persisted. ``error`` carries fixed constant strings only. ``failed`` is
returned only when owned EOF/wait/cleanup evidence confirms the child's
cessation; if cessation cannot be proved the outcome is ``unknown`` and no
body is returned.

Cessation proof is group-complete, not just leader-complete: the leader's
exit is observed WITHOUT reaping via ``waitid(P_PID, pid, WEXITED |
WNOHANG | WNOWAIT)`` so the still-owned leader PID pins its process-group
id while the whole group is killed; only then is the leader reaped and
the group proved empty by signal-0 probes. No signal other than 0 is ever
sent after the leader PID could have been released, so no signal can
reach a recycled or foreign group. On a platform without non-reaping
waitid support, or when death/reap/group-empty cannot be proved, every
spawned path fails closed as ``unknown``; no fake cleanup is claimed.

``read`` and ``capture`` are synchronous and block for at most
``timeout_seconds`` plus the fixed termination/reap/group-empty grace
periods (a few seconds); EXE-01 code on an event loop must call this leaf
off the loop (e.g. ``asyncio.to_thread``). A ``BaseException``
(KeyboardInterrupt/SystemExit/CancelledError) raised out of the pump is
propagated after a bounded best-effort owned termination; EXE-01 treats
such propagation as ``unknown``, never as success.
"""

import os
import re
import selectors
import signal
import subprocess
import time
from dataclasses import dataclass

from pal.bounded_payload_v5 import PayloadBuffer, PayloadLimitError
from pal.github_file_payload_v5 import FilePayloadError, decode_file
from pal.github_issue_payload_v5 import (
    IssuePayloadError,
    canonical_issue,
    decode_issue,
)
from pal.github_read_request_v5 import ReadRequestError, prepare_read

__all__ = ("ReadOutcome", "SubprocessRunner", "read")

SUCCEEDED = "succeeded"
FAILED = "failed"
UNKNOWN = "unknown"
_STATUSES = frozenset((SUCCEEDED, FAILED, UNKNOWN))

_FILE_CAPABILITY = "github.file.read"

_MEDIA_JSON = "application/json"
_MEDIA_TEXT = "text/plain; charset=utf-8"

_STDERR_CAP = 4096
_READ_CHUNK = 8192
_TERM_GRACE_SECONDS = 1.0
_KILL_GRACE_SECONDS = 2.0
_PEEK_INTERVAL_SECONDS = 0.01
_CHILD_CWD = os.path.abspath(os.sep)

_OBSERVED_AT = re.compile(
    r"\A\d{4}-(0[1-9]|1[0-2])-(0[1-9]|[12]\d|3[01])"
    r"T([01]\d|2[0-3]):[0-5]\d:[0-5]\dZ\Z"
)

# Non-reaping waitid is the only supported way to prove leader exit while
# the PID still pins its process group. Without it every spawned path
# fails closed as unknown rather than risking a signal to a reused PID.
_HAS_WAITID_PEEK = all(
    hasattr(os, name)
    for name in ("waitid", "P_PID", "WEXITED", "WNOHANG", "WNOWAIT")
)

_MSG_OPERATION_ID = "operation_id must be a str"
_MSG_RUNNER = "runner must be a SubprocessRunner"
_MSG_SPAWN = "child process could not be spawned"
_MSG_TIMEOUT = "child did not finish within timeout_seconds"
_MSG_STDOUT_LIMIT = "child stdout exceeded max_bytes limit"
_MSG_STDERR_LIMIT = "child stderr exceeded its byte limit"
_MSG_WAIT = "child exit status could not be observed"
_MSG_NONZERO = "child exited with a non-zero status"
_MSG_PUMP = "child output could not be consumed"
_MSG_CLOCK = "observation clock did not produce a valid timestamp"
_MSG_UNCONFIRMED = "child termination could not be confirmed"
_MSG_ISSUE_NUMBER = "issue number does not match the request"
_MSG_DECODE = "response could not be decoded"


class _ChildFailed(Exception):
    """Confirmed-failure carrier; message is always a fixed constant."""

    def __init__(self, message):
        super().__init__(message)
        self.message = message


class _PumpFailed(Exception):
    """Pump-phase failure; the child still needs owned termination."""

    def __init__(self, message):
        super().__init__(message)
        self.message = message


class _CessationUnconfirmed(Exception):
    """Owned termination, reap or group-empty proof could not be confirmed."""


@dataclass(frozen=True, slots=True)
class ReadOutcome:
    """C07 EXE-01←EXE-02 result value for one bounded read.

    ``version`` on a file read is the pinned REQUESTED commit SHA (the
    ``ref`` used in the contents query), not a provider-confirmed commit;
    ``blob_sha`` is provider metadata, never commit provenance. On an
    issue read ``version`` is the provider ``updated_at`` timestamp.
    ``error`` is a fixed constant on failed/unknown outcomes; ``body`` is
    only ever a complete succeeded body, never a partial read.
    """

    status: str
    body: bytes | None
    media_type: str | None
    locator: str | None
    observed_at: str | None
    version: str | None
    error: str | None
    blob_sha: str | None

    def __post_init__(self):
        if self.status not in _STATUSES:
            raise ValueError("invalid read status")
        if self.status == SUCCEEDED:
            valid = type(self.body) is bytes and self.error is None
        else:
            valid = self.body is None and type(self.error) is str
        for value in (
            self.media_type,
            self.locator,
            self.observed_at,
            self.version,
            self.blob_sha,
        ):
            if value is not None and type(value) is not str:
                valid = False
        if not valid:
            raise ValueError("invalid read outcome")


def _failed(message):
    return ReadOutcome(
        status=FAILED,
        body=None,
        media_type=None,
        locator=None,
        observed_at=None,
        version=None,
        error=message,
        blob_sha=None,
    )


def _unknown():
    return ReadOutcome(
        status=UNKNOWN,
        body=None,
        media_type=None,
        locator=None,
        observed_at=None,
        version=None,
        error=_MSG_UNCONFIRMED,
        blob_sha=None,
    )


def _utc_now():
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def _valid_absolute_path(value):
    return (
        type(value) is str
        and bool(value)
        and os.path.isabs(value)
        and "\x00" not in value
        and len(value.encode("utf-8")) <= 4096
    )


class SubprocessRunner:
    """Host-owned runner for one bounded ``gh api`` child per capture.

    ``gh_path`` and ``config_dir`` must be absolute path strings supplied
    by the trusted host; ``gh_path`` is never searched on PATH and no
    default exists. ``config_dir`` becomes the child's ``GH_CONFIG_DIR``
    (where gh resolves its hosts.yml authentication); its existence and
    contents are the host's responsibility. ``clock`` is a zero-argument
    callable returning the ``observed_at`` string; the default is a UTC
    ``YYYY-MM-DDTHH:MM:SSZ`` timestamp. ``popen`` is a
    ``subprocess.Popen``-compatible factory injectable by the host and by
    tests; the default is ``subprocess.Popen``. There is no default
    runner instance at module level.
    """

    __slots__ = ("_gh_path", "_config_dir", "_clock", "_popen")

    def __init__(self, *, gh_path, config_dir, clock=None, popen=None):
        if not _valid_absolute_path(gh_path):
            raise ValueError("gh_path must be an absolute path string")
        if not _valid_absolute_path(config_dir):
            raise ValueError("config_dir must be an absolute path string")
        if clock is None:
            clock = _utc_now
        if popen is None:
            popen = subprocess.Popen
        if not callable(clock) or not callable(popen):
            raise TypeError("clock and popen must be callable")
        self._gh_path = gh_path
        self._config_dir = config_dir
        self._clock = clock
        self._popen = popen

    @property
    def gh_path(self):
        return self._gh_path

    @property
    def config_dir(self):
        return self._config_dir

    def capture(self, request):
        """Run one owned child for a validated ``ReadRequest``.

        Returns ``(bounded_stdout_bytes, observed_at)`` only after owned
        EOF on both streams, owned wait confirms exit status 0, and the
        child's whole process group is proved empty. Raises
        ``_ChildFailed`` for confirmed failures and
        ``_CessationUnconfirmed`` when cessation cannot be proved; no
        partial output escapes in either case. A ``BaseException`` out of
        the pump is re-raised after a bounded best-effort termination;
        EXE-01 treats that propagation as unknown.
        """
        deadline = time.monotonic() + request.timeout_seconds
        child = self._spawn(request)
        try:
            try:
                raw = self._pump(child, request, deadline)
                self._finish(child, deadline)
            except _PumpFailed as error:
                self._terminate(child)
                raise _ChildFailed(error.message) from None
            except _CessationUnconfirmed:
                raise
            except Exception:
                self._terminate(child)
                raise _ChildFailed(_MSG_PUMP) from None
            except BaseException:
                try:
                    self._terminate(child)
                except _CessationUnconfirmed:
                    pass
                raise
            observed_at = self._observed()
        finally:
            self._close(child)
        return raw, observed_at

    def _observed(self):
        try:
            value = self._clock()
        except Exception:
            raise _ChildFailed(_MSG_CLOCK) from None
        if type(value) is not str or _OBSERVED_AT.fullmatch(value) is None:
            raise _ChildFailed(_MSG_CLOCK)
        return value

    def _spawn(self, request):
        argv = [self._gh_path, *request.argv[1:]]
        env = {
            "GH_CONFIG_DIR": self._config_dir,
            "GH_PROMPT_DISABLED": "1",
            "GH_NO_UPDATE_NOTIFIER": "1",
            "NO_COLOR": "1",
            "LC_ALL": "C",
        }
        try:
            return self._popen(
                argv,
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                cwd=_CHILD_CWD,
                start_new_session=True,
            )
        except Exception:
            raise _ChildFailed(_MSG_SPAWN) from None

    @staticmethod
    def _close(child):
        for stream in (child.stdin, child.stdout, child.stderr):
            if stream is not None:
                try:
                    stream.close()
                except Exception:
                    pass

    def _pump(self, child, request, deadline):
        buffer = PayloadBuffer(max_bytes=request.max_bytes)
        stderr_seen = 0
        with selectors.DefaultSelector() as selector:
            for stream, name in (
                (child.stdout, "stdout"),
                (child.stderr, "stderr"),
            ):
                os.set_blocking(stream.fileno(), False)
                selector.register(stream, selectors.EVENT_READ, name)
            while selector.get_map():
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    raise _PumpFailed(_MSG_TIMEOUT)
                for key, _mask in selector.select(min(remaining, 0.1)):
                    stream, name = key.fileobj, key.data
                    try:
                        part = os.read(stream.fileno(), _READ_CHUNK)
                    except BlockingIOError:
                        continue
                    if not part:
                        selector.unregister(stream)
                        continue
                    if name == "stdout":
                        try:
                            buffer.append(part)
                        except PayloadLimitError:
                            raise _PumpFailed(_MSG_STDOUT_LIMIT) from None
                    else:
                        stderr_seen += len(part)
                        if stderr_seen > _STDERR_CAP:
                            raise _PumpFailed(_MSG_STDERR_LIMIT)
        return buffer.getvalue()

    def _finish(self, child, deadline):
        """Prove leader exit (unreaped), settle the group, check status."""
        if not self._wait_exit(child, deadline):
            raise _PumpFailed(_MSG_TIMEOUT)
        self._settle_group(child)
        code = child.returncode
        if type(code) is not int:
            raise _PumpFailed(_MSG_WAIT)
        if code != 0:
            raise _PumpFailed(_MSG_NONZERO)

    @staticmethod
    def _peek_exit(child):
        """True only when leader exit is proved WITHOUT reaping the PID.

        ``waitid(WNOHANG | WNOWAIT)`` reports an unreaped zombie, so the
        owned leader PID keeps pinning its process-group id. Raises
        ``_CessationUnconfirmed`` when the platform lacks the primitive or
        the PID is no longer ours while Popen recorded no status.
        """
        if child.returncode is not None:
            return True
        if not _HAS_WAITID_PEEK:
            raise _CessationUnconfirmed
        try:
            info = os.waitid(
                os.P_PID,
                child.pid,
                os.WEXITED | os.WNOHANG | os.WNOWAIT,
            )
        except ChildProcessError:
            if child.returncode is not None:
                return True
            raise _CessationUnconfirmed from None
        except OSError:
            raise _CessationUnconfirmed from None
        return info is not None

    def _wait_exit(self, child, deadline):
        """True once exit is proved unreaped; False at ``deadline``."""
        while time.monotonic() < deadline:
            if self._peek_exit(child):
                return True
            time.sleep(_PEEK_INTERVAL_SECONDS)
        return self._peek_exit(child)

    def _settle_group(self, child):
        """Kill the group while the leader PID still pins it, reap the
        leader, then prove the group is empty.

        The leader is an unreaped zombie here (or Popen already recorded
        its status), so ``killpg(pid, SIGKILL)`` still targets this owned
        group and cannot reach a recycled id. After the reap, only
        signal-0 probes test for leftover descendants, and any real
        signal has already been sent while the PID was still pinned.
        """
        pid = child.pid
        if child.returncode is None:
            killpg = getattr(os, "killpg", None)
            if killpg is None:
                raise _CessationUnconfirmed
            try:
                killpg(pid, signal.SIGKILL)
            except (ProcessLookupError, PermissionError, OSError):
                pass
            try:
                child.wait(timeout=_KILL_GRACE_SECONDS)
            except subprocess.TimeoutExpired:
                raise _CessationUnconfirmed from None
        if type(child.returncode) is not int:
            raise _CessationUnconfirmed
        self._wait_group_empty(pid)

    @staticmethod
    def _wait_group_empty(pid):
        """Bounded proof that no process group with this id survives.

        Only signal 0 is used here: it never delivers a signal, so a
        pathological PID reuse can delay the proof into ``unknown`` but
        can never be killed by mistake.
        """
        killpg = getattr(os, "killpg", None)
        if killpg is None:
            raise _CessationUnconfirmed
        deadline = time.monotonic() + _KILL_GRACE_SECONDS
        while True:
            try:
                killpg(pid, 0)
            except ProcessLookupError:
                return
            except PermissionError:
                pass
            except OSError:
                raise _CessationUnconfirmed from None
            if time.monotonic() >= deadline:
                raise _CessationUnconfirmed
            time.sleep(_PEEK_INTERVAL_SECONDS)

    def _terminate(self, child):
        """Bounded owned termination, reap and group-empty proof.

        Process-group signals are sent only while the child PID is still
        owned (alive or an unreaped zombie pinning the group id), so no
        real signal can reach a recycled or foreign group; after the reap
        only signal-0 probes remain. Raises ``_CessationUnconfirmed``
        when death, reap or group-empty cannot be proved; callers map
        that to ``unknown`` rather than claiming a cleanup that did not
        happen.
        """
        try:
            killpg = getattr(os, "killpg", None)
            if child.returncode is None:
                if killpg is None:
                    raise _CessationUnconfirmed
                if not self._peek_exit(child):
                    try:
                        killpg(child.pid, signal.SIGTERM)
                    except (ProcessLookupError, PermissionError, OSError):
                        pass
                    term_deadline = time.monotonic() + _TERM_GRACE_SECONDS
                    if not self._wait_exit(child, term_deadline):
                        try:
                            killpg(child.pid, signal.SIGKILL)
                        except (
                            ProcessLookupError,
                            PermissionError,
                            OSError,
                        ):
                            pass
                        kill_deadline = (
                            time.monotonic() + _KILL_GRACE_SECONDS
                        )
                        if not self._wait_exit(child, kill_deadline):
                            raise _CessationUnconfirmed
                self._settle_group(child)
            else:
                self._wait_group_empty(child.pid)
            if child.returncode is None:
                raise _CessationUnconfirmed
        except _CessationUnconfirmed:
            raise
        except Exception:
            raise _CessationUnconfirmed from None


def read(
    *,
    operation_id,
    capability,
    arguments,
    timeout_seconds,
    max_bytes,
    runner,
):
    """C07 EXE-02 leaf: run one bounded read and return a ``ReadOutcome``.

    ``operation_id`` is only type-checked as ``str``; this leaf never
    issues, records or deduplicates IDs. ``arguments`` must satisfy
    ``prepare_read`` for the pinned repository; a real ``dict`` is
    copied into a private snapshot before validation (dict subclasses
    and non-dicts are still rejected), so a later mutation of the
    caller's mapping cannot change locator/version provenance or
    diverge from the argv actually used. On success the file body
    is the decoded content bytes and the issue body is canonical JSON;
    on any failure the outcome carries a fixed error constant and no body.
    """
    if type(operation_id) is not str:
        return _failed(_MSG_OPERATION_ID)
    arguments = dict(arguments) if type(arguments) is dict else arguments
    try:
        request = prepare_read(
            capability,
            arguments,
            timeout_seconds=timeout_seconds,
            max_bytes=max_bytes,
        )
    except ReadRequestError as error:
        return _failed(error.message)
    if type(runner) is not SubprocessRunner:
        return _failed(_MSG_RUNNER)
    if request.capability == _FILE_CAPABILITY:
        locator_path = arguments["path"]
        version_ref = arguments["ref"]
    else:
        number = arguments["number"]
    try:
        raw, observed_at = runner.capture(request)
    except _ChildFailed as error:
        return _failed(error.message)
    except _CessationUnconfirmed:
        return _unknown()
    try:
        if request.capability == _FILE_CAPABILITY:
            decoded = decode_file(raw, max_bytes=request.max_bytes)
            return ReadOutcome(
                status=SUCCEEDED,
                body=decoded.data,
                media_type=_MEDIA_TEXT,
                locator=locator_path + "@" + version_ref,
                observed_at=observed_at,
                version=version_ref,
                error=None,
                blob_sha=decoded.blob_sha,
            )
        issue = decode_issue(raw, max_bytes=request.max_bytes)
        if issue.number != number:
            return _failed(_MSG_ISSUE_NUMBER)
        return ReadOutcome(
            status=SUCCEEDED,
            body=canonical_issue(issue),
            media_type=_MEDIA_JSON,
            locator="issues/" + str(issue.number),
            observed_at=observed_at,
            version=issue.updated_at,
            error=None,
            blob_sha=None,
        )
    except (FilePayloadError, IssuePayloadError) as error:
        return _failed(error.message)
    except Exception:
        return _failed(_MSG_DECODE)
