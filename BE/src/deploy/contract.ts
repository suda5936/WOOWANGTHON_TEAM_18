// 배포 워크플로우(세션 A)와 AI 에이전트(세션 B) 사이의 약속(v0, 고정). 타입만 있고 동작은 없다.
// 원본: tasks/active/20261110-deploy-prototype-todo.md §4, docs/design/deploy-handoff.md. 바꾸려면 그 문서를 먼저 고친다.
// AI/ 쪽 pydantic 모델이 이 파일을 그대로 따라 한다.

/** 서비스마다 두 개 있는 배포 자리. 리소스 이름은 `<서비스>-a` · `<서비스>-b`. */
export type Slot = 'a' | 'b'

/** GoCD 파이프라인 `student-deploy`의 스테이지. 순서도 이대로다. */
export const STAGES = ['build', 'prepare', 'render', 'apply', 'verify', 'switch'] as const
export type Stage = (typeof STAGES)[number]

/** 티켓이 되는 스테이지. Switch는 open Ingress를 다시 적용할 뿐이라 실패해도 플랫폼 문제로 보고한다. */
export type TicketStage = Exclude<Stage, 'switch'>

export type Role = 'fe' | 'be' | 'ai'
export type Framework = 'vite-react' | 'nextjs' | 'nest'

// ---- 배포 입력 (docs/design/deploy-handoff.md) ----

export interface BuildSpec {
  context: string
  dockerfile: string | null
  framework: Framework | null
  nodeVersion: string | null
  install: string | null
  build: string | null
  start: string | null
  outputDir: string | null
  buildEnv: Record<string, string>
}

export interface HealthSpec {
  type: 'http' | 'tcp'
  path: string | null
  startupTimeoutSeconds: number
}

export interface Link {
  env: string
  service: string
}

/** 요청과 상한에 같은 값을 쓴다. 예: `{ cpu: '500m', memory: '512Mi' }`. */
export interface Resources {
  cpu: string
  memory: string
}

export interface RuntimeSpec {
  kind: 'server' | 'static'
  port: number
  health: HealthSpec
  env: Record<string, string>
  secretKeys: string[]
  links: Link[]
  ingressPath: string | null
  stripPrefix: boolean
  resources: Resources | null
}

export interface ServiceSpec {
  name: string
  role: Role
  dir: string
  build: BuildSpec
  runtime: RuntimeSpec
}

export interface ProjectRef {
  slug: string
  /** 학생 레포 `owner/name`. */
  repo: string
}

export interface DeploySpec {
  project: ProjectRef
  services: ServiceSpec[]
}

/** W4가 서비스마다 채운다. `reuse`면 `image`가 처음부터 있고, `run`이면 빌드 뒤에 채운다. */
export interface ServiceCondition {
  buildInputHash: string
  build: 'run' | 'reuse'
  image: string | null
}

export interface DeployCondition {
  secretHash: string | null
  /** W3까지는 항상 null. 키는 `spec.services[].name`. */
  services: Record<string, ServiceCondition> | null
}

/** W3 → W4로 넘어오는 JSON. 비밀값은 없다(key 이름만 `runtime.secretKeys`에). */
export interface DeployInput {
  commitSha: string
  deploy_condition: DeployCondition
  spec: DeploySpec
}

// ---- 스테이지 결과 (stage 스크립트의 result.json) ----

export const ERROR_KINDS = [
  'BUILD_FAILED',
  'DRY_RUN_REJECTED',
  'IMAGE_PULL',
  'CRASH_LOOP',
  'NOT_READY_TIMEOUT',
  'PENDING',
  'QUOTA_EXCEEDED',
  'VERIFY_HTTP_FAILED',
  'PIPELINE_TIMEOUT',
  'UNKNOWN',
] as const
export type ErrorKind = (typeof ERROR_KINDS)[number]

/** 스테이지가 내는 실패 종류. `PLATFORM_ABORT`(live 슬롯 보호 중단 등)는 티켓이 되지 않는다. */
export type StageErrorKind = ErrorKind | 'PLATFORM_ABORT'

export interface Signals {
  podReason: string | null
  events: string[]
  http: { path: string; status: number | null } | null
}

/** 스테이지 스크립트가 성공 · 실패 모두 남기는 결과. 티켓은 로그를 긁지 않고 이것으로 만든다. */
export interface StageResult {
  ok: boolean
  stage: Stage
  service: string | null
  errorKind: StageErrorKind | null
  errorId: string | null
  keyLogLines: string[]
  signals: Signals
}

// ---- 실행 기록 ----

export type RunStatus = 'scheduled' | 'running' | 'succeeded' | 'failed' | 'aborted'

export interface DeployRun {
  runId: string
  slug: string
  commitSha: string
  targetSlot: Slot
  status: RunStatus
  /** 지금 돌고 있거나 마지막으로 끝난 스테이지. 스케줄 직후에는 null. */
  stage: Stage | null
  /** 에이전트의 시험 실행이면 그 티켓. 이때 Switch를 건너뛰고 live_slot · W7을 건드리지 않는다. */
  ticketId: string | null
  /** 수정 PR 확인 실행이면 봇 fork 커밋. 이때도 Switch를 건너뛴다. */
  fixCheck: FixCheck | null
  stages: StageResult[]
  /** 실패했으면 실패한 스테이지의 결과(티켓의 재료). 아니면 null. */
  failure: StageResult | null
  /** W7에서 채우는 공개 주소. */
  address: string | null
  warnings: string[]
  deployInput: DeployInput
  createdAt: string
  updatedAt: string
}

export interface FixCheck {
  forkRepo: string
  commitSha: string
}

export interface StartRunOptions {
  ticketId?: string
  fixCheck?: FixCheck
}

// ---- 문제 티켓 (A → B) ----

export interface ProblemTicket {
  ticketId: string
  runId: string
  /** 같은 실행 묶음에서 같은 스테이지가 실패한 횟수. 해결 뒤 2가 되면 에이전트를 부르지 않는다. */
  attempt: number
  project: ProjectRef
  commitSha: string
  targetSlot: Slot
  stage: TicketStage
  /** 한 서비스에 묶이지 않는 실패면 null. */
  service: string | null
  errorKind: ErrorKind
  /** 안정된 지문. 예: `verify:be:GET /api/health:404`. */
  errorId: string
  /** 최대 20줄, 비밀값은 이미 가렸다. */
  keyLogLines: string[]
  signals: Signals
  /** 실패한 실행의 배포 입력(`deploy_condition.services` 채워짐). */
  deployInput: DeployInput
}

// ---- 해결 결과 (B → A) ----

export type Outcome = 'resolved' | 'user_action_required' | 'unresolved'

export interface SpecChange {
  service: string
  /** 서비스 안 경로. 예: `runtime.health.path`. */
  path: string
  from: unknown
  to: unknown
  reason: string
}

export interface FixPr {
  url: string
  forkCommitSha: string
  files: string[]
}

export interface UserAction {
  kind: 'merge_pr' | 'provide_secret' | 'other'
  message: string
}

export interface Resolution {
  ticketId: string
  outcome: Outcome
  /** `resolved`일 때만 `'w4'`. */
  resumeFrom: 'w4' | null
  /** 보고용. 실제 작업 사본은 플랫폼 서버가 ticketId로 들고 있다. */
  specChanges: SpecChange[]
  fixPr: FixPr | null
  userAction: UserAction | null
  /** 한국어. 무엇이 문제였고 무엇을 했는지. */
  summary: string
  evidence: string[]
  usage: { toolCalls: number; replans: number; redeploys: number; seconds: number }
}

// ---- BE 안의 이음매 (§4.4) ----

/** 세션 A가 구현한다: BE/src/deploy/deploy.service.ts. */
export interface DeployRunner {
  startRun(input: DeployInput, opts?: StartRunOptions): Promise<{ runId: string }>
  getRun(runId: string): Promise<DeployRun>
  getRunLogs(runId: string, stage: Stage, opts?: { service?: string; tail?: number }): Promise<string>
  applyResolution(resolution: Resolution): Promise<void>
}

/** 세션 B가 구현한다: BE/src/agent/agent.service.ts. AI 서버가 거절하면 throw한다. */
export interface TicketSink {
  submitTicket(ticket: ProblemTicket): Promise<void>
}
