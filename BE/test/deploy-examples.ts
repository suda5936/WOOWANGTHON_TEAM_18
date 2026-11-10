import type { DeployInput, ProblemTicket, Resolution } from '../src/deploy/contract.js'

// docs/design/deploy-handoff.md의 예시를 그대로 옮긴 것. contract.spec.ts가 문서와 같은지 확인한다.
// 배포 테스트는 이것을 유효한 입력으로 쓰고, 고쳐 볼 칸만 바꾼다(structuredClone 뒤).
export const exampleInput: DeployInput = {
  commitSha: 'a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2',
  deploy_condition: { secretHash: 'sha256:...', services: null },
  spec: {
    project: { slug: 'my-app', repo: 'student/my-app' },
    services: [
      {
        name: 'fe',
        role: 'fe',
        dir: 'FE',
        build: {
          context: 'FE',
          dockerfile: null,
          framework: 'vite-react',
          nodeVersion: '22',
          install: 'pnpm install --frozen-lockfile',
          build: 'pnpm run build',
          start: null,
          outputDir: 'dist',
          buildEnv: { VITE_API_URL: '/api' },
        },
        runtime: {
          kind: 'static',
          port: 8080,
          health: { type: 'http', path: '/', startupTimeoutSeconds: 10 },
          env: {},
          secretKeys: [],
          links: [],
          ingressPath: '/',
          stripPrefix: false,
          resources: null,
        },
      },
      {
        name: 'be',
        role: 'be',
        dir: 'BE',
        build: {
          context: '.',
          dockerfile: 'BE/Dockerfile',
          framework: null,
          nodeVersion: null,
          install: null,
          build: null,
          start: null,
          outputDir: null,
          buildEnv: {},
        },
        runtime: {
          kind: 'server',
          port: 3000,
          health: { type: 'http', path: '/api/health', startupTimeoutSeconds: 60 },
          env: { NODE_ENV: 'production' },
          secretKeys: ['DATABASE_URL'],
          links: [{ env: 'AI_URL', service: 'ai' }],
          ingressPath: '/api',
          stripPrefix: false,
          resources: null,
        },
      },
      {
        name: 'ai',
        role: 'ai',
        dir: 'AI',
        build: {
          context: 'AI',
          dockerfile: 'AI/Dockerfile',
          framework: null,
          nodeVersion: null,
          install: null,
          build: null,
          start: null,
          outputDir: null,
          buildEnv: {},
        },
        runtime: {
          kind: 'server',
          port: 8000,
          health: { type: 'http', path: '/health', startupTimeoutSeconds: 120 },
          env: {},
          secretKeys: ['OPENAI_API_KEY'],
          links: [],
          ingressPath: null,
          stripPrefix: false,
          resources: null,
        },
      },
    ],
  },
}

const SHA = 'a1b2c3d4e5f6a1b2c3d4e5f6a1b2c3d4e5f6a1b2'
const HASH = `sha256:${'0'.repeat(64)}`

/** 공유 계획 §4.2 예시: 헬스체크 경로가 틀려 Verify가 404로 실패했다. */
export const exampleTicket: ProblemTicket = {
  ticketId: '00000000-0000-4000-8000-000000000001',
  runId: '00000000-0000-4000-8000-000000000002',
  attempt: 1,
  project: { slug: 'my-app', repo: 'student/my-app' },
  commitSha: SHA,
  targetSlot: 'a',
  stage: 'verify',
  service: 'be',
  errorKind: 'VERIFY_HTTP_FAILED',
  errorId: 'verify:be:GET /api/health:404',
  keyLogLines: ['GET http://my-app.test.internal/api/health -> 404'],
  signals: { podReason: null, events: [], http: { path: '/api/health', status: 404 } },
  deployInput: {
    ...exampleInput,
    deploy_condition: {
      secretHash: null,
      services: {
        fe: { buildInputHash: HASH, build: 'reuse', image: `ghcr.io/bot/student-apps@${HASH}` },
        be: { buildInputHash: HASH, build: 'reuse', image: `ghcr.io/bot/student-apps@${HASH}` },
        ai: { buildInputHash: HASH, build: 'reuse', image: `ghcr.io/bot/student-apps@${HASH}` },
      },
    },
  },
}

/** 공유 계획 §4.3 예시: spec 항목 하나를 고쳐 해결했다. */
export const exampleResolution: Resolution = {
  ticketId: exampleTicket.ticketId,
  outcome: 'resolved',
  resumeFrom: 'w4',
  specChanges: [{ service: 'be', path: 'runtime.health.path', from: '/health', to: '/api/health', reason: '앱은 /api/health에서 답한다' }],
  fixPr: null,
  userAction: null,
  summary: '헬스체크 경로가 앱과 달라 확인이 404로 실패했다. 경로를 고치고 대상 슬롯에서 확인했다.',
  evidence: ['GET /api/health -> 404'],
  usage: { toolCalls: 7, replans: 1, redeploys: 1, seconds: 212 },
}
