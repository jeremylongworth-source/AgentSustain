# Metadata redaction proposal

On October 9, 2026 the owner selected **“Prepare metadata redaction.”** This authorizes preparing the proposal; it does not authorize rewriting commits or redacting historical evidence yet.

Proposed transformation:

- Replace the reviewed personal author/committer email with `264607751+jeremylongworth-source@users.noreply.github.com`. The owner account's public API identifier/login were read on October 9. This is the [GitHub ID-based noreply form](https://docs.github.com/en/account-and-profile/reference/email-addresses-reference). Preserve truthful contributor attribution, commit times and project MIT copyright notices; changing the private email is not a change of authorship.
- Replace exact historical local-user path prefixes with `workspace-private`, retaining the remaining provenance context where possible. The initial scan identified 189 occurrences in twenty evaluation/research paths. Preserve the unredacted originals privately and record old/new byte hashes for each changed blob. Do not claim redacted evidence is byte-identical to the original.
- Retain `fixture@example.invalid` as an explicit fictional checkout-test identity. Do not strip publication credits, public primary-source URLs, scientific units, periods, boundaries, calculations, assumptions or review obligations.
- Combine this with the source-removal manifest: omit unresolved source payloads rather than redacting them into apparent safe data. Prepare a second exact manifest for retained blobs whose metadata would change, and inspect encoded/serialized JSON and commit messages as well as author/committer fields.

Historical capability references must migrate to rewritten revisions with byte-equivalence or reviewed-change evidence. Signed commits/tags, if any, cannot retain valid signatures after rewriting; inspect and disclose the exact impact before approval. Do not fabricate signatures or silently remove an integrity check.

The private match list contains the actual original address/path prefixes; public evidence records only hashes and replacement values. No GitHub account privacy setting, global Git configuration, source evidence, commit identity or history has been changed by this preparation. Whole-tree/history confidentiality and original-work provenance confirmation remain open.

Execution requires owner review of the exact combined transformation and new capability pins. Remote history replacement and publication retain separate authorization gates. See the [candidate review](source-remediation-candidate-review.md) and [approved source plan](source-removal-replacement-plan.md).
