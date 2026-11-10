# Session B — AI agent (problem ticket → plan · act · verify → resolution)

- **SRS**: none yet (FR table empty; 현식 approved 2026-11-10)
- **Owner**: 현식 (suda5936), built by Claude Code session B
- **Branch**: `feat/ai-agent` (base: `claude/trusting-einstein-lt76nr`, which sits on `docs/deploy-handoff-blue-green`)
- **Shared plan (read first)**: [20261110-deploy-prototype-todo.md](20261110-deploy-prototype-todo.md) — situation, rules, contract §4, checkpoints §5, defaults §6

## Plan

The agent is the only place a model decides anything, so the code around it carries the safety: the model proposes a tool call, our code checks it against the budgets and rules, the platform gateway executes it, and **our code — not the model — judges whether the result fixed the ticket**. Build inside-out: contract and loop first against a scripted model and a fake gateway (tests only), then the real model client behind the outbound filter, then the gateway in `BE/src/agent/` on top of Session A's branch, then measure on a failure-injection set.

Start in `AI/` (empty today) so nothing depends on Session A for the first hours. Touch `BE/` only after merging `origin/feat/deploy-pipeline` at S1.

Read before coding: `docs/design/deploy-workflow.md` §6 · §7 and "알려진 한계", `docs/design/deploy-handoff.md` (the spec the agent patches), `docs/adr/002-*.md` (bot account fix PRs), `docs/ai-scope.md` §2 · §5, `docs/conventions.md` F-1.

## Todo

Order matters; S-numbers are the shared checkpoints.

- [ ] **B0 `AI/` scaffold** (by S0) — FastAPI app with `GET /health`, `uv` project, lint (ruff), typecheck, tests (pytest), one `verify`-style command that runs all three, Dockerfile, `.env.example`, CI workflow modelled on `.github/workflows/be.yml`. Record the tool choices in `docs/conventions.md` §6 ("Decided for AI"), the commands in `CLAUDE.md` Commands, the libraries in `docs/ai-scope.md` — files: `AI/**`, `.github/workflows/ai.yml`
- [ ] **B1 Contract models** (S0) — pydantic models for the problem ticket and the resolution exactly as shared plan §4.2 · §4.3; a test loads the JSON examples from the plan — files: `AI/app/contract.py`
- [ ] **B2 Design doc** (S1, before B3's code) — Korean, from `docs/design/TEMPLATE.md`: the loop, the 9 tool schemas (name, arguments, result, which budget it spends, what the gateway refuses), the verdict rules, the guards with their numbers, what goes to the external API and what is masked, failure behaviour — files: `docs/design/agent.md`
- [ ] **B3 Agent loop** (S1) — plan (hypotheses and check order) → act (one tool call) → verify (code verdict) → replan. Guards from deploy-workflow §6 as code with tests for each: same call twice in a row blocked, 3 replans, 2 redeploys, 2 trial builds, 20 tool calls, 1 fix PR, 15 min agent time, 30 min total. Every ending is one of the three outcomes; a guard trip ends `unresolved` with the reason. Tested with a scripted model and a fake gateway — files: `AI/app/agent/**`
- [ ] **B4 Verdict in code** (S1) — `resolved` only if a `deploy_target` + `service_check` after the last change passed; a repo-file fix that passed becomes `user_action_required` + `merge_pr`; the model cannot declare success by text — files: `AI/app/agent/verdict.py`
- [ ] **B5 Model client + outbound filter** (S2) — OpenAI SDK, model name and key from env, no default model name in code. Before any request leaves: mask Secret values, `.env` lines, token-looking strings (tests with realistic samples). No key or API failure → the ticket ends `unresolved` with a clear reason; no canned plan (F-1) — files: `AI/app/llm/**`
- [ ] **B6 Ticket intake** (S2) — `POST /tickets` → `202`, run the loop in the background, post the resolution to the BE callback with retries; shared bearer token — files: `AI/app/main.py`, `AI/app/tickets.py`
- [ ] **B7 BE gateway** (S2, after merging A) — `BE/src/agent/`: `submitTicket` (store ticket + working copy, call the AI server), the 9 tool routes, the resolution callback → `applyResolution`. The gateway re-checks budgets server-side and enforces the rules the model must not be trusted with (`docs/design/api.md` first) — files: `BE/src/agent/**`, `BE/test/agent*.e2e.spec.ts`
  - `repo_read` (path or listing at the ticket's commit, size cap, never `.env`), `logs_read` (A's `getRunLogs`), `memory_read` (past tickets and resolutions of this project)
  - `spec_patch` — one item per call, allow-listed paths under `spec.services[].build|runtime`, re-validated with A's validator, applied to the working copy
  - `deploy_target` — A's `startRun(workingCopy, { ticketId })`, waits for the result; `service_check` — the run's Verify result
  - `ask_user` — stores the question; the ticket ends `user_action_required`
  - `trial_build`, `repo_edit` — see B9 · stretch
- [ ] **B8 Failure-injection set** (S3) — prepared failing cases as ticket fixtures with the signals a real run gives: wrong port, wrong health path, missing required env (must end `user_action_required`, not a guess), Vite `base` path, wrong start command. Run the agent on each with the real model, record resolved / asked user / unresolved and tool-call counts, write the numbers into `docs/ai-scope.md` §2 as **미검증 → 검증됨 with the method**, or leave 미검증 and say why. The fixtures are `SAMPLE(<id>)` with a row in §3 — files: `AI/eval/**`
- [ ] **B9 Fix PR path** (S4) — `repo_edit`: commit changed files to a work branch on the bot fork, code checks (≤ 5 files, ≤ 50 changed lines, never `.env` · secrets · `.github/`, no secret-looking strings), `deploy_target` with `fixCheck`, and only after it passes open the PR into the student repo with cause · evidence · changed lines · check result; fork blocked → return patch text (ADR-002). Needs the bot token; without it, implement and test against a stubbed GitHub API and say it never ran for real
- [ ] **B10 Joint e2e** (S3) — with Session A: the "wrong health path" story of shared plan §7 end to end
- [ ] **B11 Docs** (S4) — `docs/ai-scope.md` §1 (OpenAI API, SDK, FastAPI versions) · §2 (agent row: model, role, human decision point, verification) · §5 limits, `docs/design/agent.md` matches the code, PR notes
- [ ] *Stretch, cut first*: `trial_build`; escalation to a stronger model after two identical failures; activity-log sentences for the report

## Open questions (take the default, log it, continue)

| # | Question | Default |
| --- | --- | --- |
| B-Q1 | Model name, monthly budget, data retention setting (deploy-workflow "정할 것" 4) | `OPENAI_MODEL` from env; until 현식 names one, tests use the scripted model and real calls wait |
| B-Q2 | One model for planning and tool selection, or two | one for the prototype (shared plan D1); keep the two call sites separate so the local model can take tool selection later |
| B-Q3 | Where "project memory" lives | read past `problem_ticket` rows and their resolutions; no separate memory store |
| B-Q4 | How the user answers `ask_user` | out of the prototype: the question is stored and shown by status; answering restarts with a new job |
| B-Q5 | Python version and package tool for `AI/` | Python 3.13, `uv`, pinned in `AI/pyproject.toml`; record in conventions §6 |

## Done when

- [ ] shared plan §7 items that name the agent are checked, with the command output in the Log
- [ ] each guard has a test that trips it
- [ ] the outbound filter test covers a Secret value, a `.env` line and a token-looking string
- [ ] `docs/ai-scope.md` says exactly what was verified with a real model and what was only tested with a scripted one
- [ ] tests added with each change; PR notes say "mutation testing not run: no tool chosen"
