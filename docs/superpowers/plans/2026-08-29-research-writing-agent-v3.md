# Research-writing Agent v3 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add explicit Capability/Phase Routing and a reproducible Dify Agent Prompt v3 pipeline without weakening the verified Registry/Dispatcher/Receipt baseline.

**Architecture:** Keep routing as a small pure-Python layer over the existing `SkillRegistry`. `CapabilityRouter` resolves every enabled matching Skill for explicit capability IDs; `PhaseRouter` maps the nine existing writing phases to runtime modes and delegates selection. Keep Dify integration host-facing: a YAML-aware validator and a generator create a new DSL from the current Agent snapshot, while live upload/import/publish remains an explicitly gated operation.

**Tech Stack:** Python 3.11+, standard-library routing runtime, pytest, PyYAML only for the optional Dify artifact tooling, Dify v1.16.1 Agent DSL.

**Spec:** `docs/specs/research-writing-agent-v3.md`

## Global Constraints

- Work only on `snapshot/dify-agent-2026-08-29`; do not modify or push remote `main`.
- Preserve `agentDSL/科研助手.yml` and `agentDSL/科研助手-current-2026-08-29.yml` as source snapshots.
- Preserve existing Registry, Dispatcher, Invocation Receipt, Artifact Store, Skill ZIPs, datasets, logs, checkpoints, and result files.
- Capability IDs are explicit Registry data; no keyword-based Skill guessing or duplicate hard-coded Skill catalog.
- A real Dify result is reported only after a real API call; no API key is committed or printed.
- No import, save, upload, or publish request is sent automatically by the offline build/validation commands.

---

### Task 1: Add explicit capability and phase routing

**Files:**
- Modify: `skill_runtime/core.py` (`SkillRegistry.select_all` and backward-compatible `select`)
- Create: `skill_runtime/routing.py`
- Modify: `skill_runtime/__init__.py`
- Create: `tests/skill_runtime/test_routing.py`

**Interfaces:**
- `SkillRegistry.select_all(capability: str, mode: str) -> list[dict[str, Any]]` returns every enabled matching Skill, sorted by `skill_id`, or raises the existing `DispatchError` codes.
- `CapabilityRouter(registry: SkillRegistry).route(capabilities: Sequence[str], mode: str) -> tuple[CapabilityRoute, ...]` resolves explicit capability IDs in caller order.
- `PhaseRouter(registry: SkillRegistry).route(phase: str, capabilities: Sequence[str]) -> PhaseRoute` maps the phase to its only allowed runtime mode.
- `CapabilityRoute.to_dict() -> dict[str, Any]` and `PhaseRoute.to_dict() -> dict[str, Any]` provide JSON-safe route records.

- [x] **Step 1: Write failing tests** for all-match selection, stable ordering, invalid capability/mode/phase rejection, duplicate capability rejection, and phase-to-mode mapping.
- [x] **Step 2: Run `./.venv/bin/python -m pytest -q tests/skill_runtime/test_routing.py`** and confirm collection or assertion failure because the new routing interface is absent.
- [x] **Step 3: Implement the smallest `select_all`, `CapabilityRouter`, and `PhaseRouter` surface** while keeping `select` behavior unchanged for existing callers.
- [x] **Step 4: Run the focused routing tests and then `./.venv/bin/python -m pytest -q tests/skill_runtime`**; fix implementation failures without changing the tests.
- [x] **Step 5: Run `python3 -m compileall -q skill_runtime`** and commit the routing milestone.

### Task 2: Add the production Prompt v3 and Dify artifact tooling

**Files:**
- Create: `prompts/科研助手-production-v3.md`
- Create: `scripts/validate_agent_dsl.py`
- Create: `scripts/build_agent_dsl.py`
- Modify: `pyproject.toml` optional `dify` dependencies only
- Create: `tests/skill_runtime/test_agent_dsl_tools.py`

**Interfaces:**
- `validate_agent_dsl.validate_document(document: Mapping[str, Any]) -> list[str]` returns an empty list for a structurally valid Agent DSL and explicit errors for malformed structure or embedded credentials.
- `build_agent_dsl.build_document(base: Mapping[str, Any], prompt: str) -> dict[str, Any]` deep-copies the base, replaces only the target system prompt, and never mutates the input mapping.
- CLI `python3 scripts/build_agent_dsl.py --base <snapshot> --prompt <prompt> --output <new-file>` refuses an output equal to the base and writes a new import candidate.
- CLI `python3 scripts/validate_agent_dsl.py <dsl-file>` prints `OK` only when the offline structural checks pass; missing Dify Skill assets are reported as warnings with names and never marked as bound.

- [x] **Step 1: Write failing tests** for prompt replacement isolation, source immutability, valid current snapshot parsing, missing-asset reporting, and credential rejection.
- [x] **Step 2: Run the focused tests** with system `python3` and observe failure because the tooling modules do not exist.
- [x] **Step 3: Write the production Prompt v3** from the contract, preserving the current evidence and no-fabrication rules without enumerating concrete Skill names.
- [x] **Step 4: Implement the builder and validator** with PyYAML under the optional Dify extra; refuse source overwrite and keep output paths explicit.
- [x] **Step 5: Run the focused tests, build a temporary candidate outside the repository, validate it, and remove only that temporary candidate after inspection.**
- [x] **Step 6: Commit the Prompt/tooling milestone without modifying either source DSL snapshot.**

### Task 3: Add non-mutating Dify preflight and documentation

**Files:**
- Create: `scripts/dify_agent_preflight.py`
- Create: `tests/skill_runtime/test_dify_agent_preflight.py`
- Modify: `README.md`
- Modify: `skills/README.md`

**Interfaces:**
- `dify_agent_preflight.check_agent(base_url: str, api_key: str, opener: Callable[..., Any] | None = None) -> dict[str, Any]` performs only `GET /v1/info` and `GET /v1/parameters`, returns redacted metadata, and raises a clear error for missing/invalid credentials.
- The CLI reads `DIFY_BASE_URL`/`DIFY_API_KEY` or explicit arguments, never prints the key, and never calls chat, upload, import, save, or publish endpoints.

- [x] **Step 1: Write failing tests** using a local fake opener that proves only the two GET paths are requested and authorization values are not returned.
- [x] **Step 2: Run the focused tests** and observe the expected missing-module failure.
- [x] **Step 3: Implement the read-only preflight** with standard-library HTTP so the core package stays dependency-free.
- [x] **Step 4: Run focused tests, then run the CLI without credentials** and verify it exits with a clear non-success message without a network write.
- [x] **Step 5: Document the generated DSL command, Skill upload prerequisite, and live-verification boundary; commit the milestone.**

### Task 4: Full verification and handoff

**Files:**
- No new source files; inspect all changed files and generated artifacts.

- [ ] **Step 1: Run `./.venv/bin/python scripts/build_skill_registry.py --check` and confirm `OK`.**
- [ ] **Step 2: Run `./.venv/bin/python -m pytest -q` and record the fresh total.**
- [ ] **Step 3: Run `python3 -m compileall -q skill_runtime scripts`.**
- [ ] **Step 4: Validate a newly generated Prompt v3 DSL candidate and check that the two source snapshots have no diff.**
- [ ] **Step 5: Check `git status`, branch, and diff; report changed files, exact verification output, and the unverified live-Dify condition.**
