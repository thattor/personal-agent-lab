from pathlib import Path
import ast
import hashlib
import json
import subprocess

ROOT = Path('/private/tmp/personal-agent-lab-stable0-20261006')
OUT = Path(__file__).resolve().parent
OLD = ROOT / 'evidence/research/multimodal/2026-10-08/design-v1'
REV = OUT / 'reviews'
REV.mkdir(exist_ok=True)

def git(*args):
    return subprocess.check_output(['git', *args], cwd=ROOT)

head = git('rev-parse', 'HEAD').decode().strip()
parts = []
selections = {
    'pal/store.py': ['_dedupe', 'prepare_primary', '_finish_primary_outcome', '_usable', 'stored_reply', 'operation'],
    'pal/runtime.py': ['submit'],
}
for filename, names in selections.items():
    source = git('show', f'{head}:{filename}').decode()
    lines = source.splitlines()
    nodes = [n for n in ast.walk(ast.parse(source)) if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef)) and n.name in names]
    assert {n.name for n in nodes} == set(names)
    for n in sorted(nodes, key=lambda n: n.lineno):
        parts.append(f'### {filename}:{n.lineno} {n.name}\n```python\n' + '\n'.join(lines[n.lineno-1:n.end_lineno]) + '\n```')
source_text = '\n\n'.join(parts)
(REV / 'source-excerpts.md').write_text(source_text)
design = (OLD / 'DESIGN.md').read_text()
bridge = (OUT / 'BRIDGE-PLAN.md').read_text()
intro = '''You are the official SWE-2 High implementation-design reviewer. Review supplied material only; do not invoke tools, read files, spawn agents, execute commands, or implement code. This is future PAL multimodal design, not a runtime/model qualification.

The owner explicitly requests continuation of the previous incomplete SWE review. The previous 600-second response was cut mid-note; do not pretend to recover unseen words. Review the corrected design now. Previous blockers: B1 media reservation incorrectly could occupy dedupe; B2 plain-text replay could return media primary outcome. The supplied current design now reserves only media_inputs, checks all _dedupe paths plus prepare_primary's early return, admits atomically under original key, stores immutable media-v1: prefixed ingress hash, and leaves _finish_primary_outcome as dedupe primary writer including recovery. Notes 1-8 (duplicate JSON keys, image_ref route, input-specific blobs, CAS affected-row check, host ASR/request binding, no raw audit TTS, whole-playback failure, bounded decoder) were addressed. Note 9 was cut during slot-exhaustion guidance; controller added fail-closed slot loss and bounded queue termination. Inspect whether these fixes are sufficient and whether the design contains any remaining concrete implementation blockers.

Current owner scope: current release is TEXT ONLY; multimodal belongs to next version. Design preparation and concrete bridge milestones/issues are authorized now, implementation stays deferred. Keep exact reference models, no exploration. Existing P001v2 is not adopted; NEXT plan must not activate it. All 30 product cases remain NOT_RUN. The bridge plan adds issue/dependency/exit tracking, not code or approval to install/connect/pay.

Answer COMPLETELY and CONCISELY in Japanese, at most 1800 Japanese characters. Required structure: (1) verdict for future design handoff, (2) B1/B2/note9 resolved or exact residual hole, (3) at most three actual blockers with precise smallest correction and acceptance case, or 'なし', (4) bridge dependency/test evidence caveat if needed, (5) explicit unverified runtime limits. End with literal REVIEW_COMPLETE. Prefer finite relevant findings to a long checklist. Do not require owner choices for inferable technical methods. Do not change current release acceptance or treat review as implementation proof. If evidence is insufficient, name the missing supplied fact rather than using tools. This is one bounded 600-second attempt without retry/fallback.
'''
prompt = intro + '\n## Corrected design v1\n' + design + '\n## Proposed bridge plan v2\n' + bridge + '\n## Current exact-source excerpts\n' + source_text
(REV / 'swe-question.txt').write_text(prompt)
frozen = {'source_head': head, 'source_files': {}, 'inputs': {}, 'prompt_bytes': len(prompt.encode()), 'scope': 'supplied-document review only; no implementation; current release text-only'}
for path in git('ls-files', 'pal').decode().splitlines():
    body = git('show', f'{head}:{path}')
    frozen['source_files'][path] = hashlib.sha256(body).hexdigest()
for path in [OLD/'DESIGN.md', OLD/'CONTRACT-EXAMPLES.json', OLD/'ACCEPTANCE.json', OUT/'BRIDGE-PLAN.md', REV/'source-excerpts.md', REV/'swe-question.txt']:
    frozen['inputs'][str(path)] = {'sha256': hashlib.sha256(path.read_bytes()).hexdigest(), 'bytes': path.stat().st_size}
(REV / 'input-freeze.json').write_text(json.dumps(frozen, ensure_ascii=False, indent=2)+'\n')
print(json.dumps({'head':head,'prompt_bytes':len(prompt.encode()),'source_excerpt_bytes':len(source_text.encode()),'product_files':len(frozen['source_files'])}))
