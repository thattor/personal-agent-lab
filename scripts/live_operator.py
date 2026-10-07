"""Explicit finite official-provider operator; no keepalive or paid fallback.

Run with python3 -m scripts.live_operator. Stdin commands observe an owned UI
session; they never attest that synthetic inputs were entered by a human.
"""
import argparse
import json
import signal
import subprocess
import sys
import time
from pathlib import Path

from pal.native import AccessProof, NativeClaude, native_environment
from scripts.live_runner import MatrixRunner


def git_read(root, *arguments):
    result = subprocess.run(['git',*arguments],cwd=root,capture_output=True,
                            text=True,check=True,timeout=10)
    return result.stdout.strip()


def clean_candidate(root, candidate):
    if git_read(root,'rev-parse','HEAD') != candidate:
        raise ValueError('candidate does not match HEAD')
    if git_read(root,'status','--porcelain'):
        raise ValueError('candidate checkout is dirty')


class AuditedNative(NativeClaude):
    def __init__(self, proof, max_calls=20):
        super().__init__(proof,max_calls=max_calls)
        self.sink = None
        self.initial_slots = max_calls
        self._observed_phase = 'not_started'
        self._operator_ready = False
        self._runner_claimed = False
        self._frozen_command = None

    def command(self):
        command = super().command()
        if self._frozen_command is not None and command!=self._frozen_command:
            raise ValueError('native command drift')
        return command

    def _auth_command(self):
        self._observed_phase = 'auth'
        return super()._auth_command()

    def register(self, process, control_fd):
        super().register(process,control_fd)
        if self.sink is not None:
            with self._lock:
                slot = self.initial_slots-self._remaining
            self.sink({'event':'native.supervisor.started',
                       'supervisor_pid':process.pid,'phase':self._observed_phase,
                       'native_slot_attempt':slot,'monotonic':time.monotonic()})
        # The next supervisor in this single serial call is generation. This
        # records the actual supervisor, never invents a CLI grandchild PID.
        self._observed_phase = 'generation'

    def unregister(self, process):
        super().unregister(process)
        if self.sink is not None:
            self.sink({'event':'native.supervisor.finished',
                       'supervisor_pid':process.pid,'returncode':process.returncode,
                       'monotonic':time.monotonic()})


def build_live(root, directory, proof_path, candidate):
    root = Path(root).resolve()
    directory = Path(directory).resolve()
    # Preserve every run. Do not recover/resume an earlier directory.
    directory.relative_to(root/'runtime')
    clean_candidate(root,candidate)
    proof = AccessProof.load(proof_path)
    owner = AuditedNative(proof,max_calls=20)
    command = owner.command()
    owner._frozen_command = list(command)
    version = subprocess.run([command[0],'--version'],capture_output=True,text=True,
                             check=True,timeout=10,env=native_environment())
    if len(version.stdout.encode('utf-8'))>4096:
        raise ValueError('CLI version output bound')
    proof.check()
    # Same one-use directory as pal.server; cannot reuse a consumed proof by
    # selecting a different case or run directory.
    proof.consume(root/'runtime/native-proof-use')
    owner._operator_ready = True
    runner = MatrixRunner(root,directory,root/'tests/fixtures/p002_real_ui_v1.json',
                          owner,scope='live_synthetic',candidate=candidate)
    try:
        owner.sink = runner.journal.append
        runner.journal.append({'event':'operator.config','command':command,
                              'cli_version':version.stdout.strip(),
                              'python_version':sys.version,'provider_identity':owner.identity,
                              'access_proof':{'verified_at':proof.verified_at,
                                              'route':proof.route,'no_extra_charge':True},
                              'native_slots':20,'human_evaluation':False})
    except BaseException:
        runner.close()
        raise
    return runner


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--run-directory',required=True)
    parser.add_argument('--access-proof',required=True)
    parser.add_argument('--candidate',required=True)
    args = parser.parse_args()
    root = Path(__file__).resolve().parents[1]
    runner = build_live(root,args.run_directory,args.access_proof,args.candidate)
    def interrupted(signum, frame):
        raise SystemExit('operator interrupted')
    signal.signal(signal.SIGTERM,interrupted)
    signal.signal(signal.SIGINT,interrupted)
    try:
        print(json.dumps({'ready':True,'scope':'live_synthetic','human_evaluation':False}),flush=True)
        for line in sys.stdin:
            request = json.loads(line)
            if request == {'action':'next'}:
                result = runner.start_next()
            elif request == {'action':'capture'}:
                result = runner.capture(timeout=140)
            elif set(request)=={'action','rationale','browser_observation'} and request['action']=='accept':
                runner.accept_case(request['rationale'],request['browser_observation'])
                result = {'accepted':runner.case['id'],'human_evaluation':False}
            elif request == {'action':'finish'}:
                print(json.dumps(runner.finish(),ensure_ascii=False),flush=True)
                return
            else:
                raise ValueError('unsupported operator command')
            print(json.dumps(result,ensure_ascii=False),flush=True)
    finally:
        runner.close()


if __name__=='__main__':
    # Use the canonical module identity for the exact audited-owner type gate.
    from scripts.live_operator import main as entry
    entry()
