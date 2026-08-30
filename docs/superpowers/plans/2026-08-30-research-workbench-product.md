# Research Workbench Productization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make the local research workbench reliable for real research conversations, file uploads, streamed responses, artifact delivery, and responsive use.

**Architecture:** Keep the existing zero-build browser client and Node standard-library proxy. Add only small pure workflow helpers and explicit UI states; keep Dify Core, the official Dify image, prompts, DSL, skills, and secrets unchanged.

**Tech Stack:** HTML, CSS, browser ES modules, Node.js 18+ standard library, Node test runner, optional `playwright-core` for local Chrome E2E.

**Spec:** User-approved read-only product design prompt in the conversation; no separate design spec file was requested.

## Global Constraints

- Do not modify Dify Core or rebuild the official Dify 1.16.1 image.
- Do not modify Prompt, Live DSL, Skill Registry, Tool configuration, datasets, logs, checkpoints, or result files.
- Never expose `DIFY_API_KEY`, `DIFY_SECRET_KEY`, signed URLs, or upload contents to the browser or committed files.
- Do not promise cross-turn attachment persistence; report runtime unavailability honestly.
- Every new behavior gets a failing test before production code.
- If a blocker repeats, record it with evidence and continue independent tasks.
- Keep the implementation dependency-free unless a test-only browser dependency is required for real E2E.

### Task 1: Request lifecycle and user recovery

**Files:**
- Modify: `web-client/public/index.html`
- Modify: `web-client/public/app.mjs`
- Modify: `web-client/public/styles.css`
- Create: `web-client/public/workflow.mjs`
- Test: `web-client/test/workflow.test.mjs`
- Test: `web-client/test/browser.test.mjs`

**Interfaces:**
- `canSubmit({ query, sending, attachments }) -> boolean`
- `validateUpload(file) -> string`
- `artifactIdentity(file) -> string`

- [ ] Write failing tests for blank/busy/unuploaded submission, upload validation, stop, retry, and session reset.
- [ ] Run the focused tests and confirm they fail for the missing behavior.
- [ ] Add the smallest state transitions for `idle`, `sending`, `streaming`, `completed`, `failed`, and `cancelled`.
- [ ] Preserve the original query on failure or cancellation.
- [ ] Add stop and retry controls with accessible names.
- [ ] Run focused tests and the existing suite.

### Task 2: Attachment and artifact correctness

**Files:**
- Modify: `web-client/public/app.mjs`
- Modify: `web-client/public/index.html`
- Modify: `web-client/public/styles.css`
- Modify: `web-client/server.mjs`
- Test: `web-client/test/server.test.mjs`
- Test: `web-client/test/markdown.test.mjs`

- [ ] Write failing tests for invalid artifact IDs, invalid extensions, duplicate artifacts, upload failure recovery, and ready-only file submission.
- [ ] Run the focused tests and confirm the expected failures.
- [ ] Implement client-side validation using the existing server allowlist.
- [ ] Keep failed attachments visible with retry/remove actions.
- [ ] Deduplicate artifacts by validated ID and extension.
- [ ] Keep server validation as the trust boundary and preserve same-origin artifact proxying.
- [ ] Run server, Markdown, workflow, and browser tests.

### Task 3: Truthful runtime status and proxy cancellation

**Files:**
- Modify: `web-client/server.mjs`
- Modify: `web-client/public/app.mjs`
- Test: `web-client/test/server.test.mjs`

- [ ] Write a failing test proving a disconnected client cancels the upstream streaming request.
- [ ] Write a failing test for distinct configured/unavailable health states if the chosen API remains backward compatible.
- [ ] Implement request abort propagation without logging secrets.
- [ ] Keep health wording honest: configuration presence is not runtime availability.
- [ ] Run focused proxy tests and the complete suite.

### Task 4: Research-output rendering

**Files:**
- Modify: `web-client/public/markdown.mjs`
- Modify: `web-client/public/styles.css`
- Test: `web-client/test/markdown.test.mjs`

- [ ] Write failing tests for ordered lists, fenced code blocks, tables, blockquotes, long links, and preserved safe artifact links.
- [ ] Run the focused tests and confirm they fail.
- [ ] Extend the small renderer without adding a Markdown package unless the current renderer cannot safely support the required cases.
- [ ] Add readable styles for long scientific answers, tables, code, citations, and overflow.
- [ ] Run Markdown tests and the complete suite.

### Task 5: Session recovery, accessibility, and responsive UI

**Files:**
- Modify: `web-client/public/app.mjs`
- Modify: `web-client/public/index.html`
- Modify: `web-client/public/navigation.mjs`
- Modify: `web-client/public/styles.css`
- Test: `web-client/test/ui-contract.test.mjs`
- Test: `web-client/test/browser.test.mjs`

- [ ] Write failing browser/contract tests for draft recovery, new-session protection, keyboard submission, mobile navigation close, and live status labels.
- [ ] Run focused tests and confirm the expected failures.
- [ ] Persist only safe local session metadata and completed text, never secrets or binary files.
- [ ] Add accessible names, focus states, live regions, and mobile menu behavior.
- [ ] Remove decorative controls that have no action.
- [ ] Verify layouts at 1440, 1024, 768, and 390 pixels.

### Task 6: Real local browser and Dify regression

**Files:**
- Modify: `web-client/package.json` only if test-only browser tooling is needed.
- Create: `web-client/test/browser.test.mjs` only if not already created by Task 1.
- Create: `reports/research_workbench_product_e2e.md`

- [ ] Run the complete automated suite.
- [ ] Start the local web client only after code tests pass; never start training or modify Dify data.
- [ ] Run browser journeys for simple text, task cards, upload, three-material comparison, stop, retry, new session, refresh, artifact download, and mobile layout.
- [ ] Run the three supplied reports through the real UI only when the user has authorized live testing; record filenames and outcomes without copying secrets or full private contents.
- [ ] Record every blocker, workaround, failed case, and unverified assumption.
- [ ] Do not call the product production-ready unless all P0 cases pass and evidence is saved.

### Task 7: Final verification and Git handoff

**Files:**
- Modify: `reports/research_workbench_product_e2e.md`

- [ ] Run `npm test` from `web-client` and record the exact result.
- [ ] Run repository-level relevant tests and Registry checks without touching unrelated artifacts.
- [ ] Verify `git diff --check`, `git status --short --branch`, and the changed-file list.
- [ ] Commit only source, tests, and the relevant report; never commit `.env`, keys, runtime volumes, or downloaded materials.
- [ ] Report remaining risks and platform limitations separately from application quality.
