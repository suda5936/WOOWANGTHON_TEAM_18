# Deploy prototype (W4 → W7 + AI agent) — shared plan for two parallel sessions

- **SRS**: none yet (FR table is empty). 현식 approved building without an FR on 2026-11-10; the work serves the deployer flow in `docs/design/deploy-workflow.md`.
- **Owner**: 현식 (suda5936)
- **Integration branch**: `dev/deploy-prototype` on the fork `suda5936/WOOWANGTHON_TEAM_18`. Both sessions start here and every feature merges back here.
- **Feature branches**: one `feat/<slug>` per todo slice, cut from the integration branch, merged back by a fork PR that 현식 reviews (§3 rule 5)
- **Session files**: [Session A todo](20261110-deploy-pipeline-todo.md) · [Session B todo](20261110-ai-agent-todo.md)

This file is the part both sessions share: the situation, the rules, the seam between the two tracks, and the checkpoints. Each session also has its own todo/lessons pair and edits only that pair. **This shared file is edited only when 현식 says so.**

## 1. Situation (read first)

- **What 현식 owns**: everything from "the platform server receives the deploy input JSON from W3" to "W7 done", plus the AI agent. That is: deploy input validation, slot choice, the GoCD pipeline (Build → Prepare → Render → Apply → Verify → Switch), collecting results, W7, the problem ticket, the AI agent that fixes a failed deploy, and the resolution that restarts the workflow. W0~W3, the FE screens and the cluster itself belong to teammates.
- **Design source of truth**: `docs/design/deploy-workflow.md`, `docs/design/deploy-handoff.md`, `docs/adr/009-*.md`, `docs/adr/011-*.md`, `docs/design/cluster.md` §6 · §8. These come from the fork branch `docs/deploy-handoff-blue-green` (tip `ed8d702`), which is in review as a fork PR into the team repo. **We build as if it were merged.** Changes from review are expected to be small.
- **Deadline**: first prototype by **2026-11-12 07:00 KST**. Plan written 2026-11-10 12:30 KST, so about 42 hours. Hackathon freeze is 2026-11-15 18:00 KST.
- **How we work**: two Claude Code sessions run in parallel without breaks. 현식 reviews, approves and suggests continuously. Inside a feature a session does not stop for questions that have a default (§3 rule 1); **between features it waits for his approval** (§3 rule 5).
- **What "prototype" means here** (§7 is the checkable form): the whole path exists as tested code and config, runs end to end against a local stand-in, and can be plugged into the real EC2 · GoCD · leader with a runbook. Real infra may not be ready in time (cluster build stages 08 · 09 · 09′ · 10 are still open, see `tasks/active/20261106-k3s-cluster-build-todo.md`), so nothing in the prototype may *depend* on it to be testable.

## 2. Split

| | Session A — build · deploy workflow | Session B — AI agent |
| --- | --- | --- |
| Goal | deploy input in → slot deploy → verify → switch → W7; on failure, a problem ticket out | problem ticket in → plan · act · verify → resolution out; fix PR when a repo file must change |
| Owns (only this session edits) | `Infra/charts/**`, `Infra/gocd/**`, `Infra/codebuild/**`, `BE/src/deploy/**`, `BE/test/deploy*.e2e.spec.ts`, `BE/db/**`, `docs/design/deploy-workflow.md`, `docs/design/deploy-handoff.md` | `AI/**`, `BE/src/agent/**`, `BE/test/agent*.e2e.spec.ts`, `docs/design/agent.md`, `.github/workflows/ai.yml` |
| Task pair | `20261110-deploy-pipeline-*` | `20261110-ai-agent-*` |

Shared files (both may touch, **own lines only, smallest diff**): `BE/src/app.module.ts`, `BE/src/config/env.ts` (+ its spec), `BE/.env.example`, `BE/package.json` + `pnpm-lock.yaml`, `docs/design/api.md`, `docs/ai-scope.md`, `docs/conventions.md` §6, `CLAUDE.md` Commands. On a lockfile conflict, take the other side's file and run `pnpm install`. Anything else outside your column: do not edit; write what you need in your lessons Log under `Needs from the other session` and keep going.

## 3. Rules for both sessions

1. **Inside a feature, do not stop to ask when a default exists.** Every open point in this plan has a default (§6, and `Open questions` in your todo). Take the default, write the question in your lessons Log under `Open questions for 현식`, continue. 현식 answers when he reviews the feature. Stop and ask only for: a change to the contract in §4, a secret you need, something destructive or irreversible, or a hard constraint in `CLAUDE.md` §1 you cannot satisfy.
2. **Repo rules win.** Read `CLAUDE.md` and `CONTRIBUTING.md` (the commit hook checks you opened it) and `docs/conventions.md` before the first commit. Code and tests land in the same commit. `pnpm verify` (BE) and the AI check command pass on every commit.
3. **No faked results** (`CLAUDE.md` §1.2, conventions F-1). A stand-in that the running app can return is a `MOCK(<id>)` with an `ai-scope.md` row in the same commit. Fakes that live only in tests need no marker. Never report a check you did not run as passed; say "not run" and why.
4. **No secrets in git or chat.** Keys come from the session environment. If you need one, say which host and why, then carry on with the parts that do not need it.
5. **One feature = one branch = one PR into the integration branch.** Never commit to the integration branch directly. For each todo slice:
   1. `git fetch origin dev/deploy-prototype` and cut `feat/<slug>` (the name is in your todo) from `origin/dev/deploy-prototype`.
   2. Build it with its tests, update your task pair in the same branch, `git push -u origin feat/<slug>`.
   3. Open a PR **inside the fork** (`suda5936/WOOWANGTHON_TEAM_18`, base `dev/deploy-prototype`, head `feat/<slug>`) with the repo PR template, in Korean. 현식 has authorized these fork PRs; never open one against the team repo.
   4. Post a short Korean status (done, test output, open questions, PR link, what the next feature is) and **stop. Do not start the next feature until 현식 approves.**
   5. If he asks for changes, fix them on the same feature branch and report again. When he approves (he merges the PR), go to step 1 for the next feature.
6. **Docs move with code.** API shape → `docs/design/api.md` first. A model, external API, library or tool added → `docs/ai-scope.md` in the same commit. A design detail that turned out different → fix the design doc you own, or log it for the other owner.
7. **Language**: reply to 현식 in Korean. Code, comments' identifiers, task files in English; design docs, ADRs, `ai-scope.md`, PR text in Korean. Follow the comment style already in `BE/src` (Korean "why" comments).
8. **PRs go to the fork only.** The sessions cannot reach the team repo; 현식 opens the PRs into the team repo himself. In every fork PR's notes say "mutation testing not run: no tool chosen" (conventions §6).
9. **When the handoff PR merges** into the team repo, 현식 brings the integration branch up to date and says so. Then merge `origin/dev/deploy-prototype` into your open feature branch, read what changed under `docs/design` and `docs/adr`, and adjust.

## 4. Contract between the two tracks (v0, frozen)

Both sessions code against this from the first hour. Session A puts the TypeScript types in `BE/src/deploy/contract.ts` as its first feature (`feat/deploy-contract`), merged before anything else; Session B mirrors them as pydantic models in `AI/`. A change needs 현식's OK and lands in this file first.

### 4.1 Deploy input

Exactly `docs/design/deploy-handoff.md` (`commitSha`, `deploy_condition`, `spec`). Not repeated here. It never carries secret values.

### 4.2 Problem ticket (A → B)

Built by code in the platform server when a pipeline run fails. No model is involved in building it.

```json
{
  "ticketId": "uuid",
  "runId": "uuid",
  "attempt": 1,
  "project": { "slug": "my-app", "repo": "student/my-app" },
  "commitSha": "40 hex",
  "targetSlot": "a",
  "stage": "build | prepare | render | apply | verify",
  "service": "be",
  "errorKind": "BUILD_FAILED | DRY_RUN_REJECTED | IMAGE_PULL | CRASH_LOOP | NOT_READY_TIMEOUT | PENDING | QUOTA_EXCEEDED | VERIFY_HTTP_FAILED | PIPELINE_TIMEOUT | UNKNOWN",
  "errorId": "stable fingerprint, e.g. verify:be:GET /api/health:404",
  "keyLogLines": ["at most 20 lines, secrets already masked"],
  "signals": {
    "podReason": "CrashLoopBackOff | null",
    "events": ["k8s event messages"],
    "http": { "path": "/api/health", "status": 404 }
  },
  "deployInput": { "...": "the deploy input of the failed run, deploy_condition.services filled" }
}
```

- `service` is `null` when the failure is not tied to one service. `signals` fields are `null` / `[]` when absent.
- `attempt` counts failures of the same stage for the same run chain. At `attempt: 2` after a resolution, the workflow does not call the agent again and reports instead (deploy-workflow §6).
- Platform problems (live-slot guard abort, GoCD unreachable, agent offline) never become tickets.

### 4.3 Resolution (B → A)

```json
{
  "ticketId": "uuid",
  "outcome": "resolved | user_action_required | unresolved",
  "resumeFrom": "w4",
  "specChanges": [
    { "service": "be", "path": "runtime.health.path", "from": "/health", "to": "/api/health", "reason": "..." }
  ],
  "fixPr": { "url": "https://github.com/student/my-app/pull/3", "forkCommitSha": "40 hex", "files": ["FE/vite.config.ts"] },
  "userAction": { "kind": "merge_pr | provide_secret | other", "message": "..." },
  "summary": "Korean, what was wrong and what was done",
  "evidence": ["log lines or file:line the conclusion rests on"],
  "usage": { "toolCalls": 7, "replans": 1, "redeploys": 1, "seconds": 212 }
}
```

- `resumeFrom` is `"w4"` only with `resolved`; otherwise `null`. `fixPr` and `userAction` are `null` when not used.
- `specChanges` is a report. The **working copy of the deploy input lives in the platform server**, keyed by `ticketId`; only the `spec_patch` tool changes it, one item per call, and every change is re-validated with the deploy-handoff rules. On `resolved`, the workflow restarts W4 with that working copy. The model's text never becomes the spec directly.
- A fixed repo file ends as `user_action_required` + `fixPr` + `userAction.kind: "merge_pr"` (deploy-workflow §6).

### 4.4 In-process seam inside `BE/` (TypeScript)

```ts
// Session A owns: BE/src/deploy/deploy.service.ts
startRun(input: DeployInput, opts?: { ticketId?: string; fixCheck?: { forkRepo: string; commitSha: string } }): Promise<{ runId: string }>
// opts.ticketId set  → agent's trial run: Switch is skipped, live_slot and W7 untouched
// opts.fixCheck set  → source is the bot fork commit, Switch is skipped (the one pipeline option in deploy-workflow §3)
getRun(runId: string): Promise<DeployRun>          // status, stage, targetSlot, per-stage result, failure → the ticket fields
getRunLogs(runId: string, stage: Stage, opts?: { service?: string; tail?: number }): Promise<string>
applyResolution(resolution: Resolution): Promise<void>   // resolved → restart W4 with the working copy; else mark the job and report

// Session B owns: BE/src/agent/agent.service.ts
submitTicket(ticket: ProblemTicket): Promise<void>  // stores the ticket + working copy, calls the AI server; throws if the AI server refuses
```

Until the other side exists, each session uses a test double **in tests only**. Session A calls `submitTicket` on failure; Session B's resolution callback calls `applyResolution`.

### 4.5 HTTP between BE and the AI server

| Call | Direction | Owner |
| --- | --- | --- |
| `POST {AI_SERVER_URL}/tickets` body = problem ticket → `202` | BE → AI | B |
| `POST /api/internal/agent/tools/<tool>` (9 tools, deploy-workflow §6) | AI → BE | B |
| `POST /api/internal/agent/resolutions` body = resolution → `204` | AI → BE | B |
| `POST /api/deploys` body = deploy input → `202 { runId }`, `GET /api/deploys/:runId` | W3 code · FE → BE | A |

Internal routes are `@Public()` for the user-token guard and instead require `Authorization: Bearer ${AGENT_SHARED_TOKEN}` (same value in BE and AI env; both run on the one EC2). Exact request/response shapes go into `docs/design/api.md` by the owner before the code.

Tool names (fixed): `repo_read`, `logs_read`, `memory_read`, `spec_patch`, `repo_edit`, `ask_user`, `trial_build`, `deploy_target`, `service_check`. Their schemas are Session B's `docs/design/agent.md`.

## 5. Checkpoints (KST)

The checkpoint is the state of the **integration branch**: the features listed must be merged there. Each session gets the other's work simply by cutting its next branch from the integration branch. The times assume 현식 approves each feature soon after it is reported; a feature waiting for approval is the main way this schedule slips.

| | When | Session A | Session B |
| --- | --- | --- | --- |
| S0 | 11-10 15:00 | `contract.ts` pushed; task pair filled | pydantic contract + `AI/` scaffold pushed |
| S1 | 11-10 23:00 | deploy input validation, Helm chart, stage scripts green on local tests | agent loop with guards runs a ticket to a resolution against a scripted model and a fake gateway (tests) |
| S2 | 11-11 11:00 | BE deploy module (start · poll · collect · W7 · ticket) and GoCD · CodeBuild config done; local cluster run of the stage scripts | BE gateway (tickets, tools, budgets, resolution callback) done on top of A's branch; real model call works if the key is there |
| S3 | 11-11 21:00 | **joint**: failing run → ticket → agent → `spec_patch` → trial run → resolution → W4 rerun passes, as one e2e test with a fake GoCD. Runbook ready; real-infra dry run with 현식 if infra is up | same e2e from the AI side; failure-injection set measured |
| S4 | 11-12 03:00 | feature freeze. Docs, `ai-scope.md`, known limits, PR notes | fix-PR path done or cut and declared; docs |
| End | 11-12 07:00 | prototype (§7) | |

Behind at a checkpoint → cut from the bottom of your todo (stretch first), say what was cut, never cut tests.

## 6. Defaults 현식 can veto (taken unless he says otherwise)

| # | Decision | Default | Why |
| --- | --- | --- | --- |
| D1 | Reasoning-model API | OpenAI, as written in deploy-workflow §7. Model name and key come from env (`OPENAI_MODEL`, `OPENAI_API_KEY`); no model name is hardcoded. Prototype uses the API for planning **and** tool selection ("API 대체 경로 먼저"); the leader vLLM comes after | the design already says so; vLLM is 후순위 |
| D2 | Tool gateway transport | plain authenticated HTTP routes in BE with the 9 tool names; wrapping them as an MCP server comes after the prototype | same safety checks, far less plumbing in 42 hours |
| D3 | GoCD pipeline shape | one generic pipeline `student-deploy`; the deploy input and options arrive as environment variables on the schedule API call. Deploys are serialized | simplest thing that works for the demo |
| D4 | Where deploy logic lives | Helm chart does the manifest logic (slots, links, probes, resource defaults, `NET_RAW` drop); stage scripts are thin bash (`jq`, `helm`, `kubectl`, `curl`, `aws`); everything else is TypeScript in BE | the leader agent needs no extra runtime; the chart is testable with `helm template` |
| D5 | Agent framework | none: a plain Python loop with the OpenAI SDK. Guards and verdicts are our code anyway | fewer moving parts; LangChain stays where ai-scope already lists it |
| D6 | DB access from BE | `@supabase/supabase-js` with a secret key in BE env; own tables only (`deploy_project`, `deploy_state`, `build_cache`, `deploy_run`, `problem_ticket`); SQL in `BE/db/` | teammates' tables do not exist yet; ours must not collide |
| D7 | BE ↔ AI auth | one shared bearer token | both on one EC2, not exposed |
| D8 | Results from pipeline to BE | stage scripts publish `result.json` and the rendered manifest as GoCD artifacts; BE fetches them through the GoCD API and writes the DB. The leader agent holds no DB credential | cluster.md §8 keeps the agent's rights narrow |

Out of the prototype: operating-time monitoring and the incident job, the local model, MCP transport, cancel-and-restart on a new commit mid-run, the restart-only path, security scans, FE screens, Kafka.

## 7. Done when (prototype, 2026-11-12 07:00 KST)

- [ ] `POST /api/deploys` with the example from `deploy-handoff.md` validates, picks the target slot, schedules the pipeline and returns a `runId`; a bad input is rejected with the rule it broke
- [ ] the stage scripts deploy a sample app to slot A, then a second run to slot B, verify through the test Ingress and switch the open Ingress, on a local cluster — or, if no local cluster can run in the session, on the real leader with 현식, and the status says which
- [ ] the live-slot guard aborts when the target slot is the live one, and that abort does not create a ticket
- [ ] a run that fails Verify because of a wrong health path produces a ticket; the agent reads the logs, patches one spec item, trial-deploys without switching, returns `resolved`; the workflow reruns from W4 and passes (e2e test, fake GoCD)
- [ ] agent budgets hold: a looping model is stopped by the guards and ends `unresolved`, not in a hang
- [ ] text sent to the external API has secret-looking strings masked (tested)
- [ ] `pnpm verify` in `BE/` and the AI check command are green on the integration branch
- [ ] `docs/design/api.md`, `docs/design/agent.md`, `docs/ai-scope.md` match the code; every `MOCK`/`SAMPLE` marker has its row
- [ ] a runbook lets 현식 install the pipeline on the real GoCD server and agents; what was and was not run on real infra is stated

## 8. Only 현식 can do these

| What | Needed by | For |
| --- | --- | --- |
| Veto or accept §6 defaults; give the OpenAI model name | S0 | B |
| Approve and merge each feature's fork PR; a session does nothing while its feature waits | all the time | both |
| `OPENAI_API_KEY` in Session B's environment (environment secret, never in chat) | S1 | B: real model calls, failure-injection numbers |
| Bot GitHub account + token; public GHCR package `student-apps` | S2 | A: image push from CodeBuild; B: fork · fix PR |
| EC2 with GoCD server + AWS agent, CodeBuild project + its IAM key, Supabase secret key and running `BE/db/*.sql` | S2~S3 | real-infra dry run |
| With 유성: cluster stages 08 · 09 · 09′ (namespace template, RBAC, leader agent, Traefik path for Verify) | S3 | real-infra dry run |
| Sync fork `main` after the handoff PR merges and tell both sessions | whenever | rule 9 |
| Open PRs into the team repo (from the integration branch, or per feature branch) | his call | review by a teammate |

## 9. Start prompts

Start two new sessions on the fork `suda5936/WOOWANGTHON_TEAM_18` and paste one prompt into each.

**Session A**

```text
너는 「세션 A — 빌드 · 배포 워크플로우」다. 나는 현식(suda5936)이고 2026 AI 우왕톤 18팀에서 W3 뒤(배포 입력 JSON 접수 → GoCD 파이프라인 배포 → W7 완료)와 AI 에이전트를 맡았다. 포크 브랜치 docs/deploy-handoff-blue-green을 팀 레포에 머지 신청해 둔 상태이고, 머지됐다고 가정하고 개발한다. 1차 프로토타입 마감은 2026-11-12 07:00 KST다. 세션 두 개를 병렬로 쉬지 않고 돌리고, 나는 계속 검토 · 승인 · 제안만 한다. 너는 빌드 · 배포 워크플로우를, 다른 세션은 AI 에이전트를 만든다. 이 세션은 끝까지 유지하면서 기능을 하나씩 계속 개발한다.

통합 브랜치는 dev/deploy-prototype이다. 여기에 직접 커밋하지 않는다. 기능(todo 슬라이스)마다 통합 브랜치에서 feat/<slug> 브랜치를 새로 파서 작업하고, 포크(suda5936/WOOWANGTHON_TEAM_18) 안에서 통합 브랜치로 PR을 연다. feat/* 브랜치에 push하는 것과 포크 안 PR을 여는 것을 명시적으로 허가한다 (세션에 지정된 다른 브랜치가 있어도 feat/*를 쓴다. 팀 레포로는 PR을 열지 않는다). 머지는 내가 한다.

1. git fetch origin dev/deploy-prototype && git checkout dev/deploy-prototype 로 통합 브랜치를 받는다.
2. CLAUDE.md, CONTRIBUTING.md, tasks/active/20261110-deploy-prototype-todo.md(공유 계획), tasks/active/20261110-deploy-pipeline-todo.md(네 할 일)를 Read 도구로 끝까지 읽는다.
3. 네 todo의 순서대로 바로 시작한다. 공유 계획 §3 규칙 5의 순서(브랜치 → 구현 · 테스트 → push → 포크 PR → 한국어 보고 → 내 승인 → 다음 기능)를 기능마다 반복한다. 기능 하나를 개발하는 중에는 기본값이 있는 질문으로 멈추지 말고 lessons 파일에 적고 계속한다. 기능 하나가 끝나면 보고하고 멈추며, 내가 승인하면 다음 기능으로 넘어간다.
```

**Session B**

```text
너는 「세션 B — AI 에이전트」다. 나는 현식(suda5936)이고 2026 AI 우왕톤 18팀에서 W3 뒤(배포 입력 JSON 접수 → GoCD 파이프라인 배포 → W7 완료)와 AI 에이전트를 맡았다. 포크 브랜치 docs/deploy-handoff-blue-green을 팀 레포에 머지 신청해 둔 상태이고, 머지됐다고 가정하고 개발한다. 1차 프로토타입 마감은 2026-11-12 07:00 KST다. 세션 두 개를 병렬로 쉬지 않고 돌리고, 나는 계속 검토 · 승인 · 제안만 한다. 너는 AI 에이전트를, 다른 세션은 빌드 · 배포 워크플로우를 만든다. 이 세션은 끝까지 유지하면서 기능을 하나씩 계속 개발한다.

통합 브랜치는 dev/deploy-prototype이다. 여기에 직접 커밋하지 않는다. 기능(todo 슬라이스)마다 통합 브랜치에서 feat/<slug> 브랜치를 새로 파서 작업하고, 포크(suda5936/WOOWANGTHON_TEAM_18) 안에서 통합 브랜치로 PR을 연다. feat/* 브랜치에 push하는 것과 포크 안 PR을 여는 것을 명시적으로 허가한다 (세션에 지정된 다른 브랜치가 있어도 feat/*를 쓴다. 팀 레포로는 PR을 열지 않는다). 머지는 내가 한다.

1. git fetch origin dev/deploy-prototype && git checkout dev/deploy-prototype 로 통합 브랜치를 받는다.
2. CLAUDE.md, CONTRIBUTING.md, tasks/active/20261110-deploy-prototype-todo.md(공유 계획), tasks/active/20261110-ai-agent-todo.md(네 할 일)를 Read 도구로 끝까지 읽는다.
3. 네 todo의 순서대로 바로 시작한다. 공유 계획 §3 규칙 5의 순서(브랜치 → 구현 · 테스트 → push → 포크 PR → 한국어 보고 → 내 승인 → 다음 기능)를 기능마다 반복한다. 기능 하나를 개발하는 중에는 기본값이 있는 질문으로 멈추지 말고 lessons 파일에 적고 계속한다. 기능 하나가 끝나면 보고하고 멈추며, 내가 승인하면 다음 기능으로 넘어간다.
```
