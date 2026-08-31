# Research Writing Naturalness v4

## Purpose

Reduce three reader-visible artifacts in the scientific-writing Agent:

1. overly uniform subsection length and paragraph rhythm;
2. dense sentences that carry several unrelated logical functions;
3. automatic significance or transition sentences at the end of every paragraph or subsection.

The change is a writing-policy refinement. It does not add research claims, evidence, citations, tools, knowledge, model configuration, or Dify Core behavior.

## Non-negotiable invariants

- Evidence boundary, closed-world transformation, user authorization, and the author's original claims have priority over style heuristics.
- No substantive fact, result, citation, mechanism, causal direction, scope, uncertainty level, or limitation may drift during polishing.
- Sentence length and paragraph length are diagnostic signals, not output quotas.
- A paragraph may stop when its evidence unit, method explanation, or qualification is complete.
- A short ablation may be one compact paragraph; a central result may need several paragraphs.
- Review-only remains review-only unless the user explicitly authorizes rewriting.
- The previous v3 live Prompt and DSL remain rollback baselines.

## Layer responsibilities

### Prompt

The v4 Prompt defines global precedence, knowledge-completeness checks, evidence-weighted allocation, naturalness review, minimal edit, and conflict arbitration.

### Skills

The four academic skills diagnose local problems and offer conditional structures. They must not turn sentence ranges, paragraph jobs, subsection order, or closing inference into mechanical templates.

### DSL

The v4 candidate is generated from the v3 live snapshot by replacing only the system Prompt. Model, tools, knowledge, agent parameters, and historical snapshots stay unchanged.

## Acceptance gates

- RED tests fail on the pre-change Skill packages and missing v4 files for the expected reasons.
- Skill package tests, Prompt tests, full pytest, Registry drift check, and ZIP integrity checks pass.
- The v4 candidate parses and validates without credentials.
- A structural comparison finds no non-Prompt DSL change.
- No Dify Console save, publish, or Active-production claim is made without a real authenticated host response.
- Long-run and A/B evidence remains separate from offline repository readiness.

## Known platform limitation

The known PostgreSQL physical-file error `could not open file "base/16384/16785"` is a Dify runtime blocker for the long three-report run. This task records it and does not repair the database, modify Dify Core, rebuild images, or change the primary model.
