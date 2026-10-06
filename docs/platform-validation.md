# Platform validation

The repository requires Python 3.11 or later, Git with the complete approved history, and the dependencies in `requirements-dev.txt`. Historical Git objects are runtime inputs to router integrity checks. A source archive or shallow checkout cannot replace them. Current examples and tests use fictional data; passing these checks does not establish scientific, legal, source or independent organization acceptance.

## Manual matrix

[Repository validation](../.github/workflows/validation.yml) defines Windows 2025 and Ubuntu 24.04 checks with Python 3.11 and 3.14. Each job installs the declared dependencies and runs `python -m unittest discover -s tests -v`. Jobs retain independent failures, have a 45-minute timeout, print the tested Git revision and resolved dependencies, use complete history, and avoid persisting checkout credentials. Actions are pinned to commit objects verified against their official repositories on 2026-10-06.

The workflow has only a manual trigger and read-only repository permissions. It performs no publication, package upload, release or deployment. This local file has not been pushed or dispatched. A manual workflow must be present on the remote default branch before GitHub can dispatch it; see [GitHub's manual workflow documentation](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow). Publishing and dispatch require separate owner authorization.

[Local workflow checks](../evaluations/sus25-platform-workflow-validation.json) record YAML parsing and checks of the configured matrix, commands, permissions, history and action pins. They do not validate GitHub's service schema or prove any matrix job succeeds. Temporary YAML validation tooling is outside the repository dependencies.

## Available host evidence

Native Linux execution was unavailable on the inspected machine: WSL listed only Docker Desktop's internal distribution, and the Docker Linux engine connection failed. No service was started and no Linux distribution was installed. The local Python launcher reported only Python 3.14. A subsequent read-only runtime inventory located an existing bundled Python 3.12.14 with venv/ensurepip support; this discovery does not establish Python 3.11 or Linux compatibility.

A new local clone of approved development revision `22515f4` uses independent Git objects and a fresh Windows virtual environment. Its declared dependencies are installed separately from the working repository environment. [The saved clean-checkout validation](../evaluations/sus25-clean-windows-validation.json) records 807 passing tests in 724.915 seconds on Python 3.14.3, with all 388 recorded source-file hashes unchanged. Resolved dependencies include jsonschema 4.26.0 and are listed in the witness. The clone remained clean after the suite. The workflow and documentation added later are outside this approved runtime snapshot; their local configuration checks are separate. This exercises a clean checkout on the same Windows host, rather than an independent organization or a second operating system.

## Remaining acceptance

Actual successful Windows/Linux matrix runs, native Linux/other intended agent-platform evidence, repeatable installation and independent organization acceptance on intended agent platforms, final release dependency policy and documentation usability remain open. Preserve the tested revision, interpreter, resolved dependency versions, terminal test outcome and source hashes when collecting subsequent evidence. Owner development approval through ba42b4e does not grant release or external execution authority.


## Subsequent Python 3.12 validation

An existing local bundled Python 3.12.14 was checked against a new independent-object, full-history clone of revision `6670800`. A fresh virtual environment installed only `requirements-dev.txt`. [The durable witness](../evaluations/sus25-clean-python312-validation.json) records 826 passing tests in 770.492 seconds of total execution (unittest reported 767.336 seconds), resolved dependencies, a clean final checkout and 834 unchanged tracked-file hashes. [The actual organization CLI comparison](../evaluations/sus25-python312-organization-cli.json) passes all twenty-two checks and matches the complete saved Python 3.14 output, with both input files unchanged. Every Git-tracked file in that checkout is hashed before/after validation, including code, source datasets, scenario recipes, prior result oracles and documentation. This stronger scope is separate from the earlier source-file-only witnesses and does not rewrite them.

This is a second interpreter on the same Windows host, rather than native Linux, the minimum Python 3.11, another agent platform or independent organization acceptance. The GitHub workflow remains local and undispatched. Existing bundled runtime files and global settings are unchanged; temporary checkout/environment/log files stay under ignored `private-data/`. No installation into user agent configuration, publication, deployment or release follows.


## Subsequent minimum-minor Python validation

A portable Windows x86-64 Python 3.11.17 distribution from [Astral's published release](https://github.com/astral-sh/python-build-standalone/releases/tag/20261003) was checked against a fresh full-history, independent-object clone of revision `f5a82ac`. [The runtime provenance](../evaluations/sus25-python311-runtime-provenance.json) records the exact publisher asset, release date, size and SHA-256 match. Archive paths/types/count/expanded-size boundaries were checked before extraction into ignored project-local storage. This verifies agreement with the publisher digest, not an independent binary/security audit. The runtime is not redistributed with the repository and does not determine AgentSustain's pending license.

The environment installs only the declared requirements. [The full-suite witness](../evaluations/sus25-clean-python311-validation.json) records 833 passing tests in 722.560 seconds of total execution (unittest reported 719.179 seconds), resolved dependencies, a clean final checkout and all 843 tracked-file hashes unchanged. An actual [organization CLI comparison](../evaluations/sus25-python311-organization-cli.json) already passes all twenty-two controlled checks and equals the complete saved Python 3.14 output, with both input files unchanged.

This directly tests the declared minimum minor family on Python 3.11.17; it does not certify every older patch build, another distribution, native Linux or another agent platform. System Python, global settings, source code and project dependency requirements remain unchanged. Independent organization and source/domain/professional/rights/scoped/release requirements remain open, and no GitHub workflow is dispatched.
