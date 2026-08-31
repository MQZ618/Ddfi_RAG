# Dify Output Contract Regression

Date: 2026-08-30

## Result

`BLOCKED`

The requested 3-task × 3-run live regression was not started because the deployed Skill versions could not be confirmed.

## Precondition evidence

- Dify App API `/v1/info` returned `mode=agent` and `name=科研助手 Production v3`.
- Dify Console account endpoint returned HTTP 401 with `Invalid Authorization token.`.
- No authenticated Console response was available to prove that the rebuilt `nature-writing.zip` and `nature-polishing.zip` were uploaded and bound to the tested Agent.
- The local candidate ZIP hashes were recorded for later deployment verification:
  - `nature-writing.zip`: `16dee7190aa11982f444449cc945ee5c6739f3ee7478c5b7e1ce3c5c38ff47de`
  - `nature-polishing.zip`: `8b3e1f7c611597bd411c844a6bbb5e1c7c984237b00fb0b539e49db3bb30aa4f`

## Tests not run

T1-A, T2, and T9 were not called in this run. Running them against the current App would test an unverified deployment and would not establish whether the output-contract change was active.

## Unchanged

- No Dify configuration was changed.
- No Prompt, DSL, frontend, SSE, router, model, Knowledge, Tool, database, or Dify Core file was changed.
- No API secret was written to this report or Git.

## Unblock condition

Authenticate the Dify Console, upload and bind both ZIPs to the tested Agent, record the deployment/version evidence, and then run the fixed T1-A/T2/T9 suite three independent times each.
