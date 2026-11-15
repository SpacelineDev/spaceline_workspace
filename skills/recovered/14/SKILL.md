---
name: Git Workflow
description: Inspect repository status and history, make minimal changes, review diffs, and prepare safe commits without destroying user work.
triggers: git, commit, branch, merge, rebase, repository status, working tree, resolve conflict
---

# Git workflow

1. Inspect status, current branch and existing diffs before modifying anything.
2. Never overwrite or discard uncommitted user work without explicit instruction.
3. Keep changes focused; use a branch for larger work if the repo is already under Git.
4. Review staged and unstaged diffs and run tests before a commit.
5. Avoid force push, hard reset, clean, destructive checkout and history rewriting unless the user explicitly authorizes it.
6. Summarize files changed, tests run and any remaining uncommitted state.
