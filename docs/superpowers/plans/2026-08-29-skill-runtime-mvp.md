# Skill Runtime MVP

## Goal

Deliver a small, local, verifiable runtime for the repository's writing skills:

- one explicit catalog as the source of truth;
- deterministic registry generation and drift detection;
- capability-based dispatch to an enabled registered skill;
- runtime-created invocation receipts;
- file-backed receipt and artifact storage with parent lineage;
- one integration test against the real `writing-agent-router.zip` package.

## Deliberate scope

Use Python standard library only. Do not modify Dify Core, the Dify UI, the DSL, or the existing ZIP packages. Do not implement an LLM phase router or pretend that loading a procedural `SKILL.md` is equivalent to a semantic model completion. The integration proves that the dispatcher loads the real package and emits runtime evidence; semantic writing execution remains a host-specific adapter concern.

## Implementation order

1. Add failing tests for manifest validation, registry hashing/drift, capability routing, receipt truthfulness, artifact lineage, storage, and security boundaries.
2. Implement `skill_runtime/core.py` with the registry, dispatcher, procedural ZIP adapter, receipt store, and artifact store.
3. Add the catalog for the 17 repository Skill ZIPs and generate the committed registry.
4. Run the focused suite, then the existing local tests and drift check.
5. Document the command and the explicit Dify boundary.

## Acceptance criteria

- no unregistered or disabled Skill can be dispatched;
- dispatch uses `capability` and `mode`, not an arbitrary Skill name/path;
- receipt status and `execution_confirmed` are written by the runtime;
- a failed adapter cannot produce a successful receipt;
- output artifact hash and parent input IDs are persisted;
- changing a package or manifest makes drift detection fail;
- the real router ZIP passes the integration test;
- no Dify source change is required for this MVP.
