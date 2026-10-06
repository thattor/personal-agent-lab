# Browser smoke — 2026-10-06T12:41:59.543325+00:00

Actual Chrome UI, loopback `http://127.0.0.1:58487/`, mock provider explicitly displayed.

1. Sent synthetic ordinary message through textarea/Send. User and assistant response rendered; no Goal created.
2. Sent “Make a draft about fictional green stationery, do not send.” Actual UI showed Work accepted → Preparing your draft → Your local draft is ready; Current work completed; Open local draft link rendered.
3. Opened Inspect through UI navigation. Read-only Goal completed, Attempt pass, outcome host_utf8_size_hash_readback, receipt bound to revision/epoch and 79-byte artifact with SHA256 visible. No mutation forms/buttons in Inspect.
4. Supported SIGTERM/restart using same synthetic DB retained conversation/result; latest UI displayed friendly status labels and artifact link with no duplicate completion.
5. HTTP tests independently reject inspect POST/DELETE, wrong Host/Origin, oversized requests and unknown canonical fields. Browser JS renders model text via textContent, never innerHTML; CSP forbids inline/model script execution.

[Actual backend readback](browser-state.json). Observed Goal b38e6e0020ab45c5b6699b509617b820; Attempt f11aadc5155a4069906a72b36b7b0694; receipt 1d6d8e025b61475e9f70abed4576a2d3; artifact hash 01d8ea0b520436ec56b8ffa4b45598c23173cdfddf195533298947a94139d120. Chrome translation sometimes translated labels; it did not alter submitted requests or host state.

This is browser/mock evidence, not live-provider evidence or 72-hour soak. No external/public route was opened.

6. Later synthetic receipt check verified session UUID, original client key, accepted Record ID, intent/action and timestamp without message bodies. Chrome translation initially corrupted JSON field names; translate=no/notranslate fix was rechecked in actual browser and receipt JSON remained unchanged. [Screenshot](session-receipt.png). These synthetic UI sessions are excluded from the human soak minimums.
