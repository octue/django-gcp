# Pull requests

This explains how PRs are opened, titled, versioned, and — critically — who merges them. Branch creation and upkeep is covered in [Branching](git-branching.md); commit message form in [Commits and versioning](git-commits-and-versioning.md).

## Never add a "prepared by" trailer to a PR description

Same reasoning as for commit co-authoring.

## Open the PR

- Base = the trunk you branched from ([Branching](git-branching.md)). Set it explicitly:
  `gh pr create --base <trunk>`.
- If the change touches a documented pattern/convention/architecture, update the relevant `docs/` page in the same PR; non-trivial decisions get an ADR.

## PR title

The title follows conventional-commit form (`CODE: Capitalised summary`) using the
"greatest" commit code in the PR (top-most in the [Commits and versioning](git-commits-and-versioning.md) type-code table). It matters because the PR is squash-merged, so the title becomes the single commit message that lands on `main`. That message is what the `semantic` check reads when it calculates the expected version of the next PR, so a title carrying the wrong code makes the check demand the wrong version later. The title also becomes the title of the GitHub release that `.github/workflows/release.yml` publishes when the PR merges and the version has moved, so it is read by anyone browsing the releases.

## Never merge a pull request

Opening a PR is the assistant's job; merging it is the human's — in every repo, without exception, including small fixes, green CI, doc-only changes, and PRs the assistant authored itself. `gh pr merge`, the GitHub API, and the web UI all run as the signed-in user, so a merge commits _their_ account to code they have not reviewed. Open the PR, report the URL, and stop there. The same applies to force-pushing over someone's branch or deleting branches you did not create.

## Version bumps

Bump the workspace `version` in the root `Cargo.toml` **only on PRs whose base is `main`** — never on sub-branch PRs into a trunk like `geo` (the `semantic` check only runs on `main`-bound PRs, and trunk-PR bumps just create `Cargo.toml` conflicts). How to calculate and apply the bump is in [Commits and versioning](git-commits-and-versioning.md).

## Related notes

- [Branching](git-branching.md) — bases, naming, protected branches, updating
- [Commits and versioning](git-commits-and-versioning.md) — type codes, breaking changes, semver calculation
