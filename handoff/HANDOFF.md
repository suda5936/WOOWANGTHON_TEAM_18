# 새 세션 전달사항 — AI 에이전트 성능 개선 전/후 실측 비교

> 이 `handoff/` 폴더는 세션 인계용이다. **PR을 올리기 전에 `git rm -r handoff`로 지운다**(스크립트가 필요하면 스크래치패드로 옮겨 쓴다).

## 반드시 지킬 요청 (사용자 원문)

> 성능개선을 하기전과 성능개선 후의 성능을 수치적으로 비교해야해
> 테스팅일지 작성을 통해 비교기록
> https://claude.ai/artifact/WqskQJkKNgsxPdbyZpDwNy#3ad5d676-43db
> 일지 형식은 위 아티팩트처럼 하고
> 동일한 형식을 사용해서 새 아티팩트를 작성해서 기록해줘

추가 조건(사용자):
- 성능개선 메모의 항목은 다 반영하지 말고 **타당하다고 판단한 것만** 반영한다.
- 측정은 직접 만든 가짜 환경이 아니라 **지금까지 만든 실제 서비스(app.stairnoworks.com)에서 직접** 돌린다.
- 개선 코드는 **PR 머지 뒤** 운영 AI 서버(wcp-ai)에 배포한다(브랜치 바로 배포 아님).

주의: 위 일지 아티팩트는 이전 세션에서 열리지 않았다(Claude Docs `read`가 access 거부, Artifact `read`도 제목 "Claude Docs"만 보임). 새 세션에서 먼저 다시 읽어 본다. 그래도 안 되면 사용자에게 형식을 묻는다(문서의 "채팅 시작" 버튼으로 연 대화라면 읽힐 수 있다고 안내).

## 현재 상태

### 1. 개선 코드 — 완료, 푸시됨, PR 아직 없음
- 레포 `suda5936/WOOWANGTHON_TEAM_18`, 브랜치 `claude/determined-cray-3gq1oy`
  - `598d542` docs: 4차 리허설 결과 기록 (ai-scope, pitch)
  - `1bb4b29` fix: AI 에이전트 playbook · 지시문을 실제 게이트웨이 규칙에 맞추고 측정값을 남긴다
- 기준(개선 전) = `main` `af7fcc2`, 운영 이미지 `wcp-ai:4385d98`(같은 AI 코드)
- 반영: 1(없는 도구 제거, B1·B4·R1은 needs_user), 2(지시문: name/slug 금지, 도구별 한도, 재계획에 남은 호출 수), 3(verified specPatch를 통과한 시험에서 코드가 채움), 5(B2에서 EBADENGINE 경고 · 일반 SyntaxError 제거, B5·B3·B4 뒤로), 6(티켓에 로그가 있으면 첫 관찰 생략 가능 안내), 7(추적 로그 `act done` · `classify llm`에 `requests in_tokens out_tokens seconds`)
- 보류: 4(planner timeout/max_tokens — 값 정할 측정 없음, 추론 모델 출력 잘림 위험), 8·9·10(측정 뒤 결정)
- 검증: AI verify 통과(테스트 343), 손 mutant 9개 모두 잡힘. `docs/design/AIagent.md` §8 케이스 표 갱신. task 쌍 `tasks/active/20261114-agent-perf-{todo,lessons}.md`
- 남은 일: 측정 결과로 `docs/ai-scope.md` 배포 실패 에이전트 행 갱신, PR(한국어, 템플릿 따름) → 팀원 승인 · 머지 → EC2에서 `bash Infra/aws/deploy-ai.sh`(기본 origin/main)

### 2. 실서비스 고장 레포 — 완료
`suda5936/WOOWANGTHON_TEST_2` (세션에 add_repo push로 붙여야 함)

| 시나리오 | 커밋 | 고장 | 정답 |
| --- | --- | --- | --- |
| A1 | `main` c37ed32391f4f78541614ab3950c45e7eb77329c | spec 포트 8080, 앱 3000 | verified |
| B3 | `bench/b3-build-env` 0d806dad1f80d7be8a6525e9679d5d70f94b5e8a | 빌드 때 VITE_API_KEY 필요(비밀값) | needs_user |
| B4 | `bench/b4-import-case` da3ab573e37c366bd17a39e5281c7665d416dee2 | `require('../lib/Helper')` vs `lib/helper.js` | needs_user |
| B5w | `bench/b5-copy-missing` 412268ac6c0a86763c06fbcdff64bee4eb2fbfab | npm EBADENGINE 경고 + `COPY dist` 없음 | needs_user (개선 전 코드는 B2로 잘못 분류할 것) |

R1은 실서비스에서 일어날 수 없다(`BE/src/deploys/deploy-input.ts` `SERVICE_NAME`이 미리 막음) → 단위 테스트로만.
플랫폼은 레포 안 아무 커밋이나 받는다(`assertCommit`), 그래서 브랜치 커밋을 API로 배포한다.

### 3. 측정 스크립트 — 준비됨 (이 폴더에 첨부)
- `live_bench.py <label> <scenario> <n>`: 로그인 → `POST /api/deploys` → `GET .../secrets` → `POST .../start` → status 5초 폴링(단계 전환 시각 기록) → 전후 vLLM `/metrics` 카운터 차이(토큰 · 요청 · finished_reason) → `results/<label>-<scenario>-<n>.json`
- `collect.py <deployId> [result.json]`: DB `deploy_runs`(BE의 SUPABASE_SECRET_KEY를 SSM `/wcp/be`에서 메모리로만 읽어 SELECT만 — 사용자 승인 받음) + `wcp-ai` 추적 로그(SSM `docker logs -t wcp-ai | grep ticket`)
- `ssmrun.py "<cmd>"`: EC2 `i-01eeae171d57f9615`에 SSM 명령
- `offline_agent_bench.py`: 가짜 게이트웨이 하네스. **사용자가 실서비스 측정을 원해 쓰지 않기로 함**(참고용)
- 필요: `pip install boto3`, env `AWS_*`(이미 있음, STS 통과: IAM `wowang-suda`), `DEMO_EMAIL` · `DEMO_PASSWORD`(사용자가 환경변수로 넣기로 함, 채팅에 쓰지 말 것)
- 주의: python urllib는 403 → curl 사용(스크립트가 그렇게 함). 배포는 한 번에 하나씩 출발, 1회 약 10분. vLLM 동시 요청 1이라 팀원 리허설과 겹치지 않게.

## 할 일 순서
1. 일지 아티팩트 형식 다시 확인(위 주의).
2. 개선 전: 운영(`wcp-ai:4385d98`) 그대로 A1 · B3 · B4 · B5w 1회씩 `live_bench.py before <sc> 1` → 각 `collect.py`. A1은 기존 3차(207.6초) · 4차(223.9초) 기록도 기준선으로 쓸 수 있다.
3. `docs/ai-scope.md` 갱신 커밋 → PR → 머지 → `deploy-ai.sh` → `wcp-ai` 이미지 태그 확인.
4. 개선 후: 같은 4개 `live_bench.py after <sc> 1` → `collect.py`.
5. 같은 형식의 **새 아티팩트**로 테스팅일지 작성: 시나리오별 개선 전/후 — 최종 상태(정답 여부), 분류 case, 도구 호출 수 · 거절 수, AI 처리 시간(추적 `elapsed`), 시작~완료 시간, vLLM 토큰(입력/출력) · 요청 수 · `length` 잘림 수. 출처(추적 로그 줄, deploy_runs, vLLM 카운터) 명시. 1회씩이라 해결률 · 인과는 "미검증"으로.

## 참고 사실 (이전 세션 확인)
- 4차 리허설 `wanggane-memo-4`(de1e557d…): `succeeded`, 티켓 `t_f7945b5c8770`, A1 code 분류, playbook, 도구 4번(read_pod_logs → run_render → run_deploy → run_verify), 거절 0, 223.9초, 시작부터 613초. 3차: 207.6초, 603초.
- vLLM 누적(2026-11-14 측정 시점): 요청 44건 중 6건이 `finished_reason=length`(출력 상한에 잘림) — 일지에 적을 것.
- `deploys.spec`은 바뀌지 않고 AI가 고친 spec은 `deploy_runs.input`에만 들어간다 — 설계대로(api.md 5번 "저장").
- `TOOL_LIMIT`은 재계획 없이 바로 gave_up(stop code).
