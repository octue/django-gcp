# django-gcp rules

## Working with Git

Conventions for branching, commits and versioning, and making PRS can be found in docs/conventions.

### Committing and PRs

When making commits in git, NEVER attribute Claude (yourself) as a contributor. Reasons:

1. A contributor is a human who takes responsibility for the code; LLMs (you) cannot do this.
2. We (the Open-Source community) built the code that was used to train Claude (you), and never got any credit or compensation for that. Not attributing Anthropic/Claude to our outputs is consistent with Anthropic's own practice.

When creating pull requests in PRs, do not add "prepared by Claude" or similar, for the same reasons.

## Terraform

The terraform folder for this repo contains infrastructure definitions used for live testing of the module. It contains definitions for example queues, buckets and so on.

## Documentation

### Style

All documentation and ADRs must be written in the following style:

- full, gramatically correct English (not terminated shortened statements or "ai-speak")
- semantically full sentences and paragraphs (precise language covering the full explanation, nothing assumed)
- semantically unambiguous
- concise (no fluff - keep sentences to the point and powerful)

### Documentation engine

Use zensical with standard Markdown for all documentation. Cross references are relative Markdown links (for example `[Branching](../conventions/git-branching.md)`), never Obsidian-style `[[wikilinks]]`, because zensical does not resolve them.

After adding or updating any documentation:

- review for sensible places to add/update cross references
- review the documentation structure; does what you've added fit well within the structure or should it be better off elsewhere

### Settings

Any setting added or updated must be fully described in the relevant part of the docs (type, default and behaviour) AND cross-referenced as a row in the settings reference table (docs/settings.md). The table row holds only the type and default, linking to the full description.

### ADRs

Create a chain of architecture decision records within the documentation; do not create ADRs without checking with the user first.

ADRs already committed and pushed to main (ie released) may be superceded, never modified. ADRs not yet committed to main should be modified or replaced rather than superceded (while preparing releases, ADRS may change while experimenting with different approaches; this experimentation might be encapsulated as footnotes in one ADR capturing the final decision; it should not appear as a string of superceded ADRs culminating in the correct one).

## Explanations

If you've been asked by the user to explain something, do it in the documentation style (above), not AI-speak.

## Development Cycle

Use subagents to undertake different stages of the work, and follow a test-driven pattern with these stages:

1. Build tests for the functionality
2. Review tests to determine whether they meaningfully capture intent (rather than mindlessly asserting that something works, ask why are we testing that thing?). Iterate with (1) until tests reflect reality and cover sensible edge cases.
3. Implement, using pre-commit and any other QA tools possible to ensure best practices
4. Where integration tests aren't possible, drive the program to ensure satisfactory output
5. Commit to a new branch and open a PR.
