# Documentation

How the documentation is written and maintained. See also [Branching](git-branching.md),
[Commits and versioning](git-commits-and-versioning.md), and
[Pull requests](git-pull-requests.md) for the Git conventions.

## Engine

The documentation is standard Markdown built with [Zensical](https://zensical.org),
configured by `zensical.toml` in the repository root. Read the Docs builds and publishes the
site from `.readthedocs.yaml`; the build runs in strict mode, so a broken internal link
fails the build rather than being published.

Cross references are relative Markdown links (for example
`[Branching](../conventions/git-branching.md)`), never Obsidian-style wikilinks, because
Zensical does not resolve them. If a page moves, add a redirect from its old URL to
`scripts/rtd_redirects.toml` and sync it to Read the Docs with
`python scripts/sync_rtd_redirects.py`.

## Style

All documentation is written in full, grammatically correct English: semantically complete
sentences and paragraphs, precise and unambiguous, and concise — no fluff, no shortened
note-form statements.

## Settings

Any setting added or updated must be:

1. fully described in the relevant module page (type, default, and behaviour), and
2. cross-referenced as a row in the [settings reference](../settings/django-settings.md) table, linking to
   that full description.

The table row holds only the type and default; do not duplicate the full description there.

## After any change

Review the surrounding documentation for sensible places to add or update cross references,
and consider whether the new content fits the structure or belongs elsewhere.
