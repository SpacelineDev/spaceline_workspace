# Codex workflow comparison — 2026-11-12

This review compares Spaceline 0.9.5 with publicly documented Codex workflows available on 2026-11-12. It is a product/workflow comparison, not a claim that Spaceline is an OpenAI product or a functional clone.

## Current Codex reference points reviewed

- [ChatGPT Work and Codex: current experience, model, local/cloud and voice guidance](https://help.openai.com/en/articles/20001275-chatgpt-work-and-codex) (updated within the last week when checked on 2026-11-12).
- [Codex product and app](https://openai.com/codex/)
- [Codex app announcement: parallel agents, threads, worktrees, skills and automations](https://openai.com/index/introducing-the-codex-app/)
- [Codex / ChatGPT desktop release changelog](https://learn.chatgpt.com/docs/changelog)
- [DevDay 2026 recap: agent command center, cloud Codex and code review](https://openai.com/index/devday-2026-recap/)

As of 2026-11-12, the public release changelog lists Codex CLI 0.167.2 on 2026-11-11. The desktop-app stream lists Codex app 26.1007 on 2026-10-08; CLI and desktop app have separate version tracks. The current ChatGPT desktop experience separates ChatGPT (Chat and Work) from Codex. Chat is for quick conversational assistance, Work is for longer multi-step research and deliverables, and Codex is for software development. Codex supports project-organized threads, multiple agents working in parallel on isolated worktrees, diff review/comments, reusable skills and automations. Codex Cloud can run coding tasks on managed computers and support continuation across desktop, web and mobile. These are product features, not assumptions based on a screenshot alone.

## Workflow comparison

| Current Codex workflow | Spaceline 0.9.5 implementation | Boundary |
|---|---|---|
| Chat / Work / Codex separation | Spaceline has distinct task modes for Chat, Web Search, Deep Research, Deep Think, Architect, Build, Debug, Review and other workflows | No separate global ChatGPT/Codex app switcher or separate cloud Work product |
| Projects and persistent threads | Local project selector and saved Spaceline conversations | Local-only; no account-wide/cloud recents sync |
| Multi-agent work | One selected provider/model per run; multiple research search angles are fetched concurrently before the model's tool loop | Not a true team of independently reasoning/coding agents; no agent command center or per-agent threads |
| Web research | Two initial independent search angles for Web Search; three for Deep Research; direct HTTP search and source reading stay in Activity without starting Chromium | Research quality depends on selected model reasoning, tool-call support, web access and provider quota |
| Local code work | Project file tools, checkpoints before writes, editor, terminal, preview and Git worktrees | Commands run with the Windows user's permissions; not an OS sandbox |
| Change review | Read-only Git status and redacted unstaged diff | No inline diff comments, full PR review or complete staged/untracked review workflow |
| Isolated parallel work | Create a Git worktree as another selectable Spaceline project; separate chats can target separate checkouts | Users manage separate chats; Spaceline does not supervise parallel model workers or merge agent work |
| Skills | Built-in and imported `SKILL.md` instructions | Not the same hosted skill runtime or full integrations ecosystem as Codex |
| Browser / computer use | Persistent Playwright Chromium workbench for explicit interactive browser requests; direct HTTP tools for research | No native cross-desktop computer-use agent or access to the user's everyday Chrome profile |
| Cloud / remote execution | Spaceline runs locally on the user's Windows machine | No OpenAI-managed cloud environment, remote agent execution or cross-device task continuation |
| Automations | Scheduled view and local workspace task support remain separate from the current research change | Not implemented in this build: the Scheduled view is currently a placeholder, with no background automation runner or review queue |

## Research flow

1. The selected provider/model remains authoritative; Spaceline does not silently change the model to imitate ChatGPT.
2. Web Search fans out two initial independent queries. Deep Research fans out three distinct angles concurrently before handing the evidence pack to the selected model.
3. The model receives bounded, untrusted search evidence and can call `web_search` and `web_open_source` for targeted follow-up searches and page reads. It should inspect primary sources, check dates, compare claims, and cite only URLs it actually opened.
4. Research progress is displayed in Activity. Chromium remains available in the Browser tab, but research does not launch it, request page snapshots, or switch to that tab. Explicit browser interaction still uses Chromium.
5. Deep Research has up to 14 model tool rounds; Web Search has up to 8. Actual depth depends on provider tool-calling support and usage limits.

This makes Spaceline's research workflow more deliberate; it does not make a smaller or non-tool-capable model reason like GPT-6. The user's selected model determines the reasoning capability. Spaceline also does not claim to reproduce Codex's parallel agent orchestration, remote cloud runtime, native sandbox, or full Code Review product.

## Git worktree safety

- Only projects that are themselves Git repository roots can create worktrees.
- Worktrees are created as a new `spaceline/<task>-<id>` branch in a separate `wt-...` project folder under the Spaceline workspace.
- Creation starts from the current committed `HEAD`; uncommitted changes in the base checkout are not copied.
- Worktree creation is non-destructive to the original checkout. The current release provides no worktree deletion button.
- The user selects the new worktree project and uses a separate chat for its task. This keeps file writes isolated by checkout.

## Not claimed / not yet implemented

Spaceline 0.9.5 does not include Codex-hosted models, cloud agents, remote development environments, inline diff comments, automated branch handoff, managed worktree cleanup, computer use across arbitrary desktop apps, or true multi-agent parallel execution. The Review panel remains read-only. Do not equate interface/workflow similarity with feature or model parity.


## 0.9.5 research transport and verification note

The first research search angles fan out concurrently through a direct HTTP client. It follows only bounded public HTTP/HTTPS redirects, rejects local/private destinations and non-text response types, extracts readable page content without executing page JavaScript, and bounds content before it reaches the model. The model's research tool schema exposes `web_search` and `web_open_source`; it does not expose Chromium navigation, click, or DOM-control tools unless the user explicitly requested browser interaction. The after-response Browser snapshot that previously caused a hidden Chromium launch has been removed.

A browser-level regression reproduced a mutation-observer loop in the assistant-message copy normalizer: SVG `innerHTML` serialization differed from the source string after parsing, so the observer kept replacing the same icon. Version 0.9.5 checks the parsed SVG DOM shape instead. The browser test injects legacy Copy / Copy markdown / Copy all / Copy code controls, confirms cleanup settles to one icon-only button below the reply, and verifies the copied clipboard payload is the original complete Markdown response.


The direct HTTP retrieval unit and routing tests pass, but a live public-web request could not be validated in this build environment: outbound DNS resolution is restricted here. Verify live search on the target Windows machine/network. The implementation remains model/provider agnostic; a small selected model cannot be given GPT-6-level reasoning solely by changing prompts or tools.
