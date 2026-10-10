"""PRI02-T/1 external qualification tool for one synthetic Primary-shaped call.

Python standard library only. The tool talks to NativeCandidates exclusively
through the installed public ``selection`` / ``infer_selected`` methods and uses
the frozen ``pal.primary_wire_v5`` parser for the returned wire text. No CO
private API is touched.

``runtime_binding=None`` always labels the returned evidence ``fixture``; the
result is never a native C15 proof. Raw request, prompt and return payloads
stay inside the caller-owned private ``attempt_dir``; the public mapping
carries only digests, fixed identifiers and fixed codes.
"""
import argparse
import hashlib
import importlib
import json
import os
from pathlib import Path
import re
import secrets
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from pal.contracts_v5 import Ref, RefKind, loads
from pal.primary_wire_v5 import parse_primary_output

_PROFILE = 'co-measured-native-cli-single-prompt/1'
_ROLE = 'implement'
_FOCUS = 'coding'
_POLICY = {'mode': 'fixed',
           'targets': {'implement': {'route': 'devin', 'model': 'swe-2-high'}}}
_ROUTE = 'devin'
_MODEL = 'swe-2-high'
_VERSION = '3000.11.3'
_COST_TIER = 'Free'
_TIMEOUT = 60
_MAX_REQUEST_BYTES = 32768
_ID_LIMIT = 256
_MAX_ITEMS = 64
_MEASUREMENT = re.compile(r'^sha256:[0-9a-f]{64}$')
_REQUEST_KEYS = frozenset(
    {'call_id', 'reservation_id', 'role', 'output_kind', 'messages', 'source_refs'})


def _canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'),
                      ensure_ascii=False, allow_nan=False).encode('utf-8')


def _digest(value):
    return 'sha256:' + hashlib.sha256(_canonical(value)).hexdigest()


def _utf8(value):
    try:
        value.encode('utf-8', 'strict')
    except UnicodeError:
        return False
    return True


def _bounded_id(value):
    return (type(value) is str and 0 < len(value) <= _ID_LIMIT
            and _utf8(value))


def _validate_request(request):
    """Closed C15-shaped mapping check; fixed safe ValueError, no data echoed."""
    if type(request) is not dict or set(request) != _REQUEST_KEYS:
        raise ValueError('invalid request')
    if any(type(key) is not str for key in request):
        raise ValueError('invalid request')
    if not _bounded_id(request['call_id']):
        raise ValueError('invalid request')
    if not _bounded_id(request['reservation_id']):
        raise ValueError('invalid request')
    if request['role'] != 'primary' or request['output_kind'] != 'primary_proposal':
        raise ValueError('invalid request')
    messages = request['messages']
    if type(messages) is not list or not 0 < len(messages) <= _MAX_ITEMS:
        raise ValueError('invalid request')
    for message in messages:
        if type(message) is not dict or set(message) != {'role', 'text'}:
            raise ValueError('invalid request')
        if message['role'] not in ('system', 'user'):
            raise ValueError('invalid request')
        if type(message['text']) is not str or not _utf8(message['text']):
            raise ValueError('invalid request')
    refs = request['source_refs']
    if type(refs) is not list or not 0 < len(refs) <= _MAX_ITEMS:
        raise ValueError('invalid request')
    for item in refs:
        if type(item) is not dict or set(item) != {'kind', 'id'}:
            raise ValueError('invalid request')
        if item['kind'] != 'record' or not _bounded_id(item['id']):
            raise ValueError('invalid request')
    try:
        data = _canonical(request)
    except Exception:
        raise ValueError('invalid request') from None
    if len(data) > _MAX_REQUEST_BYTES:
        raise ValueError('invalid request')
    return data


def _atomic_write(path, data):
    """fsynced write via sibling tmp + replace + directory fsync."""
    tmp = path.with_name(path.name + '.tmp')
    fd = os.open(tmp, os.O_WRONLY | os.O_CREAT | os.O_TRUNC, 0o600)
    try:
        handle = os.fdopen(fd, 'wb')
    except Exception:
        os.close(fd)
        raise
    try:
        handle.write(data)
        handle.flush()
        os.fsync(handle.fileno())
    except Exception:
        handle.close()
        try:
            os.unlink(tmp)
        except OSError:
            pass
        raise
    handle.close()
    os.replace(tmp, path)
    dirfd = os.open(path.parent, os.O_RDONLY)
    try:
        os.fsync(dirfd)
    finally:
        os.close(dirfd)


def _build_prompt(request):
    return ('PRI02-T/1 synthetic qualification fixture; every identifier below '
            'is synthetic test data, not product evidence.\n'
            'Reply with exactly one strict PRI01-WIRE JSON object of the form '
            '{"reply": <short ordinary reply>, "proposal": {"kind": "none"}} '
            'and nothing else.\n'
            'request=' + _canonical(request).decode('utf-8'))


def _evaluate(result, pin, pin_digest, request):
    """Correlated-export check: exact fields plus strict PRI01-WIRE none parse."""
    if type(result) is not dict:
        return False
    if result.get('route') != _ROUTE or result.get('model') != _MODEL:
        return False
    if type(result.get('tool_calls')) is not int or result.get('tool_calls') != 0:
        return False
    evidence = result.get('evidence')
    if type(evidence) is not dict:
        return False
    if evidence.get('version') != _VERSION or evidence.get('cost_tier') != _COST_TIER:
        return False
    if evidence.get('measurement_digest') != pin.get('measurement_digest'):
        return False
    if evidence.get('selection_digest') != pin_digest:
        return False
    text = result.get('text')
    if type(text) is not str or not text:
        return False
    refs = [Ref(RefKind.RECORD, item['id']) for item in request['source_refs']]
    try:
        parsed = parse_primary_output(text, current_record_ref=refs[0],
                                      candidates=[], allowed_record_refs=refs)
    except Exception:
        return False
    return (type(parsed) is dict and parsed.get('proposal') == {'kind': 'none'}
            and bool(parsed.get('reply')))


def qualify(request, *, candidates, attempt_dir, runtime_binding=None):
    """Run the one-attempt PRI02-T qualification and return a minimized mapping."""
    request_bytes = _validate_request(request)
    if runtime_binding is not None and type(runtime_binding) is not dict:
        raise ValueError('invalid runtime_binding')
    attempt = Path(attempt_dir)
    try:
        os.mkdir(attempt, 0o700)
    except FileExistsError:
        raise ValueError('attempt_dir exists') from None
    except OSError:
        raise ValueError('invalid attempt_dir') from None
    os.chmod(attempt, 0o700)

    evidence_kind = 'fixture' if runtime_binding is None else 'native_cli_compatibility'
    request_digest = 'sha256:' + hashlib.sha256(request_bytes).hexdigest()
    prompt = _build_prompt(request)
    prompt_digest = 'sha256:' + hashlib.sha256(prompt.encode('utf-8')).hexdigest()
    journal_path = attempt / 'journal.json'
    journal = {
        'profile': _PROFILE,
        'phase': 'prepared',
        'evidence_kind': evidence_kind,
        'request_digest': request_digest,
        'prompt_digest': prompt_digest,
        'pid': os.getpid(),
        'ppid': os.getppid(),
        'nonce': secrets.token_hex(16),
        'started': time.time(),
    }
    if runtime_binding is not None:
        try:
            journal['runtime_digest'] = _digest(runtime_binding)
        except Exception:
            pass
    _atomic_write(journal_path, _canonical(journal))
    _atomic_write(attempt / 'request.json', request_bytes)
    _atomic_write(attempt / 'prompt.txt', prompt.encode('utf-8'))
    if runtime_binding is not None:
        _atomic_write(attempt / 'runtime-binding.json', _canonical(runtime_binding))

    pin = None
    pin_digest = None
    result = None
    entered = [False]
    refused = [False]

    def _summary(status):
        out = {'status': status,
               'profile': _PROFILE,
               'evidence_kind': evidence_kind,
               'route': _ROUTE,
               'model': _MODEL,
               'request_digest': request_digest,
               'prompt_digest': prompt_digest}
        if pin_digest is not None:
            out['selection_digest'] = pin_digest
        if status == 'returned_correlated_export':
            out.update({'version': _VERSION,
                        'cost_tier': _COST_TIER,
                        'tool_calls': 0,
                        'measurement_digest': pin['measurement_digest']})
        else:
            out['code'] = status
        return out

    def _journal_terminal(status):
        journal['phase'] = 'terminal'
        journal['status'] = status
        _atomic_write(journal_path, _canonical(journal))

    def _finish_not_entered():
        try:
            _journal_terminal('not_entered')
        except Exception:
            pass
        return _summary('not_entered')

    def _hook():
        if entered[0] or refused[0]:
            refused[0] = True
            raise RuntimeError('before_launch already consumed')
        journal['phase'] = 'entering'
        _atomic_write(journal_path, _canonical(journal))
        entered[0] = True

    def _finalize(status):
        try:
            if result is not None:
                # Escaped JSON preserves a normally returned invalid Unicode
                # string for the strict wire rejection without losing its ending.
                raw = json.dumps(result, sort_keys=True, separators=(',', ':'),
                                 ensure_ascii=True, allow_nan=False).encode('utf-8')
                _atomic_write(attempt / 'return.json', raw)
            _journal_terminal(status)
        except Exception:
            status = 'unknown'
        return _summary(status)

    try:
        pin = candidates.selection(_ROLE, _FOCUS, policy=_POLICY)
    except Exception:
        return _finish_not_entered()
    except BaseException:
        try:
            _journal_terminal('not_entered')
        except Exception:
            pass
        raise

    try:
        pin_digest = _digest(pin)
    except Exception:
        pin_digest = None
    valid_pin = (type(pin) is dict
                 and pin.get('route') == _ROUTE
                 and pin.get('model') == _MODEL
                 and type(pin.get('measurement_digest')) is str
                 and bool(_MEASUREMENT.match(pin['measurement_digest']))
                 and pin_digest is not None)
    if not valid_pin:
        return _finish_not_entered()
    journal['pin_digest'] = pin_digest

    call_dir = attempt / 'call'
    try:
        os.mkdir(call_dir, 0o700)
        os.chmod(call_dir, 0o700)
    except OSError:
        return _finish_not_entered()

    try:
        result = candidates.infer_selected(pin, _ROLE, prompt, str(call_dir),
                                           timeout=_TIMEOUT, before_launch=_hook)
    except Exception:
        if not entered[0]:
            return _finish_not_entered()
        return _finalize('unknown')
    except BaseException:
        try:
            _journal_terminal('unknown' if entered[0] else 'not_entered')
        except Exception:
            pass
        raise

    if not entered[0] or refused[0]:
        return _finalize('unknown')
    if _evaluate(result, pin, pin_digest, request):
        return _finalize('returned_correlated_export')
    return _finalize('returned_invalid')


def _load_native_candidates(runtime):
    """Hash pinned CO sources under runtime, then load public NativeCandidates."""
    runtime = Path(runtime)
    digests = {}
    for relative in ('VERSION', 'co_v4/task/select.py', 'co_v4/task/infer.py',
                     'co_v4/task/transcript.py', 'co_v4/task/admission.py'):
        digests[relative] = 'sha256:' + hashlib.sha256(
            (runtime / relative).read_bytes()).hexdigest()
    version = (runtime / 'VERSION').read_text(encoding='utf-8').strip()
    if version != '0.4.5':
        raise ValueError('unqualified runtime version')
    sys.path.insert(0, str(runtime))
    module = importlib.import_module('co_v4.task.select')
    if Path(module.__file__).resolve() != (runtime / 'co_v4/task/select.py').resolve():
        raise ValueError('unqualified runtime module')
    return module.NativeCandidates, {'version': version, 'source_digests': digests}


def main(argv=None):
    parser = argparse.ArgumentParser(
        prog='qualify_primary_native_v5',
        description='PRI02-T/1 one-shot native CLI compatibility proof.')
    for name in ('runtime', 'state-dir', 'attempt-dir', 'request'):
        parser.add_argument('--' + name, required=True)
    args = parser.parse_args(argv)
    paths = {name: getattr(args, name.replace('-', '_'))
             for name in ('runtime', 'state-dir', 'attempt-dir', 'request')}
    if not all(os.path.isabs(value) for value in paths.values()):
        print('error: paths must be absolute', file=sys.stderr)
        return 2
    try:
        request = loads(Path(paths['request']).read_text(encoding='utf-8'))
        cls, binding = _load_native_candidates(paths['runtime'])
        candidates = cls(Path(paths['state-dir']))
        result = qualify(request, candidates=candidates,
                         attempt_dir=Path(paths['attempt-dir']),
                         runtime_binding=binding)
    except Exception:
        print('error: qualification failed', file=sys.stderr)
        return 2
    print(json.dumps(result, sort_keys=True, ensure_ascii=False))
    return 0 if result['status'] == 'returned_correlated_export' else 1


if __name__ == '__main__':
    raise SystemExit(main())
