# Releasing Kale

This document covers how to release `kubeflow-kale` to TestPyPI and PyPI.

## Prerequisites

- **git-cliff** (optional) - for changelog generation: `cargo install git-cliff` or `brew install git-cliff`
- **TestPyPI account** - register at https://test.pypi.org and create a project-scoped API token for `kubeflow-kale`
- **PyPI account** - register at https://pypi.org and create a project-scoped API token for `kubeflow-kale`
- **Repository secrets** configured (see [Setup Checklist](#setup-checklist))

## Version Bumping

Set the version for both Python (PEP 440) and npm (semver) with a single command:

```bash
make release VERSION=2.0.0a2
```

This updates:
- `kale/__init__.py` (`__version__ = "2.0.0a2"`)
- `labextension/package.json` (`"version": "2.0.0-alpha.2"`)
- Generates a changelog (if git-cliff is installed)

Commit the version bump:

```bash
git add kale/__init__.py labextension/package.json CHANGELOG/
git commit -s -m "Release v2.0.0a2"
git push
```

## Pre-release Versioning (PEP 440)

| Stage | Python Version | npm Version | Example |
|-------|---------------|-------------|---------|
| Alpha | `2.0.0a1` | `2.0.0-alpha.1` | Early testing |
| Beta | `2.0.0b1` | `2.0.0-beta.1` | Feature complete, testing |
| Release Candidate | `2.0.0rc1` | `2.0.0-rc.1` | Final validation |
| Final | `2.0.0` | `2.0.0` | Production release |

## Running the Release Workflow

The release workflow is **manual-only** (`workflow_dispatch`). Navigate to:

**Actions → Release → Run workflow**

### Dry Run (default)

By default, `dry_run` is `true`. This runs the full build, lint, test, and wheel
validation pipeline **without publishing anything**. Use this to verify
everything works before a real release.

### Publishing

Uncheck `dry_run` to publish. The workflow follows this sequence:

```
prepare → build → test-wheels → create-tag → publish-testpypi ─┬→ publish-pypi
                                                                │   (production env,
                                                                │    manual approval)
                                                                ├→ github-release
                                                                └→ bump-dev-version
```

1. **Build & test** - lints, runs tests, builds wheel, smoke-tests the wheel
2. **Create tag** - creates and pushes a git tag (e.g., `v2.0.0a2`)
3. **Publish to TestPyPI** - uploads to TestPyPI (requires `release` environment)
4. **Publish to PyPI** - uploads to production PyPI (requires `production` environment with manual approval)
5. **GitHub Release** - creates a GitHub release with the wheel attached
6. **Bump dev version** - automatically bumps the version on the branch to the next pre-release

The dev version bump creates a PR that increments the pre-release number
(`2.0.0a1` → `2.0.0a2`). For final releases, it bumps the patch and starts a
new alpha cycle (`2.0.0` → `2.0.1a1`). Merge the PR to update the branch.

### Validating on TestPyPI

After the TestPyPI publish succeeds, validate the package before approving
the production PyPI deployment:

```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ kubeflow-kale==2.0.0a2
python -c "from kale import __version__; print(__version__)"
kale --help
```

The `--extra-index-url` is needed because TestPyPI may not have all dependencies.

Once validated, go to the workflow run in GitHub Actions and approve the
`production` environment deployment to publish to PyPI.

## Testing from a Fork

You can test the full release workflow from a fork:

1. Fork the repository
2. Add `TESTPYPI_API_TOKEN` to your fork's repository secrets
   (Settings → Secrets and variables → Actions)
3. The token must be scoped to the `kubeflow-kale` project on TestPyPI
4. Create a `release` environment in your fork (Settings → Environments)
5. Run the workflow with `dry_run` unchecked

This publishes to TestPyPI only. The `production` environment and `PYPI_API_TOKEN`
are only needed for the upstream repository.

## Setup Checklist

### Repository Secrets

| Secret | Where | Purpose |
|--------|-------|---------|
| `TESTPYPI_API_TOKEN` | Repository secrets | Project-scoped token for `kubeflow-kale` on TestPyPI |
| `PYPI_API_TOKEN` | Repository secrets | Project-scoped token for `kubeflow-kale` on PyPI |

### GitHub Environments

| Environment | Purpose | Protection Rules |
|-------------|---------|-----------------|
| `release` | TestPyPI publishing | None (or branch protection) |
| `production` | PyPI publishing | **Required reviewers** (manual approval) |

To configure environments: Settings → Environments → New environment.

For the `production` environment, enable "Required reviewers" and add at least
one maintainer as a reviewer. This ensures someone manually approves every
production PyPI publish after validating on TestPyPI.
