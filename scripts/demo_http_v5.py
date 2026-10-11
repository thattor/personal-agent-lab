"""Run the disposable, loopback-only PAL v5 mock example; no provider calls."""
from pathlib import Path
import sys
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pal.http_v5 import LocalMockApp,create_server

def main():
    app=LocalMockApp();server=create_server(app)
    print('Mock-only fixed example: http://127.0.0.1:'+str(server.server_port),flush=True)
    try:server.serve_forever()
    except KeyboardInterrupt:pass
    finally:
        server.server_close()
        closed=app.close()
        if not closed:print('Shutdown incomplete; owned mock work and data remain held.',file=sys.stderr)
    return 0 if closed else 1

if __name__=='__main__':sys.exit(main())
