"""Sanitize before persistence or provider context. Deliberately not perfect detection."""
import re

_PATTERNS = (
    re.compile(r'-----BEGIN [^-]*PRIVATE KEY-----.*?-----END [^-]*PRIVATE KEY-----', re.S),
    re.compile(r'\b(?:sk|ghp|github_pat)-?[A-Za-z0-9_]{16,}\b'),
    re.compile(r'(?i)\bBearer\s+[A-Za-z0-9._~+/-]+=*'),
    re.compile(r'(?i)\b(?:api[_ -]?key|token|password|secret)\s*[:=]\s*[^\s,;]+'),
)


def sanitize(value):
    if isinstance(value, str):
        for pattern in _PATTERNS:
            value = pattern.sub('[REDACTED]', value)
        return value
    if isinstance(value, dict):
        return {str(k): sanitize(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [sanitize(v) for v in value]
    return value
