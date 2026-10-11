"""Verify only H's prescribed document correction and retained metrics."""

import json
from pathlib import Path


root = Path(__file__).parent
candidate = (root / "milestone-candidate-g.md").read_text(encoding="utf-8")
old = "Root evidence (`verification.json`):"
new = "Root evidence (`verification.json`, `three-way-proof.json`):"
assert candidate.count(old) == 1
document = (root / "milestone-review.md").read_text(encoding="utf-8")
assert document == candidate.replace(old, new, 1)
assert len(document.split()) < 500

verification = json.loads((root / "verification.json").read_text(encoding="utf-8"))
proof = json.loads((root / "three-way-proof.json").read_text(encoding="utf-8"))
assert verification["root_full"]["tests"] == 399
assert verification["root_full"]["status"] == "PASS"
assert verification["targeted"]["tests"] == 122
assert verification["targeted"]["status"] == "PASS"
assert proof["maximum_distinct_tasks"] == 3
assert len(proof["segments_at_maximum"]) == 8
assert round(sum(item["seconds"] for item in proof["segments_at_maximum"]), 6) == 262.733616
print(f"Exact document correction PASS; words={len(document.split())}; no product tests rerun")
