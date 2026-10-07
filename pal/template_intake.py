"""Conservative host eligibility grammar, never model authority or completeness."""
import re


def allows_preview(specification):
    cue = re.search(r'\b(?:template|blank form)\b|テンプレート|ひな形|雛形', specification, re.IGNORECASE)
    marker = re.search(r'\{\{[^{}\r\n]{1,128}\}\}|___|＿＿', specification)
    return bool(cue and marker)
