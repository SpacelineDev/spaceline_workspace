---
name: Code Review
description: Review code for correctness, regressions, maintainability, tests, performance, API contracts and edge cases before proposing changes.
triggers: code review, review code, inspect code, analyze code, refactor, quality audit, architecture review, review pull request
---

# Code review

1. Read the relevant files, call sites, tests, configuration and repository conventions before suggesting edits.
2. Trace data flow and error paths, not just the selected function.
3. Prioritize reproducible correctness defects, security issues, data loss and backward compatibility over style.
4. For behavioral changes, write a failing regression test first, implement the smallest fix, then refactor.
5. Inspect the final diff for accidental changes, secrets, generated files and inconsistent documentation.
6. Run focused tests and the repository's full suite; report exact commands and results.
7. Do not claim code is deployed or user-tested when it was only edited locally.
