# Existing PAL remote material: independent publication audit

Independent native Sol review of Root's read-only GitHub snapshots on 2026-10-09.
Target: existing `thattor/personal-agent-lab`, explicitly selected for publication
by the owner in the current parent chat. No additional network access, visibility
change, deletion, source/canonical update or external transmission was performed.
This note is the only audit-workspace change.

## Coverage and method

Read all seven `/private/tmp/pal-publication-*.json` inputs with
`json.JSONDecoder.raw_decode`, skipping whitespace between concatenated pages.
The actual snapshots contain one complete JSON page each; the parser supports
multiple pages. Inspected all titles/bodies plus metadata, not just keyword hits.
Supplemental full-input scans found no credential-prefix/private-key/Bearer
patterns, secret-value assignments, email addresses or personal home paths.
Pattern absence is supporting evidence, not a general secret-detection guarantee.

| Snapshot | Observed coverage | SHA256 |
| --- | --- | --- |
| issues | 19 entries: 18 Issues + draft PR19 | 86290bdbe4955c74ddfbddd988d92b7a322627ed2c2baa4c2f82d73e8c01de8c |
| comments | 27 issue comments | 8e42885db1adc931f72a2b1264a5501263a8e8894109410115ab75551a5764ce |
| pr-comments | 0 review comments | 4f53cda18c2baa0c0354bb5f9a3ecbe5ed12ab4d8e11ba873c2f11161202b945 |
| releases | 1 Stable-0 release, 0 uploaded assets | 40730e694ff285a627c7fabe49ee0314386142ae64734961653a3510f8fbeb81 |
| actions | total_count 0, 0 workflow runs | a2790a384d7d281e7395679000c35d27768d89dbd7052f725b8f4688beb59915 |
| artifacts | total_count 0, 0 artifacts | 244563f989470892c537c9a4622920af0d228ee4528f7d00c64a06d6cd95856c |
| branches | 2: main94fcacb; codex/pal-v5-co a7562f8 | 98b9e6ef2b198cf0d5dc823770d201439cfc18f47cbb143978dd0623bc75944f |

## Findings

No concrete credential, actual third-party personal data or unrelated private
project content requiring removal was found in these supplied remote materials.
Normal PAL development decisions, user approval summaries, review/task/commit IDs,
finite provider/cost observations, local process IDs/loopback ports and historical
limitations are technical project evidence, not credentials. Public GitHub author
identity/profile links are not treated as sensitive merely because they identify
the repository author. Cedar/Mika/Birch examples are named fictional test fixtures,
not asserted real people's histories.

Specific cross-project check: Issue8 comment6071966562 mentions a private local
RO-Crate trial using one 若木 article. It describes the proposed provenance
experiment and explicitly excludes the private article text, personal and family
information; none of those contents appears in the supplied comment. This is not
flagged as a private-content disclosure simply because the experiment is called
private. No additional owner confirmation target was identified by this audit.

Historical PAL comments include usage percentages and account-plan labels, and
Issue6 links a private Projects board and a proposed support-draft evidence file.
These supplied texts contain no account secret or support-message private body.
A public repository does not itself change that Projects board's visibility. The
linked repository files and their historical versions still require Root's separate
Git/source publication audit; this remote-text review does not certify those targets.

## Remaining limits

The branch snapshot reports protected=false for both branches. Root separately
reports ADMIN access/private repository, wiki/discussions disabled and zero forks;
these were not independently fetched here. Rulesets remain unverified because the
Free-private endpoint returned HTTP403. No bypass was attempted, and this is not
relabelled as “no rulesets.” Root owns the concrete visibility operation and final
source/history/evidence/attachment coverage. Deleted/edited past remote text,
private Projects contents, unprovided API pages and later remote changes are not
covered. No absolute repository-wide “safe to publish” guarantee is made, and no
abstract hypothetical risk creates a new blanket owner wait.
