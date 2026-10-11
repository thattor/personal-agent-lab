"""Check a bounded design report; the host binds its input snapshot separately."""
import json
from pathlib import Path
import sys


def main():
    path, contract = sys.argv[1:]
    raw = Path(path).read_bytes()
    if len(raw) > 16000:
        raise ValueError('report exceeds declared bound')
    report = json.loads(raw.decode('utf-8'))
    if report.get('schema') != 'PAL.design-review/1' or report.get('contract') != contract:
        raise ValueError('unexpected report identity')
    if report.get('verdict') not in ('ALIGNED', 'REFINE', 'BLOCKED'):
        raise ValueError('missing bounded verdict')
    for name in ('value', 'responsibilities', 'contract_alignment', 'evidence_limits',
                 'findings', 'recommendation'):
        if not isinstance(report.get(name), str) or not report[name].strip():
            raise ValueError('missing report section: ' + name)
    print(json.dumps({'status': 'bounded_design_report_valid',
                      'verdict': report['verdict'], 'product_acceptance': False}))


if __name__ == '__main__':
    main()
