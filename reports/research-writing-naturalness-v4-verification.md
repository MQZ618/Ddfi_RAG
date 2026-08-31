# Research Writing Naturalness v4 Verification

Date: 2026-08-30

## Scope

This verification covers the repository candidate for the naturalness revision of the scientific-writing Agent. It does not claim that v4 is saved, published, or active in Dify.

## Repository state

- Canonical checkout: `/Users/mqzzz/Desktop/LLM辅助科研系统/Ddfi_RAG-github-snapshot`
- Branch: `main`
- Baseline HEAD at start: `b7814d9f`
- Remote: `git@github.com:MQZ618/Ddfi_RAG.git`
- The checkout was already ahead of `origin/main` by six commits; this task did not push.
- v3 Prompt and v3 live DSL were preserved as rollback baselines.

## Implemented repository changes

- Added `prompts/科研助手-production-v4.md` with style-conflict arbitration, evidence-weighted allocation, knowledge-completeness checks, sentence-load review, and minimal-edit rules.
- Rebuilt `skills/academic-writing-review.zip` with explicit naturalness diagnostics and a diagnose-before-rewriting boundary.
- Rebuilt `skills/results-section-revision.zip` so subsection closures, transitions, openings, and lengths are conditional on evidence rather than fixed templates.
- Rebuilt `skills/nature-polishing.zip` so sentence length is a review signal and overloaded logical functions, not visual line count, determine splitting.
- Rebuilt `skills/nature-writing.zip` so paragraph jobs, evidence ladders, Method triads, Introduction length, and Discussion responsibilities are flexible contracts.
- Updated `skills/README.md` and `skills/WRITING_AGENT_MANIFEST.md` to describe the versioned package changes and the unchanged `remove-ai-flavor` boundary.
- Generated `agentDSL/科研助手-production-v4-naturalness-candidate.yml` from `agentDSL/科研助手-production-v3-live.yml` with the existing builder.
- Added `tests/skill_runtime/test_natural_writing_skill_packages.py`.
- Regenerated `skill-registry/skill-registry.json` with the official registry builder after the ZIP changes.

## Offline verification

| Check | Result |
|---|---|
| Natural-writing regression | `10 passed` |
| Agent DSL tests | `9 passed` |
| Full repository pytest | `68 passed` |
| Registry drift check | `OK` |
| DSL validation | `OK` with expected missing-upload warnings for Dify Skill assets |
| Four ZIP integrity checks | all `No errors detected in compressed data` |
| `git diff --check` | passed |
| Web client regression | `36 passed` |

The DSL structural test confirms that the candidate differs from the v3 live source only in `agent_packages.agent_1.soul.prompt.system_prompt`; model, Tool, Knowledge, agent settings, and historical DSL files were not changed.

## Dify host evidence

The local App API preflight, using the ignored local environment file without exposing its secret, returned:

- `mode: agent`
- `name: 科研助手 Production v3`
- file upload enabled with local-file method and a three-file limit

The runtime chat endpoint was then probed with a minimal streaming request. The real response was:

```text
{"code":"agent_not_published","message":"Agent has not been published. Please publish the Agent before using the API.","status":400}
```

The Dify Console management endpoints were checked without credentials. They returned `401 Invalid Authorization token`. The current session did not expose an authenticated Console control surface, and the available browser-control runtime was not callable in this session. Consequently, no new Agent was created and no v4 Draft was saved.

## A/B and release status

The required v3 Active versus v4 Draft A/B run was not executed because there is no v4 Draft and the current v3 App API reports `agent_not_published`. Therefore this report does not claim:

- Skill upload or binding;
- Draft save;
- Composer validation;
- Active publication;
- writing-quality improvement;
- factual-drift result from a live A/B comparison.

The three-report long-run PostgreSQL blocker remains recorded as `DIFY-DB-001` in `bug记录/Dify_Postgres_Physical_File_Missing.md`. It was not repaired.

## Additional test note

The legacy `pytest -q tests/dify_workflow` command remains independently unhealthy: `13 passed, 3 errors, 13 warnings`. The three errors are missing pytest fixture `results` in `test_11_rag_status_consistency`, `test_12_internal_leakage`, and `test_13_duplicate_output`; the warnings are existing tests returning dictionaries. This task did not modify those legacy tests because they are outside the naturalness scope.

## Readiness judgment

- Repository candidate: ready for review and import preparation.
- Dify Draft: not ready; Console authentication and an unpublished current App block synchronization.
- Dify Active production: not ready; no publish or Composer evidence exists.
- Dify platform/runtime limitation: Console authentication is unavailable in this session; current App runtime also requires publication, and the known PostgreSQL physical-file corruption blocks the long three-report run.

Next unblock condition: authenticate the Dify Console, create a separate `科研助手 Production v4` Draft using the candidate and four rebuilt Skill packages, run Composer validation, then run the specified blinded three-repeat A/B suite before any publication decision.
