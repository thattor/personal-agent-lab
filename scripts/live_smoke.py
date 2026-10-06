"""One explicitly authorized official-provider smoke, synthetic input only."""
import hashlib
import json
import platform
import sqlite3
import subprocess
import sys
import time
from datetime import datetime,timezone
from pathlib import Path

sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from pal.native import NativeClaude,AccessProof
from pal.runtime import Runtime


def main():
    proof_data=json.loads(Path(sys.argv[1]).read_text())
    provider=NativeClaude(AccessProof(proof_data['verified_at'],proof_data['no_extra_charge']))
    started=datetime.now(timezone.utc).isoformat()
    output=Path(sys.argv[2])
    output.mkdir(parents=True,exist_ok=True)
    runtime=Runtime(output/'smoke.db',provider=provider)
    try:
        normal=runtime.submit('live-normal','Hello. Reply briefly about our synthetic stationery exercise.')
        normal_response=normal['response'].result(timeout=150)
        assert normal['goal'] is None
        assert 'provider unavailable' not in normal_response['content'].lower(),normal_response
        limited=runtime.submit('live-limit','Record only: make a draft later. Do not start work now.')
        limited_response=limited['response'].result(timeout=150)
        assert limited['goal'] is None
        assert 'provider unavailable' not in limited_response['content'].lower(),limited_response
        assert runtime.store.inspect()['goals']==[]
        draft=runtime.submit('live-draft','Make a draft of three sentences inviting a fictional colleague to discuss synthetic apples. Keep it local, do not send. Output only draft text.')
        draft['response'].result(timeout=10)
        assert runtime.idle.wait(150)
        goal=runtime.store.get_goal(draft['goal']['id'])
        assert goal['state']=='completed',goal
        data=runtime.store.inspect()
        receipt=data['receipts'][0]
        body=runtime.store.artifact(receipt['artifact_id'])
        assert hashlib.sha256(body).hexdigest()==receipt['hash']
        assert b'<invoke' not in body.lower(), 'Native route leaked planning/tool transcript into draft'
        assert data['outcomes'][0]['check_status']=='pass'
        (output/'draft.txt').write_bytes(body)
        (output/'language.json').write_text(json.dumps({'normal':normal_response,'explicit_record_only':limited_response,'draft_request':draft['goal'],'final_goal':goal},indent=2,ensure_ascii=False)+'\n')
        (output/'host-evidence.json').write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
        version=subprocess.run([provider.command()[0],'--version'],capture_output=True,text=True,timeout=10).stdout.strip()
        record={'status':'PASS','started_at':started,'ended_at':datetime.now(timezone.utc).isoformat(),'provider':provider.identity,'model_requested':'opus','actual_model_version':'not reported by text output','adapter':'pal/native.py + pal/native_supervisor.py','native_cli_version':version,'python':platform.python_version(),'sqlite':sqlite3.sqlite_version,'live_calls':3,'capabilities':{'model_tools':[],'mcp':[],'customizations':'safe-mode','canonical_store_access':False,'paid_fallback':False,'session_persistence':False},'cost_verification':proof_data,'host_receipt':receipt,'host_checks':['fixed_local_draft_criteria','UTF8','nonempty','max4096bytes','hash_readback','current_revision_epoch','usable_source_manifest'],'quality_claim':'none','normal_conversation_goal_count':0,'draft_goal_count':len(data['goals'])}
        (output/'result.json').write_text(json.dumps(record,indent=2)+'\n')
        print(json.dumps({'status':'PASS','provider':provider.identity,'goal_state':goal['state'],'hash':receipt['hash']}))
    finally:
        runtime.close()


if __name__=='__main__':
    main()
