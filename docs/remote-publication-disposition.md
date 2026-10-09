# Remaining GitHub publication decision

The approved local source/metadata transformation does not authorize a GitHub change. Read-only checks on October 9, 2026 found repository ID `1404938419`, private visibility, default branch `main`, zero forks and zero pull requests. The advertised remote still points to `56de36e08ec99e847dc9f308a492c6d05e6d82b9`, containing the original history. No remote content or setting has changed.

## Proposed clean remote arrangement

For a public edition that excludes the unresolved historical payloads, prepare a new non-fork repository from the verified rewritten history and keep the original GitHub repository private as an archive. Preserving the requested `jeremylongworth-source/AgentSustain` URL would require an explicitly approved rename of the existing private repository followed by creation of a new private repository at that name. This is a proposal, not an executed or pre-approved account change.

Before execution, choose and verify the private archive name, snapshot repository settings, recheck refs/forks/PRs and preserve the original private backup. Then, only after explicit authorization, rename the old private repository, create the fresh non-fork private repository, and push only the validated rewritten branch as `main`. Preserve the original private archive and avoid copying old refs, objects, forks, releases or backup bundles into the new repository.

Reusing the original name deliberately ends GitHub's rename redirects. Existing clone URLs would then target the new repository, so update every known original/private clone to the private archive URL before creating or pushing the fresh public edition. Otherwise an old clone could reintroduce the original history. Do not assume all collaborator clones are known or automatically updated.

Verify the new repository identity and branch, clone it independently, rerun object/payload/privacy and runtime-pin checks, and test that known omitted source objects are unavailable in the new repository context. A later visibility change requires its own exact-content/confidentiality/provenance and publication approval. GitHub reporting enablement remains under the separate A5 decision.

## Existing-repository alternative

An in-place history rewrite is possible only with a separate remote-update decision and a defensible retained-object disposition. A force-push alone does not prove removal from GitHub cached SHA views or other references. Do not infer that the absence of forks/PRs guarantees purge, or that GitHub Support will remove ordinary metadata or unresolved rights material under its sensitive-data policy. Qualified clearance of any server-retained source material would also change the publication basis and needs actual evidence.

Primary guidance: [GitHub history removal and limitations](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository) and [repository renaming](https://docs.github.com/en/repositories/creating-and-managing-repositories/renaming-a-repository). Preserve the existing-repository URL intent; no rename, repository creation/deletion, force-push, visibility change, support contact or reporting-setting change is authorized by this local proposal.
