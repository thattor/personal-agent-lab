"""Reproduce READ01's local before/after assertions and retained demo evidence."""
from pathlib import Path
import argparse
import json

from demo_readback_v5 import run_demo, render


def verify_demo():
    demo = run_demo()
    first, later = demo['before']['items'][0], demo['after']['items'][0]
    assert first['work']['value']['state'] == later['work']['value']['state'] == 'completed'
    before = next(x for x in first['reads'] if x['ref']['kind'] == 'verification')
    after = next(x for x in later['reads'] if x['ref']['kind'] == 'verification')
    assert before['validity'] == 'current' and after['validity'] == 'source stopped'
    assert before['result']['value']['content'] == after['result']['value']['content']
    assert before['result']['value']['hash'] == after['result']['value']['hash']
    notices = [x for x in demo['after']['items'] if x['event']['kind'] == 'progress']
    assert len(notices) == 1
    assert notices[0]['reads']
    assert all(x['result']['ok'] and x['result']['value']['usable'] is False
               for x in notices[0]['reads'])
    return demo


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output-dir', type=Path, required=True)
    destination = parser.parse_args().output_dir
    destination.mkdir(parents=True, exist_ok=True)
    demo = verify_demo()
    (destination / 'demo.json').write_text(json.dumps(demo, ensure_ascii=False, indent=2) + '\n')
    (destination / 'demo.log').write_text(
        'Local temporary SQLite, mock model, structural verification.\n\nBefore source stop\n'
        + render(demo['before']) + '\nAfter source stop\n' + render(demo['after']) + '\n')
    print('PASS: completed history, immutable verification hash, current usability and stopped record notice')
