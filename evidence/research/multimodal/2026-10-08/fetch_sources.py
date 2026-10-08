"""Capture selected public research sources without executing downloaded code."""
import concurrent.futures
import datetime
import hashlib
import json
from pathlib import Path
import sys
import urllib.request

ROOT = Path(__file__).resolve().parent
REPOS = ['QwenLM/Qwen-Live-Harness', 'QwenLM/Qwen-MM-Plugins',
         'open-webui/open-webui', 'livekit/agents', 'immich-app/immich']

def get(url):
    request = urllib.request.Request(url, headers={'User-Agent': 'PAL-read-only-research', 'Accept': 'application/vnd.github+json'})
    with urllib.request.urlopen(request, timeout=35) as response:
        return response.read()

def inventory(repo):
    out = ROOT / 'sources' / repo.replace('/', '__')
    out.mkdir(parents=True, exist_ok=True)
    metadata = json.loads(get('https://api.github.com/repos/' + repo))
    commit = json.loads(get('https://api.github.com/repos/' + repo + '/commits/' + metadata['default_branch']))
    tree = json.loads(get('https://api.github.com/repos/' + repo + '/git/trees/' + commit['sha'] + '?recursive=1'))
    record = {'repo': repo, 'sha': commit['sha'], 'commit_date': commit['commit']['committer']['date'],
              'retrieved_at': datetime.datetime.now(datetime.timezone.utc).isoformat(),
              'license': metadata.get('license'), 'default_branch': metadata['default_branch'],
              'tree_truncated': tree.get('truncated', False)}
    (out / 'metadata.json').write_text(json.dumps(record, ensure_ascii=False, indent=2) + '\n')
    (out / 'tree.json').write_text(json.dumps(tree, ensure_ascii=False, indent=2) + '\n')
    return record

def capture(repo, path):
    out = ROOT / 'sources' / repo.replace('/', '__')
    metadata = json.loads((out / 'metadata.json').read_text())
    url = 'https://raw.githubusercontent.com/' + repo + '/' + metadata['sha'] + '/' + path
    data = get(url)
    target = out / 'files' / path
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(data)
    entry = {'repo': repo, 'sha': metadata['sha'], 'path': path, 'url': url,
             'sha256': hashlib.sha256(data).hexdigest(), 'bytes': len(data)}
    return entry

if __name__ == '__main__':
    if sys.argv[1] == 'inventory':
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
            for repo, result in zip(REPOS, pool.map(inventory, REPOS)):
                print(json.dumps(result, ensure_ascii=False), flush=True)
    elif sys.argv[1] == 'capture':
        items = json.loads((ROOT / 'selected-files.json').read_text())
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
            receipts = list(pool.map(lambda item: capture(item['repo'], item['path']), items))
        (ROOT / 'source-receipts.json').write_text(json.dumps(receipts, ensure_ascii=False, indent=2) + '\n')
        for entry in receipts:
            print(json.dumps(entry, ensure_ascii=False), flush=True)
