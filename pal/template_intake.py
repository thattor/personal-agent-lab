"""Conservative host eligibility grammar, never model authority or completeness."""
import re
import unicodedata


def has_unresolved_markers(content):
    """Reserved template marker floor only; do not normalize stored bytes."""
    folded = unicodedata.normalize('NFKC', content)
    return '＿＿' in content or any(marker in folded for marker in ('{{', '}}', '___'))


def allows_preview(specification):
    cue = re.search(r'\b(?:template|blank form)\b|テンプレート|ひな形|雛形', specification, re.IGNORECASE)
    marker = re.search(r'\{\{[^{}\r\n]{1,128}\}\}|___|＿＿', specification)
    return bool(cue and marker)
