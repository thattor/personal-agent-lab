"""Loopback conversation and strictly read-only inspect UI; no external exposure."""
import argparse
import json
import signal
import threading
from http.server import BaseHTTPRequestHandler,ThreadingHTTPServer
from pathlib import Path
from urllib.parse import urlsplit,unquote

from .runtime import Runtime,MockProvider
from .native import NativeClaude,AccessProof

_WEB=Path(__file__).resolve().parent/'web'


def make_server(runtime,port=8765):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args):
            pass  # Do not log request bodies, account identifiers, or raw error text.

        def send(self,status,body,content_type='application/json; charset=utf-8'):
            if isinstance(body,dict):
                body=json.dumps(body,ensure_ascii=False).encode()
            elif isinstance(body,str):
                body=body.encode()
            self.send_response(status)
            self.send_header('Content-Type',content_type)
            self.send_header('Content-Length',str(len(body)))
            self.send_header('Cache-Control','no-store')
            self.send_header('X-Content-Type-Options','nosniff')
            self.send_header('X-Frame-Options','DENY')
            self.send_header('Content-Security-Policy',"default-src 'self'; script-src 'self'; style-src 'self'; object-src 'none'; frame-ancestors 'none'; base-uri 'none'; form-action 'self'")
            self.end_headers()
            self.wfile.write(body)

        def allowed(self,post=False):
            expected=f'127.0.0.1:{self.server.server_port}'
            if self.headers.get('Host')!=expected:
                self.send(403,{'error':'unexpected host'})
                return False
            if post and self.headers.get('Origin')!='http://'+expected:
                self.send(403,{'error':'unexpected origin'})
                return False
            return True

        def do_GET(self):
            if not self.allowed():
                return
            route=urlsplit(self.path).path
            files={'/':'conversation.html','/inspect':'inspect.html','/app.js':'app.js','/style.css':'style.css'}
            if route in files:
                path=_WEB/files[route]
                mime={'html':'text/html; charset=utf-8','js':'text/javascript; charset=utf-8','css':'text/css; charset=utf-8'}[path.suffix[1:]]
                self.send(200,path.read_bytes(),mime)
            elif route.startswith('/api/operation/'):
                key=unquote(route[len('/api/operation/'):])
                if not key or len(key)>200:
                    self.send(400,{'error':'invalid operation key'})
                else:
                    self.send(200,runtime.store.operation(key))
            elif route=='/api/health':
                self.send(200,runtime.health())
            elif route=='/api/state':
                self.send(200,dict(runtime.store.inspect(),selections=runtime.store.selections(),provider=runtime.provider.identity,provider_status=runtime.provider.status() if hasattr(runtime.provider,'status') else {'mode':'mock'},runtime=runtime.health()))
            elif route.startswith('/api/artifact_status/'):
                try:
                    self.send(200,runtime.store.artifact_status(route.rsplit('/',1)[-1]))
                except ValueError:
                    self.send(404,{'error':'unknown artifact'})
            elif route.startswith('/api/artifact/'):
                try:
                    self.send(200,runtime.store.artifact(route.rsplit('/',1)[-1]),'text/plain; charset=utf-8')
                except ValueError:
                    self.send(404,{'error':'unknown artifact'})
            else:
                self.send(404,{'error':'unknown route'})

        def do_POST(self):
            if not self.allowed(post=True):
                return
            if self.path!='/api/message':
                self.send(405,{'error':'inspect and artifacts are read-only'})
                return
            if self.headers.get('Transfer-Encoding') or self.headers.get('Content-Type')!='application/json':
                self.send(400,{'error':'JSON with bounded Content-Length required'})
                return
            try:
                size=int(self.headers.get('Content-Length','0'))
            except ValueError:
                size=0
            if not 0<size<=65536:
                self.send(413,{'error':'request size bound'})
                return
            try:
                payload=json.loads(self.rfile.read(size))
                if not isinstance(payload,dict) or not {'key','text'}<=set(payload) or not set(payload)<={'key','text','goal_id','control'}:
                    raise ValueError('invalid message contract')
                result=runtime.submit(**payload)
                self.send(202,{k:v for k,v in result.items() if k!='response'})
            except (ValueError,TypeError,RuntimeError):
                self.send(400,{'error':'message rejected; check current state or request fields'})

        def do_PUT(self):
            self.send(405,{'error':'unsupported method'})
        do_DELETE=do_PUT
        do_PATCH=do_PUT

    server=ThreadingHTTPServer(('127.0.0.1',port),Handler)
    server.daemon_threads=True
    return server


def build_provider(args, marker_dir=Path('runtime/native-proof-use')):
    session_seconds=getattr(args,'native_session_seconds',None)
    if args.provider=='mock':
        if args.access_proof is not None or args.native_call_limit is not None or session_seconds is not None:
            raise ValueError('native options require explicit official provider')
        return MockProvider(args.mock_task_delay)
    if args.provider!='official_claude_pro' or not args.access_proof or args.mock_task_delay:
        raise ValueError('explicit official provider requires proof and no mock delay')
    limit=16 if args.native_call_limit is None else args.native_call_limit
    provider=NativeClaude(AccessProof.load(args.access_proof),max_calls=limit,
                          session_seconds=900 if session_seconds is None else session_seconds)
    provider.proof.consume(marker_dir)
    return provider


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--db',default='runtime/pal.db')
    parser.add_argument('--port',type=int,default=8765)
    parser.add_argument('--mock-task-delay',type=float,default=0,help='bounded mock execution latency for control/recovery exercises')
    parser.add_argument('--provider',choices=('mock','official_claude_pro'),default='mock')
    parser.add_argument('--access-proof',help='operator-issued fresh official no-extra-charge metadata JSON')
    parser.add_argument('--native-call-limit',type=int,help='bounded generation invocations, 1..32 (default16)')
    parser.add_argument('--native-session-seconds',type=int,help='explicit finite admission window, 1..8100 seconds (default900); startup proof must be fresh within900 seconds')
    args=parser.parse_args()
    try:
        provider=build_provider(args)
    except (ValueError,RuntimeError,OSError) as error:
        parser.error(str(error))
    runtime=Runtime(args.db,provider=provider)
    server=make_server(runtime,args.port)
    def stop(*_):
        threading.Thread(target=server.shutdown,daemon=True).start()
    signal.signal(signal.SIGTERM,stop)
    signal.signal(signal.SIGINT,stop)
    print(f'PAL {provider.identity} conversation: http://127.0.0.1:{server.server_port}',flush=True)
    try:
        server.serve_forever()
    finally:
        server.server_close()
        runtime.close()


if __name__=='__main__':
    main()
