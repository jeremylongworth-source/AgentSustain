# Platform validation

The repository requires Python 3.11 or later, Git with the complete approved history, and the dependencies in `requirements-dev.txt`. Historical Git objects are runtime inputs to router integrity checks. A source archive or shallow checkout cannot replace them. Current examples and tests use fictional data; passing these checks does not establish scientific, legal, source or independent organization acceptance.

## Manual matrix

[Repository validation](../.github/workflows/validation.yml) defines Windows 2025 and Ubuntu 24.04 checks with Python 3.11 and 3.14. Each job installs the declared dependencies and runs `python -m unittest discover -s tests -v`. Jobs retain independent failures, have a 45-minute timeout, print the tested Git revision and resolved dependencies, use complete history, and avoid persisting checkout credentials. Actions are pinned to commit objects verified against their official repositories on 2026-10-06.

The workflow has only a manual trigger and read-only repository permissions. It performs no publication, package upload, release or deployment. This local file has not been pushed or dispatched. A manual workflow must be present on the remote default branch before GitHub can dispatch it; see [GitHub's manual workflow documentation](https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow). Publishing and dispatch require separate owner authorization.

[Local workflow checks](../evaluations/sus25-platform-workflow-validation.json) record YAML parsing and checks of the configured matrix, commands, permissions, history and action pins. They do not validate GitHub's service schema or prove any matrix job succeeds. Temporary YAML validation tooling is outside the repository dependencies.

## Available host evidence

Native Linux execution was unavailable on the inspected machine: WSL listed only Docker Desktop's internal distribution, and the Docker Linux engine connection failed. No service was started and no Linux distribution was installed. The local Python launcher reported only Python 3.14. Linux and Python 3.11 compatibility remain unverified.

A new local clone of approved development revision `22515f4` uses independent Git objects and a fresh Windows virtual environment. Its declared dependencies are installed separately from the working repository environment. [The saved clean-checkout validation](../evaluations/sus25-clean-windows-validation.json) records 807 passing tests in 724.915 seconds on Python 3.14.3, with all 388 recorded source-file hashes unchanged. Resolved dependencies include jsonschema 4.26.0 and are listed in the witness. The clone remained clean after the suite. The workflow and documentation added later are outside this approved runtime snapshot; their local configuration checks are separate. This exercises a clean checkout on the same Windows host, rather than an independent organization or a second operating system.

## Remaining acceptance

Actual successful Windows/Linux matrix runs, minimum-Python evidence, repeatable installation and organization acceptance on intended agent platforms, final release dependency policy and documentation usability remain open. Preserve the tested revision, interpreter, resolved dependency versions, terminal test outcome and source hashes when collecting subsequent evidence. Owner development approval through ba42b4e does not grant release or external execution authority.
