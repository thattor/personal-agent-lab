"""Validate a bounded design report; no implementation acceptance is implied."""
import hashlib
import json
from pathlib import Path
import sys


def main():
    report = json.loads(Path(sys.argv[1]).read_text())
    if report.get('schema') != 'PAL.CHANGE01.milestone-review/1':
        raise ValueError('unexpected report schema')
    if report.get('verdict') not in ('ALIGNED', 'REFINE', 'BLOCKED'):
        raise ValueError('missing bounded verdict')
    if report.get('contract') != 'CHANGE01/1':
        raise ValueError('unexpected contract')
    if report.get('source_sha256') != '498b06ca6033c980bfdfe24b54195f247dbc7a46d267c67a1a54b0028f5c3e8f':
        raise ValueError('unexpected source identity')
    for name in ('value', 'responsibilities', 'contract_alignment', 'evidence_limits',
                 'findings', 'next_dependency'):
        if not isinstance(report.get(name), str) or not report[name].strip():
            raise ValueError('missing report section: ' + name)
    hashes = report.get('input_sha256')
    required = ('docs/design/contracts-v5/CHANGE01-SCOPE.md',
                'docs/design/contracts-v5/CHANGE01-OWNER-EXCERPTS.md',
                'docs/design/contracts-v5/CHANGE01-MILESTONE.md')
    if not isinstance(hashes, dict):
        raise ValueError('missing input hashes')
    for name in required:
        if hashes.get(name) != hashlib.sha256(Path(name).read_bytes()).hexdigest():
            raise ValueError('input identity mismatch: ' + name)
    print(json.dumps({'status': 'report_schema_and_input_hashes_valid',
                      'verdict': report['verdict'], 'product_acceptance': False}))


if __name__ == '__main__':
    main()
