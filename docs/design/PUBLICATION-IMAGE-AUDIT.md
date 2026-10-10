# Publication image audit — independent read-only inspection

2026-10-09. Scope: union of all reachable history of `18813c2`, `94fcacb` and `a7562f8`, not merely current trees. 32 distinct image blobs were extracted unchanged using git cat-file into /private/tmp/pal-publication-image-audit and individually viewed with view_image. Git objects and images were not edited; this note is the only committed change. No external checkout, network, authentication, model API, publication or history rewrite was used.

## Conclusion for visibility decision

No image shows a credential, token, password, real personal contact address/telephone, account identifier, unrelated project material, desktop username/path, device serial or private browser tabs. The visible chats are PAL test conversations. Explicit synthetic text establishes the Cedar/Mika samples; same-history ui-production-run/README.md and human-material.md establish the named thank-you and family gathering as developer synthetic inputs, not actual family/personal events. ui-integration-run/README.md establishes the meeting and bookshelf examples as seeded synthetic fixtures. A first name or concrete date in these images is therefore not evidence of a real person's conversation.

Recommendation: these 32 images alone provide no concrete privacy blocker to publication of the audited history. Do not represent this as clearance of text blobs, other refs, LFS/external assets, future commits or the whole repository. Root should combine this result with its separate text/credential/history audit before visibility changes. No deletion or history rewrite is recommended solely for these pixels.

Concrete remaining presentation issues: artifact-only samples lack an on-image synthetic label (especially rows 26–30); retain their linked README provenance or add a synthetic caption in future public presentation. Row 29 is a distorted clipped screenshot, already documented as non-proof by its README; prefer row 28 for demonstrations. Provider names, remaining-call counters and an expired request deadline expose historical operational status, not account credentials. These can remain historical evidence, but must not imply current service availability. Row 18 shows loopback/browser blocking, not a remote private endpoint. Rows marked .png actually contain JPEG: a format/extension discrepancy, not private metadata.

## Metadata and method

All 32 blobs decode as JPEG, RGB, 8-bit, three samples, no alpha. sips reports sRGB and 72 DPI. Dimensions are 1265×712 for ordinary UI captures; rows 11/31 are 1280×787, row 32 is 1265×778, artifact captures are 960×868 except row 29 (960×300). Independent JPEG marker inspection found only the standard 14-byte APP0 JFIF segment in every image: no APP1 EXIF/GPS/XMP, APP13 IPTC, COM comment or other application metadata. All end at the JPEG EOI marker, without trailing appended content. No location/camera/author metadata was observed. This is a normal metadata/pixel audit, not a steganography proof.

Inventory came from git rev-list --objects for the three refs, filtered for image extensions and confirmed blob type. The expected 32 unique blobs were obtained. Each row below denotes its own completed pixel and metadata inspection; category descriptions intentionally avoid copying raw private information.

- `18813c2` resolves to `18813c2dd28e87236d836451c1e0f2b1267da1fa`; reaches 32 audited image blobs.
- `94fcacb` resolves to `94fcacbf506b7514a2380dc1c4e61ccc5dcffca2`; reaches 32 audited image blobs.
- `a7562f8` resolves to `a7562f82192e478d5184947ebb38daa4ff3b38b1`; reaches 32 audited image blobs.

## Per-blob coverage (32/32)

| # | Blob | Historical path | Observed content / disposition |
|---|---|---|---|
| 1 | `5ff7c49f7284e940a6557d4bca6a01368e92a6b3` | `evidence/functional/stable1-20261007-run2/A1/ui.jpg` | Fictional lunch request; running UI; no credential/contact/device disclosure observed. |
| 2 | `0e1d2e0a1b603c9e99fad5a8c0f6e7de3be04e97` | `evidence/functional/stable1-20261007-run2/A2/ui.jpg` | Same fictional lunch; queued UI; no credential/contact/device disclosure observed. |
| 3 | `5847d949c25365304ba4e04efba760a7c57c1bee` | `evidence/functional/stable1-20261007-run2/B1/ui.jpg` | Unspecified generic thank-you request; queued; no credential/contact/device disclosure observed. |
| 4 | `68d365e84a79b4642047329bf28ae631b5667629` | `evidence/functional/stable1-20261007-run2/B2/ui.jpg` | Same generic thank-you; running; no credential/contact/device disclosure observed. |
| 5 | `00d1d1c3f99298af96ac81c44bd16c1339d84e00` | `evidence/functional/stable1-20261007-run2/C1/ui.jpg` | Explicit synthetic Cedar/Mika background; no credential/contact/device disclosure observed. |
| 6 | `fe632065ddd7110c5480a6b487ec3c2e883a4a17` | `evidence/functional/stable1-20261007-run2/C2/ui.jpg` | Explicit synthetic Cedar/Mika alternate reply; no credential/contact/device disclosure observed. |
| 7 | `93c4bfd6f2f1d16b5c7fb9a7f3081b155e75407d` | `evidence/functional/stable1-20261007-run2/FLOW1/final-ui.jpg` | Maple control test; completed/no target; no credential/contact/device disclosure observed. |
| 8 | `684a6b123505f74ffc14f0c332dfd6599e80ee7b` | `evidence/functional/stable1-20261007-run2/FLOW1/pending-ui.jpg` | Fictional draft correction; paused; no credential/contact/device disclosure observed. |
| 9 | `8d31d0b77b17f1a26822fc96768e90b05ebacf71` | `evidence/functional/stable1-20261007-run2/FLOW2_VOID_ONLY/final-ui.jpg` | Control-only synthetic conversation; no credential/contact/device disclosure observed. |
| 10 | `46b36441f06f675a7a312efb70316c33c788e01d` | `evidence/functional/stable1-20261007/C1/ui.jpg` | Explicit synthetic Cedar/Mika initial run; no credential/contact/device disclosure observed. |
| 11 | `1f5905c75efb2e51329c866b568558f02ee67906` | `evidence/operations/c063-preview.jpg` | Empty preview; provider counter and historical deadline only; no credential/contact/device disclosure observed. |
| 12 | `4f96223fab8928f60addaf6d729392ca9ecf4753` | `evidence/reviews/judgment-boundary/c047-controlled-cancel/cancelled.jpg` | Maple cancellation test; no credential/contact/device disclosure observed. |
| 13 | `2c31c33751fb2c621c5003c1990eb04fb8d1be76` | `evidence/reviews/judgment-boundary/c047-controlled-cancel/running.jpg` | Maple generic draft request; no credential/contact/device disclosure observed. |
| 14 | `07ed7efe52a158e6bb3e5d56f8109a64a80f898f` | `evidence/reviews/judgment-boundary/ui-c044-absence-failure/artifact-ui.png` | Generic lunch artifact; no recipient/date; no credential/contact/device disclosure observed. |
| 15 | `e176597d0777a173fc9a40bf768783354e36d163` | `evidence/reviews/judgment-boundary/ui-c044-absence-failure/conversation-ui.png` | Explicit fictional lunch conversation; no credential/contact/device disclosure observed. |
| 16 | `b872819881ac6f283fa4f20a2774e206ef2be7e5` | `evidence/reviews/judgment-boundary/ui-c045-partial/ABS-A1/artifact-ui.png` | Placeholder lunch artifact; circles replace values; no credential/contact/device disclosure observed. |
| 17 | `2413e0e90bae962740c6a98a44aac50093a2e5a9` | `evidence/reviews/judgment-boundary/ui-c045-partial/ABS-A1/conversation-ui.png` | Explicit fictional lunch; budget exhausted; no credential/contact/device disclosure observed. |
| 18 | `95851209e9b1e961baeb3f1826904db8cc1a0795` | `evidence/reviews/judgment-boundary/ui-c045-partial/ABS-A2/artifact-browser-block.png` | Loopback blocked-client error only; no credential/contact/device disclosure observed. |
| 19 | `7c6da4bb0d565ad4be089a30297590939969ed9e` | `evidence/reviews/judgment-boundary/ui-c045-partial/ABS-A2/conversation-ui.png` | Explicit fictional lunch alternate request; no credential/contact/device disclosure observed. |
| 20 | `0f38fa513668228c822fde6012152af114029f3b` | `evidence/reviews/judgment-boundary/ui-c045-partial/RUNNING-CANCEL/conversation-ui.png` | Maple draft fixture; unspecified particulars; no credential/contact/device disclosure observed. |
| 21 | `12fc0237e18c65dd30a39b1e7ca5d6c6ba6f2824` | `evidence/reviews/judgment-boundary/ui-c045-partial/TARGET-A/conversation-ui.png` | Generic cancel request; no personal detail; no credential/contact/device disclosure observed. |
| 22 | `c98bf5730685b0464e5d000f4b18ae2ec1cd6fb8` | `evidence/reviews/judgment-boundary/ui-c045-partial/TARGET-B/b1-ui.png` | Named work-target control fixture; no credential/contact/device disclosure observed. |
| 23 | `78c68c727ea5ac4039bdf8e1169f0e5fa89eb9ad` | `evidence/reviews/judgment-boundary/ui-c045-partial/TARGET-B/b2-ui.png` | Same fixture; historical correction refusal; no credential/contact/device disclosure observed. |
| 24 | `5026da467d222efd16114b2ea39b8b50cdba06e7` | `evidence/reviews/judgment-boundary/ui-c045-partial/TARGET-B/conversation-ui.png` | Same fixture; cancellation applied; no credential/contact/device disclosure observed. |
| 25 | `a248a258d10ac2fbce209ae14d4fd1d1ae69c30f` | `evidence/reviews/judgment-boundary/ui-cancel-transport/cancel-ui.jpg` | Explicit fictional picnic cancellation; no credential/contact/device disclosure observed. |
| 26 | `0ff5c0c8e16262aa9bc4b4f8b047e8286371a41c` | `evidence/reviews/judgment-boundary/ui-integration-run/answer-artifact.jpg` | Seeded synthetic meeting artifact; README establishes provenance; no credential/contact/device disclosure observed. |
| 27 | `ec2ca9e4856c374c92051924e9ca305787a1c042` | `evidence/reviews/judgment-boundary/ui-integration-run/correct-artifact.jpg` | Seeded synthetic bookshelf artifact; README establishes provenance; no credential/contact/device disclosure observed. |
| 28 | `34302e4e77ef0b90c703ad920a245a565b8a9bfc` | `evidence/reviews/judgment-boundary/ui-production-run/ui-invite-artifact-full.jpg` | Synthetic family invitation; README establishes provenance; no credential/contact/device disclosure observed. |
| 29 | `95089b52651a7c6c718840a83b5f87fe2982e1e1` | `evidence/reviews/judgment-boundary/ui-production-run/ui-invite-artifact.jpg` | Distorted clip of synthetic invitation; not display proof; no credential/contact/device disclosure observed. |
| 30 | `382f8b43d364166f782fba049b30d77e1bd0980f` | `evidence/reviews/judgment-boundary/ui-production-run/ui-known-artifact.jpg` | Synthetic named thank-you; README establishes provenance; no credential/contact/device disclosure observed. |
| 31 | `4056143b40f1291b3afaea71cb19d0e62f75277f` | `evidence/soak/2026-10-06/handoff.png` | Mock synthetic canary, visibly redacted; no credential/contact/device disclosure observed. |
| 32 | `4c26e7385252379dd504631e1ec2d6a30c484a2f` | `evidence/ui/session-receipt.png` | Explicit synthetic session receipt checks; mock provider; no credential/contact/device disclosure observed. |

## Limits and next check

The exact original image bytes are retained locally in the extraction directory with manifest.json. This note uses blob IDs/paths so it remains reviewable without republishing screenshots. Existing repo README provenance was read at audited ref18813c2; no old external PAL implementation was searched. No tests are appropriate for a note-only visual audit; git diff --check and exact one-file commit validation apply. Repeat inventory/pixel inspection if the publication ref gains new image blobs. Final visibility approval and any unrelated content remediation remain Root-owned.
