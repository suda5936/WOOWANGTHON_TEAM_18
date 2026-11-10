# Session A — build · deploy workflow — lessons

## Log

- 2026-11-10: Task pair created from the shared plan; the session starts here.
- 2026-11-10 A0 `feat/deploy-contract`: `BE/src/deploy/contract.ts` holds the §4 types plus `StageResult` (the `result.json` shape A3 writes), `DeployRun`, `StartRunOptions`, and the two seam interfaces `DeployRunner` (A) / `TicketSink` (B). `BE/test/deploy-examples.ts` has the deploy-handoff example, the §4.2 ticket and the §4.3 resolution, typed; `contract.spec.ts` parses the first JSON block of `deploy-handoff.md` and checks it equals the fixture, so a doc edit that is not mirrored fails the test. `pnpm verify` green (8 files, 314 tests).
  - Additions beyond §4 (not contract changes, A-side only): `TicketStage = Exclude<Stage, 'switch'>` (a Switch failure is a platform problem, never a ticket); `StageErrorKind = ErrorKind | 'PLATFORM_ABORT'` (guard abort lives in `result.json` but never in a ticket); `signals.http` is `null` when there was no HTTP check; `DeployRun.status` is `scheduled | running | succeeded | failed | aborted`.

### Open questions for 현식

- A0-Q1: a Switch-stage failure — default: reported as a platform problem, not ticketed (`TicketStage` excludes `switch`), because the target slot already passed Verify and the agent has nothing to fix there. Say if it should be ticketed.

### Needs from the other session

## Lessons

<filled when done>
