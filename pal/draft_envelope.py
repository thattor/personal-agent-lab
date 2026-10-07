"""Decode untrusted task proposals; source checks and state writes belong to host.

Passing this decoder proves syntax and bounds only, never usefulness, provenance,
or Goal completion. Runtime integration is a separate reviewed boundary.
"""
import json
import re


class EnvelopeRejected(ValueError):
    pass


def validate_placeholders(content, missing):
    """Literal token consistency only, never semantic completeness."""
    def tokens(text):
        matches = set(re.findall(r'\{\{[^{}\r\n]{1,128}\}\}', text))
        remainder = re.sub(r'\{\{[^{}\r\n]{1,128}\}\}', '', text)
        if '{{' in remainder or '}}' in remainder:
            raise EnvelopeRejected('malformed placeholder')
        return matches
    if tokens(content) != tokens(missing):
        raise EnvelopeRejected('placeholder declaration mismatch')


def _pairs(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise EnvelopeRejected('duplicate envelope key')
        result[key] = value
    return result


def _constant(_):
    raise EnvelopeRejected('nonfinite JSON value')


def _text(value, limit):
    if not isinstance(value, str) or not value.strip() or '\x00' in value or value.startswith('\ufeff'):
        raise EnvelopeRejected('invalid envelope text')
    try:
        size = len(value.encode('utf-8', errors='strict'))
    except UnicodeError:
        raise EnvelopeRejected('invalid envelope unicode') from None
    if size > limit:
        raise EnvelopeRejected('envelope text exceeds bound')


def decode_draft(raw, max_bytes):
    """Return data for host validation, with no I/O or canonical authority."""
    if type(max_bytes) is not int or not 1 <= max_bytes <= 12000:
        raise ValueError('invalid draft byte bound')
    if not isinstance(raw, str):
        raise EnvelopeRejected('envelope must be JSON text')
    try:
        if len(raw.encode('utf-8', errors='strict')) > 40000:
            raise EnvelopeRejected('envelope exceeds bound')
        data = json.loads(raw, object_pairs_hook=_pairs, parse_constant=_constant)
    except (UnicodeError, json.JSONDecodeError, RecursionError):
        raise EnvelopeRejected('malformed envelope') from None
    shapes = {
        'complete': {'kind', 'content', 'citations'},
        'needs_input': {'kind', 'question', 'citations'},
        'incomplete_preview': {'kind', 'content', 'missing', 'citations'},
    }
    if not isinstance(data, dict) or not isinstance(data.get('kind'), str):
        raise EnvelopeRejected('invalid envelope kind')
    if data['kind'] not in shapes or set(data) != shapes[data['kind']]:
        raise EnvelopeRejected('invalid envelope fields')
    if data['kind'] == 'needs_input':
        _text(data['question'], 2000)
    else:
        _text(data['content'], max_bytes)
        if data['kind'] == 'incomplete_preview':
            _text(data['missing'], 2000)
    citations = data['citations']
    if not isinstance(citations, list) or len(citations) > 50:
        raise EnvelopeRejected('invalid citations')
    for citation in citations:
        if not isinstance(citation, dict) or set(citation) != {'source_id', 'quote'}:
            raise EnvelopeRejected('invalid citation fields')
        _text(citation['source_id'], 128)
        _text(citation['quote'], 2000)
    return data
