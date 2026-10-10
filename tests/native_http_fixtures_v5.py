"""Typed synthetic Claude provider for disposable native HTTP tests; no CLI."""
import copy
import json
import uuid
import native_claude_fixtures_v5 as claude


class Provider:
    fixture_only = True

    def __init__(self, behavior=None):
        self.profile = claude.profile()
        self.behavior = behavior
        self.requests = []
        self.preflights = 0

    def preflight(self):
        self.preflights += 1
        return {'fixture_only': True}

    def invoke(self, request, *, on_enter):
        self.requests.append(copy.deepcopy(request))
        attempt = {'run_id': 'http-fixture', 'job_id': request['role'],
                   'attempt_id': str(uuid.uuid4())}
        on_enter(attempt)
        output = self.behavior(request) if self.behavior else primary(request)
        if type(output) is not str:
            output = json.dumps(output, ensure_ascii=False)
        return claude.returned(request, self.profile, output, attempt)


def context(request):
    return json.loads(request['messages'][1]['text'])


def primary(request, *, new=False):
    proposal = {'kind': 'none'}
    if new:
        proposal = {'kind': 'new_work', 'brief': {
            'purpose': 'synthetic saved draft',
            'target': {'repository': 'demo', 'issue_numbers': [], 'files': []},
            'constraints': ['no sending'], 'conditions': [
                {'description': 'saved draft', 'check': 'artifact_saved'}], 'context_refs': []}}
    return {'reply': 'fixture receipt', 'proposal': proposal}


def compose(request, text='SYNTHETIC_SAVED_BODY'):
    return {'kind': 'compose', 'content': text, 'media_type': 'text/plain',
            'source_refs': request['source_refs']}
