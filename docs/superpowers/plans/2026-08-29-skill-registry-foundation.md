# Skill Registry Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace the 17-entry hand-maintained registry catalog with discoverable per-Skill manifests and a deterministic, validated generated Registry containing three real Skill packages.

**Architecture:** `skills/<skill-id>/manifest.json` is the metadata source for each registered Skill, while the existing uploadable ZIP remains the Skill definition artifact. The runtime discovers manifests under `skills/`, validates their schema and definition paths, normalizes entries, sorts them by `skill_id`, and hashes only semantic Registry content; `generated_at` and filesystem-relative output location do not affect the hash. Existing Dispatcher, Receipt, and Artifact classes remain outside this milestone.

**Tech Stack:** Python 3.11+ standard library, JSON, ZIP inspection, SHA-256, pytest.

**Spec:** User-provided task in `/Users/mqzzz/.codex/attachments/96d1c20a-2ed4-46fb-91cf-b911544bc37d/pasted-text.txt`.

## Global Constraints

- Work only in `snapshot/dify-agent-2026-08-29`; do not modify or push remote `main`.
- Preserve the existing Dispatcher, Invocation Receipt, Artifact Store, Dify files, datasets, logs, checkpoints, and result artifacts.
- Use Python standard library only for Registry code.
- Registered sample definitions are `academic-writing-review.zip`, `evidence-audit.zip`, and `writing-agent-router.zip`; the other ZIPs remain unregistered in this milestone.
- Supported manifest providers are `procedural_skill`, `invokable_skill`, and `tool`; `native` is not registered as a virtual Skill in this milestone.
- The semantic hash excludes `generated_at`, `definition_root`, and `registry_hash), and uses canonical JSON with stable key and Skill ordering.
- Do not hand-edit `skill-registry/skill-registry.json`; regenerate it with the builder.

---

### Task 1: Discover and validate individual manifests

**Files:**
- Modify: `skill_runtime/core.py`
- Test: `tests/skill_runtime/test_skill_runtime.py`

**Interfaces:**
- Produce `discover_manifests(manifest_root: Path) -> list[Path]`.
- Produce `load_manifest_source(source: Path) -> list[tuple[dict[str, Any], Path | None]]` for a manifest directory, one manifest file, or the existing catalog shape used by compatibility tests.
- Produce `validate_manifest(manifest: Mapping[str, Any], project_root: Path, manifest_path: Path | None = None) -> dict[str, Any]`.
- Keep `validate_manifest_catalog(catalog, project_root)` as a compatibility wrapper returning normalized entries.

- [ ] **Step 1: Write failing tests for discovery and schema errors**

Add tests that create `tmp_path/skills/demo/manifest.json` and `tmp_path/skills/demo/SKILL.md`, then assert:

```python
paths = discover_manifests(tmp_path / "skills")
assert paths == [tmp_path / "skills" / "demo" / "manifest.json"]
assert validate_manifest(json.loads(paths[0].read_text()), tmp_path)["skill_id"] == "demo"

with pytest.raises(ValueError, match="missing or invalid skill_id"):
    validate_manifest({"version": "1.0.0"}, tmp_path)
with pytest.raises(ValueError, match="duplicate skill_id"):
    validate_manifest_catalog([manifest(), manifest()], tmp_path)
with pytest.raises(ValueError, match="invalid provider_type"):
    validate_manifest({**manifest(), "provider_type": "unknown"}, tmp_path)
with pytest.raises(ValueError, match="invalid mode"):
    validate_manifest({**manifest(), "modes": ["unknown"]}, tmp_path)
with pytest.raises(ValueError, match="definition"):
    validate_manifest({**manifest(), "definition": "missing.md"}, tmp_path)
with pytest.raises(ValueError, match="empty capability"):
    validate_manifest({**manifest(), "capabilities": []}, tmp_path)
```

Also assert a `../outside` definition is rejected and a non-semver version such as `v1` is rejected.

- [ ] **Step 2: Run the focused tests to verify the new tests fail for missing APIs/behavior**

Run:
```bash
./.venv/bin/python -m pytest -q tests/skill_runtime/test_skill_runtime.py
```

Expected: failure in the newly added discovery/individual-manifest tests because the current runtime only accepts the centralized catalog and does not expose individual-manifest discovery.

- [ ] **Step 3: Implement the minimal loader, validator, and path checks**

In `skill_runtime/core.py`, add recursive `manifest.json` discovery, accept a single manifest object or a legacy `{"skills": [...]}` source, normalize schema version to `"1.0"`, strip scalar strings, require the MVP fields, require a non-empty capabilities list, require known modes, and validate every referenced definition.

Resolve ZIP definitions from the project root only when the manifest uses an object such as:

```json
{"path": "skills/demo.zip", "content_entry": "demo/SKILL.md"}
```

Reject absolute paths, `..` components, paths outside `project_root/skills`, missing files, invalid ZIPs, and missing `content_entry` entries. Preserve a string definition such as `"SKILL.md"` for a manifest-local plain-file Skill by resolving it relative to the manifest directory.

- [ ] **Step 4: Run the focused tests and the existing runtime tests**

Run:
```bash
./.venv/bin/python -m pytest -q tests/skill_runtime/test_skill_runtime.py
```

Expected: all validation and existing runtime tests pass; no Dify or online workflow tests are collected.

### Task 2: Build a deterministic Registry and drift checker

**Files:**
- Modify: `skill_runtime/core.py`
- Modify: `scripts/build_skill_registry.py`
- Test: `tests/skill_runtime/test_skill_runtime.py`

**Interfaces:**
- Extend `build_registry(manifest_path: Path, project_root: Path, output_path: Path, generated_at: str | None = None) -> Path` so `manifest_path` may be a manifest root directory.
- Keep `SkillRegistry.from_file(path: Path)` and `SkillRegistry.check_drift(manifest_path: Path) -> bool` stable for Dispatcher callers.
- Add a semantic-payload helper internal to `core.py`; it must exclude `generated_at`, `definition_root`, and `registry_hash`.
- Make the CLI default source `ROOT / "skills"`; retain `--manifest` as an explicit source override.

- [ ] **Step 1: Write failing tests for discovery build, stable hash, and drift**

Add tests that:

```python
build_registry(tmp_path / "skills", tmp_path, tmp_path / "out-1" / "registry.json", generated_at="2026-01-01T00:00:00Z")
build_registry(tmp_path / "skills", tmp_path, tmp_path / "out-2" / "registry.json", generated_at="2026-01-02T00:00:00Z")
assert json.loads(first.read_text())["registry_hash"] == json.loads(second.read_text())["registry_hash"]

assert SkillRegistry.from_file(first).check_drift(tmp_path / "skills") is False
manifest_file.write_text(manifest_file.read_text().replace('"1.0.0"', '"1.0.1"'))
assert SkillRegistry.from_file(first).check_drift(tmp_path / "skills") is True

build_registry(tmp_path / "skills", tmp_path, rebuilt)
assert SkillRegistry.from_file(rebuilt).check_drift(tmp_path / "skills") is False

document = json.loads(rebuilt.read_text())
assert all((tmp_path / document["definition_root"] / item["definition"]["path"]).is_file()
           for item in document["skills"])
```

Add a test that changing only `generated_at` leaves the hash unchanged and a test that two manifests with the same semantic fields in different file order yield the same hash.

- [ ] **Step 2: Run the new tests to confirm they fail against the current centralized builder**

Run:
```bash
./.venv/bin/python -m pytest -q tests/skill_runtime/test_skill_runtime.py -k "discovery or hash or drift"
```

Expected: failure because the current builder reads one centralized JSON file, hashes the output-relative `definition_root`, and does not discover sidecar manifests.

- [ ] **Step 3: Implement minimal deterministic build and CLI wiring**

Build normalized entries from all discovered manifests, inject definition archive SHA-256 and byte size, sort Skills by `skill_id`, serialize canonical semantic content with `sort_keys=True` and compact separators, and put the resulting `sha256:<digest>` in the generated document. Keep `generated_at` as an informational field after hashing.

Update `--check` to load the generated Registry and compare it against the same discovered source directory. Return exit code 0 with `OK` when current and 1 with `DRIFT` when stale.

- [ ] **Step 4: Run focused tests and both builder commands**

Run:
```bash
./.venv/bin/python -m pytest -q tests/skill_runtime/test_skill_runtime.py
./.venv/bin/python scripts/build_skill_registry.py --output /tmp/ddfi-skill-registry-test.json
./.venv/bin/python scripts/build_skill_registry.py --check
```

Expected: pytest passes; the explicit temporary build succeeds; the committed Registry reports `OK`.

### Task 3: Register real samples and regenerate the committed artifact

**Files:**
- Create: `skills/academic-writing-review/manifest.json`
- Create: `skills/evidence-audit/manifest.json`
- Create: `skills/writing-agent-router/manifest.json`
- Modify: `skill-registry/skill-registry.json` (generated only)
- Modify: `tests/skill_runtime/test_skill_runtime.py`

**Interfaces:**
- Each sample manifest points to its existing ZIP and its existing `SKILL.md` entry.
- The generated Registry contains exactly the three discovered sample Skill IDs for this milestone.
- The existing real-router integration test uses the discovered source directory and continues proving that the real ZIP definition can be loaded by the existing adapter.

- [ ] **Step 1: Add manifest fixtures and a real-sample assertion**

Create the three JSON files with `schema_version: "1.0"`, `version: "1.0.0"`, `enabled: true`, `provider_type: "procedural_skill"`, one or more concrete capabilities, one or more supported modes, required `task` input, object output, and `writes_artifacts: false/network: false` mutation declarations.

Add a test that discovers exactly these three manifest files and asserts that every generated Registry Skill has a real existing definition.

- [ ] **Step 2: Run the sample test before regenerating**

Run:
```bash
./.venv/bin/python -m pytest -q tests/skill_runtime/test_skill_runtime.py -k "real or manifest"
```

Expected: the new sample-discovery assertion fails until the builder and manifests are in place.

- [ ] **Step 3: Generate the committed Registry**

Run:
```bash
./.venv/bin/python scripts/build_skill_registry.py
```

Do not edit `skill-registry/skill-registry.json` by hand.

- [ ] **Step 4: Run Registry and full offline verification**

Run:
```bash
./.venv/bin/python scripts/build_skill_registry.py --check
./.venv/bin/python -m pytest -q tests/skill_runtime
```

Expected: `OK` and a complete offline suite with zero failures.

### Task 4: Document recovery and completion evidence

**Files:**
- Modify: `README.md`
- Modify: `skills/README.md`

**Interfaces:**
- Document `skills/<skill-id>/manifest.json` as the per-Skill metadata source.
- Document manifest validation, Registry build, drift check, test commands, and that the generated JSON is not hand-edited.
- State that only three samples are registered and the remaining ZIPs are intentionally outside this milestone.
- State that the Dify layer is not modified and that the semantic execution adapter remains host-specific.

- [ ] **Step 1: Update the two READMEs with exact commands**

Use:
```bash
./.venv/bin/python scripts/build_skill_registry.py
./.venv/bin/python scripts/build_skill_registry.py --check
./.venv/bin/python -m pytest -q tests/skill_runtime
```

- [ ] **Step 2: Run final verification and inspect the diff**

Run:
```bash
./.venv/bin/python scripts/build_skill_registry.py --check
./.venv/bin/python -m pytest -q tests/skill_runtime
git diff --check
git status --short
git diff --stat
```

Confirm that no Dify, dataset, log, checkpoint, or result file changed and that the Registry has no Skill ID without a real definition.

- [ ] **Step 3: Commit the completed milestone**

Run:
```bash
git add docs/superpowers/plans/2026-08-29-skill-registry-foundation.md skill_runtime/core.py scripts/build_skill_registry.py tests/skill_runtime/test_skill_runtime.py skills/academic-writing-review/manifest.json skills/evidence-audit/manifest.json skills/writing-agent-router/manifest.json skill-registry/skill-registry.json README.md skills/README.md
git commit -m "feat: add discoverable skill registry manifests"
```

- [ ] **Step 4: Re-run verification against the committed tree**

Run:
```bash
git status --short --branch
./.venv/bin/python scripts/build_skill_registry.py --check
./.venv/bin/python -m pytest -q tests/skill_runtime
```

Expected: the branch remains `snapshot/dify-agent-2026-08-29`, the committed Registry reports `OK`, and the focused offline tests report zero failures.
