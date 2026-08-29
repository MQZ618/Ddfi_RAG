# Custom Research Frontend and File Delivery Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a project-side research workbench and a secure Dify chat/file proxy without modifying Dify Core, the official image, or the production Agent configuration.

**Architecture:** A zero-dependency Node server serves `web-client/public/`, proxies validated chat/upload requests to Dify, and signs tool-file download requests on demand. The browser renders a small safe Markdown subset and rewrites only validated Dify tool-file URLs to the same-origin artifact route.

**Tech Stack:** Node.js built-ins (`http`, `crypto`, `fs`, `node:test`), semantic HTML, CSS, browser JavaScript, Dify HTTP/SSE APIs.

**Spec:** `docs/superpowers/specs/2026-08-29-custom-research-frontend-design.md`

## Global Constraints

- Work only in branch `feature/custom-research-frontend` and its linked worktree.
- Do not edit Dify Core, `dify-main/`, Prompt v3, Live DSL, registry data, datasets, logs, checkpoints, or experiment results.
- Do not commit real API keys, Dify secrets, signed URLs, uploaded files, or generated artifacts.
- Do not claim a file is downloadable unless a real file ID and a successful proxy path exist.
- Keep cross-turn attachment persistence explicitly documented as a platform limitation.
- Use tests before implementation for the server and Markdown transformation.

## Task 1: Lock the contract and test harness

- [x] Add `web-client/package.json` with `npm test` and `npm start` scripts and no runtime dependencies.
- [x] Add `web-client/.env.example` with placeholders only; minimally unignore this file in `.gitignore`.
- [x] Add `web-client/test/server.test.mjs` for health, config, Dify payload allow-listing, SSE passthrough, artifact signing/proxying, and invalid path rejection.
- [x] Add `web-client/test/markdown.test.mjs` for HTML escaping, safe ordinary links, and validated tool-file URL rewriting.
- [x] Run `npm test`; observed the intended RED failure before implementation, then reached GREEN.

## Task 2: Implement the project-side server

- [x] Add `web-client/server.mjs` with environment parsing, bounded request bodies, JSON validation, and no secret logging.
- [x] Implement `GET /api/health` without exposing secret values.
- [x] Implement `POST /api/chat` with a fixed streaming mode and an explicit allow-list for forwarded fields.
- [x] Implement single-file `POST /api/files/upload` using a bounded multipart parser and Dify’s service API.
- [x] Implement `GET /api/artifacts/:id.:ext` with UUID/extension validation, fresh Dify HMAC signing, and byte-stream proxying.
- [x] Re-run server tests until GREEN; Dify integration coverage remains local and fake.

## Task 3: Implement the research workbench UI

- [x] Add `web-client/public/index.html` with the research-workbench layout, accessible controls, quick-task cards, chat region, attachments, and evidence status panel.
- [x] Add `web-client/public/styles.css` with the navy/cream/teal/amber visual system, responsive layout, and honest empty states.
- [x] Add `web-client/public/markdown.mjs` with safe escaping/rendering and validated Dify artifact-link rewriting.
- [x] Add `web-client/public/app.mjs` with chat SSE handling, conversation state, upload state, quick-task fill/send, artifact cards, and error/reset behavior.
- [x] Add `web-client/README.md` with setup, configuration, tests, startup, architecture, and known limitations.

## Task 4: Integration verification

- [x] Run `npm test` from `web-client/` and the existing Python test suite from the repository root.
- [x] Start the local server with placeholder configuration and verify health, static serving, invalid artifact requests, and no-secret output with a Node HTTP smoke command.
- [x] Run a fake-Dify streaming smoke test that proves the browser-facing proxy receives SSE and rewrites a tool-file URL to a same-origin artifact path.
- [ ] Real local Dify chat/upload/download smoke test is not claimed; it requires live App credentials and would change/consume runtime state.
- [x] Inspect the diff for scope, secrets, binary files, and accidental changes outside the declared target files.

## Task 5: Handoff

- [x] Update the plan checkboxes with actual verification results.
- [x] Run `git status --short`, `git diff --check`, and the full relevant tests.
- [x] Commit only the scoped project-side changes on `feature/custom-research-frontend`.
- [x] Report the checkpoint tag, new commit, files changed, commands run, risks, and deferred Dify platform limitations.
