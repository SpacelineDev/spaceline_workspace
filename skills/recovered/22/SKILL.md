---
name: Security Review
description: Threat-model local applications and agent tools; inspect authentication, secrets, path traversal, SSRF, shell execution, injection, file parsing and destructive actions.
triggers: security review, security audit, threat model, vulnerability, harden, ssrf, injection, secrets, credential leak
---

# Security review

1. Identify assets, trust boundaries, attacker-controlled inputs and dangerous capabilities.
2. Check authentication/authorization on every API route and fail closed on invalid sessions.
3. Inspect secrets handling, logging, environment exposure, path traversal and symlink behavior.
4. Review browser navigation and redirects for private-network access and DNS-resolution gaps.
5. Review process invocation for shell usage, argument injection, working-directory escape and command allowlists.
6. Parse untrusted archives/documents with size, entry-count, XML and decompression limits; never execute macros.
7. Add regression tests for each confirmed flaw. State residual risks and do not call a partial mitigation complete security.
