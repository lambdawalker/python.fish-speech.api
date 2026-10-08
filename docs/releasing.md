# Publishing to PyPI

The package and workflow are ready for publishing. A maintainer must complete
the PyPI account-side configuration before the first release. A name lookup
returned 404 during setup; this does not reserve the package name.

## One-time setup

1. Sign in to [PyPI](https://pypi.org/) and enable the account's required 2FA.
2. Open [Publishing](https://pypi.org/manage/account/publishing/) and add a
   **pending publisher** for a new project with these exact values:

   | Field | Value |
   | --- | --- |
   | PyPI project name | `fish-speech-api` |
   | GitHub owner | `lambdawalker` |
   | Repository | `python.fish-speech.api` |
   | Workflow filename | `publish.yml` |
   | Environment | `pypi` |

3. In GitHub repository Settings → Environments, create/configure `pypi`.
   If desired, restrict deployments to version tags and add required reviewers.
4. If the PyPI project already exists under your account, add these values under
   its Publishing settings instead of creating a pending publisher.

Trusted Publishing exchanges GitHub's OIDC identity for short-lived upload
credentials. Do not add a long-lived PyPI token secret. The workflow's publish
job has `id-token: write`; the build job does not. If the package name becomes
unavailable, choose another name and update the metadata, docs, URLs and
publisher configuration consistently before releasing.

## First release

The checked-in version is `0.1.0`.

1. Ensure the **Test and build** workflow is green on the intended main commit.
2. Open GitHub → Releases → Draft a new release.
3. Create tag `v0.1.0` on that commit, enter release notes, and publish the release.
4. Watch **Publish to PyPI**. It checks tag/version agreement, tests, builds,
   checks metadata, and uploads the wheel and source distribution.
5. Verify from a clean project: `uv add 'fish-speech-api==0.1.0'`.

A tag push alone does not publish. The trigger is a published GitHub release.
No initial release/tag is created automatically by this repository setup.

## Later releases

```bash
uv version 0.1.1
uv lock
uv sync --locked
uv run --locked python -m unittest discover -s tests -v
uv build
uv run --locked twine check --strict dist/*
```

Commit `pyproject.toml`, `uv.lock`, and code/doc changes. Publish a GitHub release
with the matching tag (`v0.1.1`). Each version is immutable on PyPI; fixes need a
new version. The workflow does not silently skip already uploaded files. If an
upload partially succeeded, inspect PyPI before deciding how to recover.

The workflow deliberately has no manual trigger or automatic version bump.
To test a distribution without publishing, use `uv build` and install the wheel
into a clean environment. TestPyPI is not configured by this workflow.

References:
- [PyPI: creating a project with a Trusted Publisher](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/)
- [uv: building and publishing](https://docs.astral.sh/uv/guides/package/)
