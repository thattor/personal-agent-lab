from pathlib import Path
import datetime
import hashlib
import json
import os
import signal
import subprocess
import time

ROOT=Path('/private/tmp/personal-agent-lab-stable0-20261006')
BASE=Path(__file__).resolve().parent
OUT=BASE/'reviews'
CLI='/Users/hattoritoshiyasu/.local/bin/claude'
env=dict(os.environ)
for key in ['ANTHROPIC_API_KEY','ANTHROPIC_AUTH_TOKEN','ANTHROPIC_BASE_URL','CLAUDE_CODE_OAUTH_TOKEN','CLAUDE_CODE_USE_BEDROCK','CLAUDE_CODE_USE_VERTEX','CLAUDE_CODE_USE_FOUNDRY']:
    env.pop(key,None)
auth=subprocess.run([CLI,'auth','status'],cwd=ROOT,env=env,capture_output=True,timeout=30)
data=json.loads(auth.stdout)
assert auth.returncode == 0 and data.get('loggedIn') and data.get('authMethod')=='claude.ai' and data.get('apiProvider')=='firstParty' and data.get('subscriptionType')=='pro'
access={'checked_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'auth':'existing official Claude Pro / claude.ai / firstParty','fresh_ui_source':'CUA Chrome tab 172833039 at claude.ai/new#settings/usage, observed this turn before this call','usage_ui':{'plan':'Pro','session_used_percent':6,'weekly_used_percent':27,'extra_usage_switch':0,'extra_usage_amount':'$0','auto_reload':'OFF'},'tools':[],'mcpServers':{},'safe_mode':True,'max_turns':1,'max_seconds':240,'paid_fallback':False,'authority':'Repository Opus design-partner requirement and owner continuation/next-version planning instruction'}
(OUT/'opus-access.json').write_text(json.dumps(access,ensure_ascii=False,indent=2)+'\n')
intro='''あなたはPALの独立したOpus設計パートナーです。同封資料だけを読み、ツール/MCP/ファイル操作/委任/実装をしないでください。今回は次バージョンの具体的な接続計画の設計レビューです。本人は現行版テキストのみ、マルチモーダルは次版、今は設計準備を進める、途中のSWEレビューは継続、人間固有判断だけ人間チャットへ、と既に明示しました。この方針を再承認待ちにしないでください。
既存設計v1には詳細な閉じたmedia API、入力別BLOB、MediaInputの状態CAS、client_keyのmedia予約/不変media-v1 hash/原子的admit/dedupe終端記録、host-only権限、source再帰参照停止、実QwenとASR/TTS境界、停止/boot/epoch制御があり、30評価ケースは全てNOT_RUNです。元のOpus詳細レビューをcontrollerが反映し、部分SWEのB1/B2とノートも修正しました。現在SWEはこの修正版の実装設計レビューを別途実行中。SWE完了前にMM0を閉じるつもりはありません。
現行Stable-1/P002/D029が唯一のACTIVE実装。N1-01–10と本人総合評価/最終監査の条件は維持。P001v2は未採用であり、本計画から採用しません。既存7milestone/12issueには専用multimodal計画がありませんでした。共有repo/GitHubはPAL開発だけが書き、本チャットは準備資料を渡します。
質問: 下記の計画は、現行開発を止めず、将来設計を具体的に一区切りにし、レビュー/計画/実装/実測の混同を防ぐ最小十分な接続計画か。MM0–4の依存/出口、部分host試験と全30ケース、次版activationと不要な人間gate、videoを今回対象外にする説明をchallengeしてください。新しいモデル探索や機能追加は不要です。必要な技術修正を最大3件、正確な箇所と最小修正文で示すか『なし』としてください。今回の製品PASS/実機測定は一切ありません。
1800字以内の日本語で、結論→blocker/修正→採用可能な範囲→未検証の順に完結させ、最後は REVIEW_COMPLETE と書いてください。レビューの完了を製品完成と取り違えないでください。
'''
question=intro+'\n'+(BASE/'OWNER-INSTRUCTION.md').read_text()+'\n'+(BASE/'BRIDGE-PLAN.md').read_text()
(OUT/'opus-question.txt').write_text(question)
(OUT/'opus-input-freeze.json').write_text(json.dumps({'prompt_sha256':hashlib.sha256(question.encode()).hexdigest(),'prompt_bytes':len(question.encode()),'bridge_sha256':hashlib.sha256((BASE/'BRIDGE-PLAN.md').read_bytes()).hexdigest()},indent=2)+'\n')
cmd=[CLI,'-p','--model','opus','--permission-mode','plan','--safe-mode','--tools','','--strict-mcp-config','--mcp-config','{"mcpServers":{}}','--disable-slash-commands','--max-turns','1','--no-session-persistence','--output-format','text']
started=time.monotonic()
timeout=False
with (OUT/'opus-question.txt').open('rb') as stdin,(OUT/'opus-response.txt').open('wb') as stdout,(OUT/'opus-stderr.txt').open('wb') as stderr:
    process=subprocess.Popen(cmd,cwd=ROOT,env=env,stdin=stdin,stdout=stdout,stderr=stderr,start_new_session=True)
    try:process.wait(timeout=240)
    except subprocess.TimeoutExpired:
        timeout=True
        os.killpg(process.pid,signal.SIGTERM)
        try:process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            os.killpg(process.pid,signal.SIGKILL)
            process.wait()
answer=(OUT/'opus-response.txt').read_bytes()
result={'finished_at':datetime.datetime.now(datetime.timezone.utc).isoformat(),'elapsed_seconds':round(time.monotonic()-started,3),'exit_code':process.returncode,'timeout':timeout,'response_bytes':len(answer),'stderr_bytes':(OUT/'opus-stderr.txt').stat().st_size,'response_sha256':hashlib.sha256(answer).hexdigest(),'response_complete':process.returncode==0 and not timeout and answer.rstrip().endswith(b'REVIEW_COMPLETE'),'attempts':1,'fallback':False}
(OUT/'opus-completion.json').write_text(json.dumps(result,indent=2)+'\n')
print(json.dumps(result),flush=True)
