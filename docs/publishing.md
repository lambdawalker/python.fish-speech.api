# Automated releases and PyPI publishing

`fish-speech-api` is one distribution built from `src/fishapi`, imported as
`fishapi`. It has no command-line entry point or required runtime dependency.
The optional `codec` extra installs `ormsgpack`. Hatchling remains the build
backend and uv manages development dependencies.

## Everyday release flow

1. Merge changes into `main` using Conventional Commit squash titles.
2. **Release and publish Python package** opens or updates a Release Please PR.
   It updates `pyproject.toml`, the project's version in `uv.lock`,
   `CHANGELOG.md`, and `.release-please-manifest.json`.
3. Review that PR and its validation. The workflow checks out the generated
   candidate and runs the same tests/build checks as ordinary PR CI.
4. Merge the release PR yourself. Keep its generated title and release labels.
5. The next main-branch run creates the GitHub tag/release, resolves its exact
   commit, tests/builds the distributions, and publishes through PyPI OIDC.
6. The final read-only job checks PyPI filenames/hashes and installs the exact
   version in a clean environment outside the checkout.

A feature merge prepares a release PR; it does not immediately upload a package.
There is no auto-merge. A GitHub release can exist even when upload fails: only a
successful verification job confirms PyPI availability.

### Versions

The first planned release is **0.1.0**, matching the existing project metadata.
There were no tags/GitHub releases and the PyPI project lookup returned HTTP 404
when this automation was added on October 8, 2026. This is not a name reservation
or verification of account ownership.

The empty release manifest lets Release Please's Python strategy propose its
initial `0.1.0`. The bootstrap SHA is this repository's initial commit, before
its client implementation. After the first release, history drives subsequent
versions. Do not set a permanent `release-as: 0.1.0` override.

| Change | Before 1.0 | At/after 1.0 |
| --- | --- | --- |
| `fix: ...` | Patch | Patch |
| `feat: ...` | Patch | Minor |
| `feat!: ...` or `BREAKING CHANGE:` | Minor | Major |
| `docs: ...` | Patch (Python strategy) | Patch (Python strategy) |
| Only `chore:` changes | Usually no release | Usually no release |

The two pre-major flags intentionally follow the names-library reference.
Ordinary releases use stable `vX.Y.Z` tags. Prerelease GitHub releases and
alpha/beta/rc/dev/post/local-version tags are rejected. Introduce an explicit
prerelease policy before using those versions. For a deliberate 1.0 transition,
use Release Please's documented one-release override and remove it afterward.

Do not hand-bump routine versions. There is no redundant runtime version
constant. The checker compares package metadata, the project's lockfile entry,
and the manifest once populated.

## One-time owner setup

These are account settings, not settings the repository files configure.

1. Sign in to [PyPI](https://pypi.org/), verify your email, and enable required 2FA.
2. For a new project, add a [pending publisher](https://pypi.org/manage/account/publishing/).
   If the project already exists under your account, use that project's
   Publishing settings instead.

   | Trusted Publisher field | Exact value |
   | --- | --- |
   | PyPI project | `fish-speech-api` |
   | GitHub owner | `lambdawalker` |
   | Repository | `python.fish-speech.api` |
   | Workflow filename | `publish.yml` |
   | GitHub environment | `pypi` |

3. Create/configure the [`pypi` GitHub environment](https://github.com/lambdawalker/python.fish-speech.api/settings/environments).
   Required reviewers are optional. If restricting deployment refs, allow both
   the **main branch** and **v* tags**: automated runs retain a main ref even
   though they build tagged source, while release-event runs use tag refs.
   The old tag-only restriction must be expanded for automatic publication.
4. In [Actions settings](https://github.com/lambdawalker/python.fish-speech.api/settings/actions),
   enable **Allow GitHub Actions to create and approve pull requests** so Release
   Please can open PRs. It receives contents/issues/pull-request writes only in
   its release-management job. Review any organization policy that overrides this.
5. Check branch protection and required checks as described below.

No PyPI API-token secret is needed. Only the isolated publishing job gets
`id-token: write`; it downloads the validated artifacts and invokes the official
PyPA publisher without checking out or executing the client source. No account
settings or publisher registration are assumed to have been completed by this
change. If the project name is unavailable, resolve ownership or choose a name
and update metadata, release configuration, checks, URLs, and publisher together.

### Bot-created PR checks

GitHub's built-in token generally does not trigger workflows for the PRs/releases
it creates. This is why publication consumes Release Please outputs in the same
run, rather than waiting for a separate release event.

The generated candidate is explicitly validated by the main-branch run, but its
checks may attach to the triggering base commit rather than the candidate PR's
head. Inspect that run and its resolved source SHA. If branch protection requires
PR-attached checks, an owner can close/reopen the release PR to trigger ordinary
PR CI, or configure an appropriately scoped GitHub App integration. Do not weaken
branch protection or treat a check on unrelated source as candidate validation.

## Validation and safe rehearsal

```bash
uv sync --locked
uv run --locked python -m unittest discover -s tests -v
uv run --locked python scripts/check_release.py
# Begin with a clean dist directory (remove previous build outputs first).
uv build
uv run --locked twine check --strict dist/*
uv run --locked python scripts/check_release.py --dist dist
```

`uv build` builds the sdist first and builds the wheel from it, exercising the
archive's self-contained packaging. CI runs Python 3.10, 3.12, and 3.14, checks
source/archive versions and contents, and imports a freshly installed wheel with
no dependencies from outside the checkout using isolated Python. Tests use a
local HTTP fixture; no Fish Speech server, GPU, model, or credentials are needed.
Release tooling uses `tomli` only on Python 3.10 as a development dependency.

Pull requests run these checks without publication or OIDC. For a local wheel
smoke test on Linux/macOS:

```bash
uv venv /tmp/fishapi-check
uv pip install --python /tmp/fishapi-check/bin/python --no-deps dist/*.whl
(cd /tmp && /tmp/fishapi-check/bin/python -I -c "from fishapi import FishAPI; print(FishAPI('spark.local').base_url)")
```

Use equivalent virtual-environment executable paths on Windows. No TestPyPI
publisher is configured. **Run workflow** on `main` reconciles release PRs and
may publish a merged, unreleased PR; it is not a dry run. Other branches cannot
use dispatch to publish.

## First release

Complete owner setup, then inspect the release PR created by the next releasable
main-branch commit (or run reconciliation on `main`). Confirm it proposes `0.1.0`
and that validation is green. Merge it when ready to release. Approve the `pypi`
environment if required. After the verification job succeeds:

```bash
uv add 'fish-speech-api==0.1.0'
# Or:
python -m pip install 'fish-speech-api==0.1.0'
```

The implementation of this workflow itself does not create a release tag or
upload a package. Do not create a competing manual `v0.1.0` release while its
Release Please PR is pending.

## Recovery

All automatic, manual, and release-event entry points share one concurrency
group, with active runs never cancelled by a later run. GitHub may replace a
pending run with a newer one; this is not a FIFO queue. If a release-event run
was cancelled while pending, rerun that original event run after the active run
finishes so its tag identity is preserved. The publishing job
consumes the exact validated Python 3.12 artifacts; it never rebuilds them.
Each build also stores `release-record/release.json` containing the version,
source commit, distribution filenames, and SHA-256 hashes.

- **Build fails after release creation:** use **Re-run failed jobs** on that
  original run to preserve release outputs. Starting a fresh reconciliation run
  may find no new release and therefore not publish anything.
- **Upload fails before any files arrive:** inspect PyPI, then retry the failed
  upload job from the same run, reusing the retained artifacts.
- **Some/all filenames already exist:** the preflight refuses the version and
  the publisher does not silently skip files. Download both the
  `python-distributions` and `release-record` artifacts from the original run.
  Compare every existing filename/hash with PyPI's version JSON endpoint. If all
  expected files match, do not upload again; run the local verifier below.
  If the verification job previously ran and failed, it can also be rerun;
  when upload failed, that job may have been skipped and unavailable to rerun. If only a subset
  exists and matches, have a maintainer perform a narrowly scoped recovery upload
  of only the missing original files through an authorized publisher. This
  workflow intentionally stops for that reconciliation; it has no blanket
  skip-existing recovery switch. Conflicting bytes require investigation and a
  new version, never overwriting/reusing filenames or moving a tag.
- **Post-upload verification fails:** retry only verification after checking
  registry propagation. Uploading again is unnecessary. The verifier has bounded
  retries and rejects hash conflicts/yanked files.
- **Artifacts expire:** Actions artifacts are requested for 90 days (subject to
  repository policy). Archive the distributions and release record in durable
  release storage before expiration if longer recovery is needed. Do not assume
  a new build is byte-identical or reconstruct missing provenance by guessing.

The existing **published GitHub release** trigger remains a manual/recovery
entry point. It accepts only stable matching tags whose resolved commit is on
main's history and whose packaging/lock/manifest agree. Use releases containing
this automation; historical source without its validation scripts is not
silently upgraded. Tag pushes alone do not publish. Never delete/recreate tags
or releases to force a retry.

For manual read-only verification of a downloaded release record:

```bash
uv run --no-project python scripts/verify_pypi.py /path/to/release.json
```

A registry outage/authentication error is not treated as an absent version.
Preflight fails closed. Successful preflight does not reserve the PyPI name.

## Troubleshooting

| Symptom | Check |
| --- | --- |
| Release Please cannot open a PR | Actions PR-creation setting, job permissions, organization restrictions |
| No release PR appears | Releasable Conventional Commit after bootstrap; release labels/history |
| Release PR lacks required checks | Bot-token limitation above; trigger ordinary PR CI as an owner |
| Trusted Publisher exchange fails | Exact owner/repository/workflow/environment values and environment ref rules |
| Version check fails | Project metadata, local lockfile entry, release manifest, stable tag |
| Existing version/files | Compare original hashes and follow partial-upload recovery; never overwrite |
| GitHub release exists but pip cannot install | Build/upload/verification results; GitHub release existence is not PyPI availability |

Official references:
- [Release Please Action](https://github.com/googleapis/release-please-action)
- [Release Please manifest configuration](https://github.com/googleapis/release-please/blob/main/docs/manifest-releaser.md)
- [PyPI Trusted Publishing](https://docs.pypi.org/trusted-publishers/using-a-publisher/)
- [Creating a PyPI project through OIDC](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/)
- [uv building and publishing](https://docs.astral.sh/uv/guides/package/)
