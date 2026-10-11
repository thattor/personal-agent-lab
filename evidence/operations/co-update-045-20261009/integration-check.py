"""Synthetic request -> mock text -> prepared bytes; no provider or persistence."""

import hashlib
import json
from pathlib import Path

from pal.artifact_content_v5 import prepare_content
from pal.github_read_request_v5 import ReadRequestError, prepare_read


def main():
    body = "## Synthetic issue\r\n日本語の本文\r\n"
    observations = []

    def mock_read(request):
        assert request.argv == (
            "gh", "api", "--method", "GET", "--hostname", "github.com",
            "repos/thattor/personal-agent-lab/issues/7",
        )
        observations.append(request.argv[-1])
        assert len(body.encode("utf-8")) <= request.max_bytes
        return body

    request = prepare_read(
        "github.issue.read", {"repository": "thattor/personal-agent-lab", "number": 7}
    )
    content = prepare_content(mock_read(request), "text/markdown")
    assert content.content == body
    assert content.data.decode("utf-8") == body
    assert content.byte_count == 40
    assert content.sha256 == hashlib.sha256(body.encode("utf-8")).hexdigest()
    try:
        mock_read(prepare_read("github.issue.read", {"repository": "foreign/repo", "number": 7}))
    except ReadRequestError as error:
        assert error.code == "denied"
    else:
        raise AssertionError("foreign repository accepted")
    assert len(observations) == 1
    result = {
        "status": "PASS",
        "scope": "two pure helpers, synthetic mock read, unsaved content preview",
        "request_argv": request.argv,
        "content_preview": {
            "hash": content.sha256, "bytes": content.byte_count,
            "media_type": content.media_type,
        },
        "foreign_repository_reaches_mock": False,
        "real_provider_calls": 0,
        "saved_artifacts_receipts_or_completion": 0,
        "ct_e2e_service_acceptance": "NOT_RUN",
    }
    Path(__file__).with_name("integration-check.json").write_text(
        json.dumps(result, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(json.dumps(result, ensure_ascii=False))


if __name__ == "__main__":
    main()
