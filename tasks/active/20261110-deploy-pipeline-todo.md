# Session A — build · deploy workflow (deploy input → GoCD pipeline → W7)

- **SRS**: none yet (FR table empty; 현식 approved 2026-11-10)
- **Owner**: 현식 (suda5936), built by Claude Code session A
- **Branch**: one `feat/<slug>` per slice below, cut from and merged back into the integration branch `dev/deploy-prototype` by a fork PR (shared plan §3 rule 5)
- **Shared plan (read first)**: [20261110-deploy-prototype-todo.md](20261110-deploy-prototype-todo.md) — situation, rules, contract §4, checkpoints §5, defaults §6

## Plan

Build the path in the order the data flows, each slice testable without real infra. The manifest logic goes into one Helm chart so the stage scripts stay thin; the platform-side logic (validation, slot choice, build cache, GoCD calls, W7, ticket) is a Nest module `BE/src/deploy/`. GoCD and CodeBuild are reached only through small clients that tests replace by stubbing `fetch` / a fake `kubectl` · `aws` on `PATH` — the same pattern the BE tests already use. The real-infra hookup is a runbook 현식 runs.

Read before coding: `docs/design/deploy-workflow.md` (all), `docs/design/deploy-handoff.md` (all), `docs/adr/009-*.md`, `docs/adr/011-*.md`, `docs/design/cluster.md` §6 · §8, then `BE/src/repos/` and `BE/test/` for the house style.

## Todo

Order matters; S-numbers are the shared checkpoints. The name after each title is that slice's branch.

- [x] **A0 Contract types** `feat/deploy-contract` (by S0) — `DeployInput`, `ProblemTicket`, `Resolution`, `DeployRun`, `Stage`, `Slot` exactly as shared plan §4 — files: `BE/src/deploy/contract.ts`. Push at once; Session B waits on it.
- [ ] **A1 Deploy input validation** `feat/deploy-input-validation` (S1) — every row of the validation table in `deploy-handoff.md`, including the resource sum × 2 against the ResourceQuota; the error names the rule and the field. Pure function, table-driven tests using the doc's example as the valid case — files: `BE/src/deploy/deploy-input.ts`, `.spec.ts`
- [ ] **A2 Helm chart `student-app`** `feat/student-app-chart` (S1) — per service and slot: Deployment · Service · ConfigMap named `<service>-<slot>`, labels `app` · `slot`, `startupProbe` · `readinessProbe` from `runtime.health` (periods and thresholds in deploy-workflow §4), resource defaults when `resources` is `null`, `capabilities.drop: ["NET_RAW"]`, `envFrom` Secret `<service>-secrets` only when `secretKeys` is not empty, `links` → `http://<service>-<slot>:<port>`, image by digest. Separate toggles render the open Ingress and the test Ingress (same path rules, `stripPrefix` via Traefik middleware) pointing at a given slot. No NetworkPolicy · ResourceQuota · LimitRange in the chart. Tests: `helm template` output asserted per rule (a script or helm-unittest, whichever installs) — files: `Infra/charts/student-app/**`
- [ ] **A3 Stage scripts** `feat/deploy-stage-scripts` (S1) — one script per stage, input = deploy input JSON + target slot + options from env, output = `result.json` (`ok`, `stage`, `service`, `errorKind`, `signals`, key log lines) on success **and** failure, so the ticket never needs log scraping — files: `Infra/gocd/stages/{build,prepare,render,apply,verify,switch}.sh`, tests under `Infra/gocd/test/`
  - `prepare`: live-slot guard (read the open Ingress; abort with a distinct `PLATFORM_ABORT` result if any backend is the target slot or backends disagree; no Ingress = first deploy, go on), then delete Deployments · Services · ConfigMaps labelled with the target slot
  - `render`: deploy input + images + slot → values → `helm template` → `kubectl apply --dry-run=server`; publish the manifest as an artifact
  - `apply`: AI → BE → FE, `kubectl rollout status` with the per-service timeout (startup + 120 s, max 7 min); on timeout collect Pod reason and events into `signals`
  - `verify`: Pod Ready + Endpoints, apply the test Ingress, request `/`, the page's JS · CSS, and each BE health path through Traefik with Host `<slug>.test.internal` (10 s, 3 tries, 5 s apart)
  - `switch`: apply the open Ingress pointing at the target slot; skipped when the run is a trial or a fix check
  - `build`: per service, `reuse` → nothing; `run` → start CodeBuild, wait, read the pushed digest; write `images.json`
- [ ] **A4 Local cluster run** `feat/deploy-local-cluster-run` (S2) — if the Docker daemon works in the session, bring up k3d or kind with Traefik and run prepare → switch for a small public sample image: first deploy to A, second to B, guard abort case, wrong-health-path failure case. If it cannot run here, say so in the Log and move this to the runbook dry run; do not mark it done.
- [ ] **A5 DB tables** `feat/deploy-db` (S2) — SQL for `deploy_project (slug, repo, live_slot)`, `deploy_state (slug, slot, deploy_input, manifest, images)`, `build_cache (service key, build_input_hash, image)`, `deploy_run`, and the access code — files: `BE/db/*.sql`, `BE/src/deploy/deploy.store.ts`
- [ ] **A6 BE deploy module** `feat/deploy-run-api` (S2) — `startRun` (validate → target slot = opposite of `live_slot`, first is A → `buildInputHash` per service from GitHub tree · blob SHAs → `build_cache` lookup → fill `deploy_condition.services` → schedule the GoCD pipeline), a poller that follows the run through the GoCD API and pulls `result.json` · manifest · logs, `getRun`, `getRunLogs`, and `POST /api/deploys` · `GET /api/deploys/:runId` (write `docs/design/api.md` first) — files: `BE/src/deploy/**`
- [ ] **A7 W7 and failure** `feat/deploy-w7-ticket` (S2) — success: set `live_slot`, scale the previous live slot's Deployments to 0, record address · status · warnings on the run. Failure: build the problem ticket from `result.json` (shared plan §4.2) and call `submitTicket`; `PLATFORM_ABORT` and GoCD · agent outages are reported, not ticketed. `applyResolution`: `resolved` → restart W4 with the working copy; second failure of the same stage after a resolution → report without calling the agent
- [ ] **A8 GoCD and CodeBuild config** `feat/gocd-codebuild-config` (S2) — pipeline-as-code for `student-deploy` (six stages, Build on the `aws` agent resource, the rest on `leader`, 30 min job timeout, artifacts between stages), CodeBuild `buildspec.yml`, platform default Dockerfiles for `vite-react` · `nextjs` · `nest`, image tag `<slug>-<name>-<hash 12>` in `ghcr.io/<bot>/student-apps` — files: `Infra/gocd/*.gocd.yaml`, `Infra/codebuild/**`. Build each default Dockerfile once against a tiny sample app if Docker works here.
- [ ] **A9 Joint e2e** `feat/deploy-agent-e2e` (S3) — once Session B's gateway is in the integration branch: the "wrong health path" story from shared plan §7 as one BE e2e test with a fake GoCD — files: `BE/test/deploy-agent.e2e.spec.ts`
- [ ] **A10 Runbook** `feat/deploy-runbook` (S3) — Korean, step by step: GoCD server config repo, agent resources and tools each agent needs, CodeBuild project + IAM, env vars, how to run the first real deploy and what to look at — files: `Infra/gocd/README.md`
- [ ] **A11 Docs** `feat/deploy-docs` (S4) — `docs/ai-scope.md` rows (GoCD, CodeBuild, Helm, anything installed), `BE/.env.example`, `CLAUDE.md` Commands if a new check command exists, design-doc corrections, known limits
- [ ] *Stretch, cut first*: fix-check run option end to end with a real fork commit; cancel-and-restart when a new commit arrives mid-run

## Open questions (take the default, log it, continue)

| # | Question | Default |
| --- | --- | --- |
| A-Q1 | Prepare must confirm required Secret keys exist, but the leader agent may not read Secrets (cluster.md §8) and the design does not say where the key names are left | BE checks its own record of key names before scheduling; Prepare does not check. Log it for 현식 and 유성 |
| A-Q2 | Trial runs for a ticket need "no Switch" without a fork source, while deploy-workflow §3 names one option (fork source + no Switch) | one pipeline variable `SKIP_SWITCH` and one optional source override; the design doc gets a one-line clarification |
| A-Q3 | GitHub API for tree SHAs is unauthenticated today (60 requests/hour per IP) | use it as is; note the limit in known limits; bot token later |
| A-Q4 | `deploy_project` vs a teammate's future projects table | keep our own table; rename or merge when theirs lands |

## Done when

- [ ] shared plan §7 items that name the deploy side are checked, with the command output in the Log
- [ ] every stage script has a failing-case test, not only the happy path
- [ ] tests added with each change; PR notes say "mutation testing not run: no tool chosen"
- [ ] what ran on a local cluster, what ran only against fakes, and what never ran is written down plainly
