# Branching

This explains how branches are created, named, pushed, and kept up to date. Opening and managing the resulting pull request is covered separately in [Pull requests](git-pull-requests.md).

## Start the branch from the right base

- **Fetch first, branch off the remote tip**, never a stale local branch:
  `git fetch origin && git checkout -b <name> origin/<base>`.
- **The base is the trunk you will merge back into**, usually but not always `main`.
- Branch names are lowercase, hyphen-separated.

## Never push to a protected branch

Never `git push` to `main` or any protected branch, even with admin/bypass rights and even if asked. Branch protection routes changes through CI and PR review; bypassing it skips those gates. Push a feature branch and open a PR instead — if the user wants a direct push to a protected branch, they must do it themselves.

If push output contains `Bypassed rule violations` or any sign a protection rule was overridden, that means the wrong thing just happened — flag it immediately.

## Keeping a branch up to date

Bring a branch up to date by merging the target branch in (rebase only on request — it rewrites history and needs a force-push).

## Related notes

- [Pull requests](git-pull-requests.md) — opening, titling, and versioning the PR
- [Commits and versioning](git-commits-and-versioning.md) — commit message form and semver
