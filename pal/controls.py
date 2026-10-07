"""Finite host control proposals, never target IDs or canonical mutations.

Only explicit whole-message cancel/correct forms are recognized. Target cues
are literal hints for transaction-bound resolution; unrecognized text returns
None. Correction payload is retained verbatim, apart from surrounding space.
"""
import re
import unicodedata


def literal(value):
    return ''.join(c for c in unicodedata.normalize('NFKC', value)
                   if unicodedata.category(c) != 'Cf').strip()


_TARGET = r'(?:その|(?P<cue>[\w -]{1,100})の)?(?:下書き|作業)を'
_CANCEL = re.compile(_TARGET + r'(?:止めて|中止して|停止して)[。.!]?')
_CORRECT = re.compile(_TARGET + r'訂正して')


def parse_control(text):
    if not isinstance(text, str):
        return None
    # Split only the first separator; subsequent colons belong to the payload.
    parts = re.split('[:：]', text, maxsplit=1)
    prefix = literal(parts[0])
    if len(parts) == 2:
        payload = parts[1].strip()
        match = _CORRECT.fullmatch(prefix)
        if payload and (match or prefix.casefold() == 'correct that'):
            return {'action': 'correct', 'cue': match.group('cue') if match else None,
                    'text': payload}
        return None
    if prefix.casefold() in ('stop that', 'cancel that', '止めて', '停止して'):
        return {'action': 'cancel', 'cue': None}
    match = _CANCEL.fullmatch(prefix)
    if match:
        return {'action': 'cancel', 'cue': match.group('cue')}
    return None
