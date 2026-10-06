"""Watch the host lifetime pipe; reap the native process group on any exit.

No canonical state or credentials are passed here. Output is capped before it is
forwarded. The supervisor survives host SIGKILL long enough to kill/reap children.
"""
import json
import os
import selectors
import signal
import subprocess
import sys
import time
from sanitize import sanitize


def main():
    control_fd, timeout, cap = int(sys.argv[1]), float(sys.argv[2]), int(sys.argv[3])
    command = json.loads(sys.argv[4])
    process = None

    def stop(*args):
        if process is not None:
            try:
                os.killpg(process.pid, signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=5)
        raise SystemExit(2)

    signal.signal(signal.SIGTERM, stop)
    signal.signal(signal.SIGINT, stop)
    request = sys.stdin.buffer.read(131073)
    if len(request) > 131072:
        return 2
    try:
        process = subprocess.Popen(command, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE, start_new_session=True, close_fds=True)
        process.stdin.write(request)
        process.stdin.close()
        selector = selectors.DefaultSelector()
        selector.register(control_fd, selectors.EVENT_READ, 'control')
        selector.register(process.stdout, selectors.EVENT_READ, 'stdout')
        selector.register(process.stderr, selectors.EVENT_READ, 'stderr')
        output = bytearray()
        stderr_size = 0
        stderr_buffer = bytearray()
        deadline = time.monotonic() + timeout
        open_streams = 2
        while open_streams:
            if time.monotonic() >= deadline:
                stop()
            for key, _ in selector.select(min(.1, max(0, deadline-time.monotonic()))):
                chunk = os.read(key.fd, 4096)
                if key.data == 'control':
                    stop()  # EOF or explicit host shutdown signal
                elif not chunk:
                    selector.unregister(key.fileobj)
                    open_streams -= 1
                elif key.data == 'stdout':
                    output.extend(chunk)
                    if len(output) > cap:
                        stop()
                else:
                    stderr_size += len(chunk)
                    stderr_buffer.extend(chunk)
                    if stderr_size > cap:
                        stop()
        result = process.wait(timeout=max(.1,deadline-time.monotonic()))
        if result != 0:
            sys.stderr.write("native_returncode=" + str(result) + "\n")
            sys.stderr.write(sanitize(stderr_buffer.decode("utf-8",errors="replace"))[:2000])
            sys.stderr.write("\nSanitized failed stdout: " + sanitize(output.decode("utf-8",errors="replace"))[:2000])
            return 2
        sys.stdout.buffer.write(output)
        return 0
    finally:
        if process is not None:
            try:
                os.killpg(process.pid,signal.SIGKILL)
            except ProcessLookupError:
                pass
            process.wait(timeout=5)
            for stream in (process.stdin,process.stdout,process.stderr):
                if stream and not stream.closed:
                    stream.close()


if __name__ == '__main__':
    sys.exit(main())
