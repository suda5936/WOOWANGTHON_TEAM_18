"""AI 에이전트 성능 측정 하네스 (개선 전/후 비교용).

실제 모델(ai.env의 LOCAL_MODEL_* / PLANNER_MODEL_*)과, BE 게이트웨이 규칙을 흉내 낸
가짜 게이트웨이로 시나리오를 돌린다. 실제 BE · 클러스터 · GoCD는 건드리지 않는다.

흉내 내는 BE 규칙 (BE/src/gateway): 도구 8개만 노출, name/slug 패치 PATCH_FORBIDDEN,
build/runtime 밖 경로 PATCH_FORBIDDEN, runtime.port 정수 검사 INVALID_SPEC(fields),
도구별 한도 {run_build:2, run_render:5, run_deploy:2, run_verify:3} · 전체 20 → TOOL_LIMIT,
verified의 specPatch는 마지막 성공 run_deploy + 통과 run_verify의 패치와 같아야 함(INVALID_RESULT).

usage: PYTHONPATH=<AI code dir> python agent_bench.py <label> <reps> [scenario...]
"""

import asyncio
import copy
import json
import re
import sys
import time
from datetime import UTC, datetime, timedelta
from typing import Any

from fastmcp import FastMCP
from fastmcp.tools.base import ToolResult
from pydantic_ai.messages import ToolCallPart
from pydantic_ai.models.wrapper import WrapperModel

from ai_server.agent import loop
from ai_server.agent.gateway import GatewayToolset
from ai_server.agent.memory import CaseMemory, load_cases
from ai_server.agent.models import GatewayGrant, Ticket
from ai_server.agent.runs import TicketRun
from ai_server.config import load_settings

Json = dict[str, Any]
SHA = "c37ed32391f4f78541614ab3950c45e7eb77329c"
NOW = datetime(2026, 11, 14, 6, 25, tzinfo=UTC)
LIMITS = {"run_build": 2, "run_render": 5, "run_deploy": 2, "run_verify": 3}
TOTAL = 20
NAMES = re.compile(r"^/spec/(services/\d+/name|project/slug)$")
ALLOWED = re.compile(r"^/spec/services/\d+/(build|runtime)(/|$)")


def spec(port: int = 8080, name: str = "web", framework: str | None = None) -> Json:
    return {
        "project": {"repo": "student/app", "slug": "bench-app"},
        "services": [
            {
                "dir": ".",
                "name": name,
                "role": "be",
                "build": {
                    "build": None, "start": None, "context": ".", "install": None,
                    "buildEnv": {}, "framework": framework, "outputDir": None,
                    "dockerfile": "Dockerfile", "nodeVersion": None,
                },
                "runtime": {
                    "env": {}, "kind": "server", "port": port, "links": [],
                    "health": {"path": "/api/health", "type": "http", "startupTimeoutSeconds": 30},
                    "resources": None, "secretKeys": [], "ingressPath": "/", "stripPrefix": False,
                },
            }
        ],
    }


def base_ticket(tid: str, stage: str, error: str, sp: Json, raw: Json, lines: list[str]) -> Json:
    return {
        "ticketId": tid, "commitSha": SHA, "stage": stage, "service": sp["services"][0]["name"],
        "targetSlot": "a",
        "deployInput": {"commitSha": SHA, "deploy_condition": {}, "spec": sp},
        "errorMessage": error, "raw": raw,
        "logs": {"from": (NOW - timedelta(minutes=10)).isoformat(), "to": NOW.isoformat(), "lines": lines},
        "previous": None,
    }


def build_raw(msg: str) -> Json:
    return {"codebuild": {"buildStatus": "FAILED", "currentPhase": "COMPLETED", "phases": [
        {"phaseType": "BUILD", "phaseStatus": "FAILED", "contexts": [{"statusCode": "COMMAND_EXECUTION_ERROR", "message": msg}]}
    ]}, "k8s": None}


# ---- 시나리오: 티켓 + 오라클(패치된 spec이 실제로 고쳐졌는가) + 정답 상태 ----

def sc_a1() -> Json:
    sp = spec(8080)
    raw = {"codebuild": None, "k8s": {
        "pod": {"metadata": {"name": "web-a-7d9f"}, "status": {"phase": "Running", "containerStatuses": [
            {"name": "web", "ready": False, "restartCount": 0, "state": {"running": {}}, "lastState": {}}]}},
        "events": [{"reason": "Unhealthy", "type": "Warning", "count": 12,
                    "message": "Readiness probe failed: Get \"http://10.42.0.31:8080/api/health\": dial tcp 10.42.0.31:8080: connect: connection refused",
                    "lastTimestamp": NOW.isoformat()}],
        "status": None}}
    lines = ["> wanggane-memo@1.0.0 start", "> node server.js", "listening on 3000"]
    t = base_ticket("bench_a1", "apply", "service web did not become ready: Readiness probe failed", sp, raw, lines)
    return {"ticket": t, "expect": "verified",
            "fixed": lambda s: s["services"][0]["runtime"]["port"] == 3000 and type(s["services"][0]["runtime"]["port"]) is int,
            "fail": {"stage": "apply", "errorMessage": "service web did not become ready: Readiness probe failed (port 8080 connection refused)"},
            "pod_logs": lines, "repo": {}}


def sc_r1() -> Json:
    sp = spec(3000, name="web-")
    status = {"kind": "Status", "code": 422, "reason": "Invalid", "status": "Failure",
              "message": 'Service "web--a" is invalid: metadata.name: Invalid value: "web--a": a DNS-1035 label must consist of lower case alphanumeric characters or \'-\', start with an alphabetic character, and end with an alphanumeric character',
              "details": {"name": "web--a", "kind": "Service", "causes": [
                  {"reason": "FieldValueInvalid", "field": "metadata.name",
                   "message": 'Invalid value: "web--a": a DNS-1035 label must consist of lower case alphanumeric characters or \'-\', start with an alphabetic character, and end with an alphanumeric character (regex used for validation is \'[a-z]([-a-z0-9]*[a-z0-9])?\')'}]}}
    raw = {"codebuild": None, "k8s": {"pod": None, "events": [], "status": status}}
    t = base_ticket("bench_r1", "render", "render failed: Service \"web--a\" is invalid (422)", sp, raw, [])
    return {"ticket": t, "expect": "needs_user", "fixed": lambda s: False,
            "fail": {"stage": "render", "errorMessage": "render failed: Service \"web--a\" is invalid (422)", "status": status},
            "pod_logs": [], "repo": {}}


def sc_b3() -> Json:
    sp = spec(3000, framework="vite")
    lines = ["#12 [build 5/6] RUN npm run build", "#12 0.9 > vite build",
             "#12 1.4 Error: VITE_API_KEY is required (set it in .env)", "#12 1.4     at config (/app/vite.config.ts:7:11)",
             "#12 ERROR: process \"/bin/sh -c npm run build\" did not complete successfully: exit code: 1"]
    t = base_ticket("bench_b3", "build", "build failed: exit code 1", sp, build_raw("Error while executing command: docker build. Reason: exit status 1"), lines)
    return {"ticket": t, "expect": "needs_user",
            "fixed": lambda s: False,  # 값은 비밀값이라 지어낸 값으로 통과시키면 오답
            "build_fixed": lambda s: bool(s["services"][0]["build"]["buildEnv"].get("VITE_API_KEY")),
            "fail": {"stage": "build", "errorMessage": "build failed: exit code 1"},
            "build_log": lines,
            "pod_logs": [], "repo": {".env.example": {"type": "file", "content": "# 발급받은 API 키 (비밀값)\nVITE_API_KEY=\n", "truncated": False},
                                     ".": {"type": "dir", "entries": [{"name": "src", "type": "dir", "size": 0}, {"name": "package.json", "type": "file", "size": 410}, {"name": ".env.example", "type": "file", "size": 52}, {"name": "vite.config.ts", "type": "file", "size": 210}, {"name": "Dockerfile", "type": "file", "size": 300}]}}}


def sc_b4() -> Json:
    sp = spec(3000)
    lines = ["#12 [build 5/6] RUN npm run build", "#12 2.1 > tsc && vite build",
             "#12 3.0 [vite]: Rollup failed to resolve import \"./components/Header\" from \"/app/src/App.tsx\".",
             "#12 3.0 error during build:", "#12 3.0 Error: Could not resolve './components/Header' from src/App.tsx",
             "#12 ERROR: process \"/bin/sh -c npm run build\" did not complete successfully: exit code: 1"]
    t = base_ticket("bench_b4", "build", "build failed: exit code 1", sp, build_raw("Error while executing command: docker build. Reason: exit status 1"), lines)
    return {"ticket": t, "expect": "needs_user", "fixed": lambda s: False, "build_fixed": lambda s: False,
            "fail": {"stage": "build", "errorMessage": "build failed: exit code 1"}, "build_log": lines, "pod_logs": [],
            "repo": {"src/components": {"type": "dir", "entries": [{"name": "header.tsx", "type": "file", "size": 640}]},
                     "src": {"type": "dir", "entries": [{"name": "App.tsx", "type": "file", "size": 900}, {"name": "components", "type": "dir", "size": 0}]},
                     ".": {"type": "dir", "entries": [{"name": "src", "type": "dir", "size": 0}, {"name": "package.json", "type": "file", "size": 410}]},
                     "src/App.tsx": {"type": "file", "content": "import Header from './components/Header'\nexport default function App() { return <Header /> }\n", "truncated": False}}}


SCENARIOS = {"A1": sc_a1, "R1": sc_r1, "B3": sc_b3, "B4": sc_b4}


# ---- 패치 적용 ----

def _ptr(path: str) -> list[str]:
    return [p.replace("~1", "/").replace("~0", "~") for p in path.split("/")[1:]]


def apply_patch(doc: Json, patch: list[Json]) -> Json:
    root = {"spec": copy.deepcopy(doc)}
    for op in patch:
        parts = _ptr(op["path"])
        cur: Any = root
        for p in parts[:-1]:
            cur = cur[int(p)] if isinstance(cur, list) else cur.setdefault(p, {})
        last = parts[-1]
        if op["op"] in ("replace", "add"):
            if isinstance(cur, list):
                cur[int(last)] = op["value"]
            else:
                cur[last] = op["value"]
        elif op["op"] == "remove":
            cur.pop(last, None)
        else:
            raise ValueError(op["op"])
    return root["spec"]


class BenchGateway:
    def __init__(self, sc: Json) -> None:
        self.sc = sc
        self.base = sc["ticket"]["deployInput"]["spec"]
        self.calls: list[tuple[str, Json]] = []
        self.rejects: list[str] = []
        self.counts: dict[str, int] = {}
        self.total = 0
        self.last_ok_deploy: list[Json] | None = None
        self.verified_patch: list[Json] | None = None
        self.built_ok = False
        self.submitted: list[Json] = []
        self.server = FastMCP("bench-gateway")
        self._register()

    def _reject(self, code: str, msg: str, fields: list[Json] | None = None) -> ToolResult:
        self.rejects.append(code)
        body: Json = {"code": code, "message": msg}
        if fields:
            body["fields"] = fields
        return ToolResult(structured_content=body, is_error=True)

    def _budget(self, tool: str) -> ToolResult | None:
        if self.total >= TOTAL or (tool in LIMITS and self.counts.get(tool, 0) >= LIMITS[tool]):
            return self._reject("TOOL_LIMIT", f"{tool} call limit reached")
        self.total += 1
        self.counts[tool] = self.counts.get(tool, 0) + 1
        return None

    def _patched(self, patch: Any) -> tuple[Json | None, ToolResult | None]:
        patch = patch or []
        if not isinstance(patch, list):
            return None, self._reject("INVALID_ARGUMENT", "specPatch must be an array")
        for op in patch:
            path = str(op.get("path", ""))
            if NAMES.match(path):
                return None, self._reject("PATCH_FORBIDDEN", f"{path}: name and slug cannot be tried on the target slot (slot and Secret names follow them)")
            if not ALLOWED.match(path):
                return None, self._reject("PATCH_FORBIDDEN", f"{path}: only build and runtime paths may be patched")
        try:
            s = apply_patch(self.base, patch)
        except Exception as e:
            return None, self._reject("INVALID_ARGUMENT", f"patch does not apply: {type(e).__name__}")
        port = s["services"][0]["runtime"].get("port")
        if type(port) is not int or not 1 <= port <= 65535:
            return None, self._reject("INVALID_SPEC", "see fields", [{"path": "services[0].runtime.port", "code": "INVALID_TYPE"}])
        return s, None

    def _register(self) -> None:
        srv = self.server
        sc = self.sc

        def rec(name: str, args: Json) -> None:
            self.calls.append((name, {k: v for k, v in args.items() if v is not None}))

        @srv.tool
        def get_target_status(service: str | None = None) -> ToolResult:
            rec("get_target_status", {"service": service})
            if r := self._budget("get_target_status"):
                return r
            k8s = sc["ticket"]["raw"].get("k8s") or {}
            return ToolResult(structured_content={"pods": [k8s.get("pod")] if k8s.get("pod") else [], "events": k8s.get("events", []), "rollouts": []})

        @srv.tool
        def read_pod_logs(service: str, lines: int | None = None, previous: bool | None = None) -> ToolResult:
            rec("read_pod_logs", {"service": service, "lines": lines, "previous": previous})
            if r := self._budget("read_pod_logs"):
                return r
            return ToolResult(structured_content={"lines": sc["pod_logs"]})

        @srv.tool
        def read_repo(path: str, source: Json | None = None) -> ToolResult:
            rec("read_repo", {"path": path})
            if r := self._budget("read_repo"):
                return r
            key = path.strip().lstrip("./") or "."
            key = "." if path.strip() in (".", "./", "") else key
            if key in sc["repo"]:
                return ToolResult(structured_content=sc["repo"][key])
            return self._reject("NOT_FOUND", f"{path} is not in the repository at this commit")

        @srv.tool
        def run_build(service: str, specPatch: list[Json] | None = None, source: Json | None = None, buildOverrides: Json | None = None) -> ToolResult:
            rec("run_build", {"service": service, "specPatch": specPatch})
            if r := self._budget("run_build"):
                return r
            s, r = self._patched(specPatch)
            if r:
                return r
            if sc.get("build_fixed", lambda _: True)(s):
                self.built_ok = True
                return ToolResult(structured_content={"ok": True, "reused": False, "build": None, "failedPhase": None, "logTail": [], "image": "ghcr.io/bench@sha256:2"})
            return ToolResult(structured_content={"ok": False, "reused": False, "build": None, "failedPhase": "BUILD", "logTail": sc.get("build_log", [])[-5:], "image": None})

        @srv.tool
        def run_render(specPatch: list[Json] | None = None) -> ToolResult:
            rec("run_render", {"specPatch": specPatch})
            if r := self._budget("run_render"):
                return r
            s, r = self._patched(specPatch)
            if r:
                return r
            if sc["ticket"]["stage"] == "render":
                return ToolResult(structured_content={"ok": False, "status": sc["fail"].get("status"), "failure": sc["fail"]})
            return ToolResult(structured_content={"ok": True, "status": None, "failure": None})

        @srv.tool
        def run_deploy(specPatch: list[Json] | None = None, source: Json | None = None) -> ToolResult:
            rec("run_deploy", {"specPatch": specPatch})
            if r := self._budget("run_deploy"):
                return r
            s, r = self._patched(specPatch)
            if r:
                return r
            stage = sc["ticket"]["stage"]
            ok = sc["fixed"](s) if stage in ("apply", "render") else (self.built_ok and sc["build_fixed"](s))
            self.last_ok_deploy = list(specPatch or []) if ok else None
            if ok:
                return ToolResult(structured_content={"ok": True, "services": [{"service": "web", "ready": True, "reason": None}], "pods": [], "events": [], "failure": None})
            return ToolResult(structured_content={"ok": False, "services": [{"service": "web", "ready": False, "reason": "not ready"}], "pods": [], "events": sc["ticket"]["raw"].get("k8s", {}) and sc["ticket"]["raw"]["k8s"].get("events", []), "failure": sc["fail"]})

        @srv.tool
        def run_verify() -> ToolResult:
            rec("run_verify", {})
            if r := self._budget("run_verify"):
                return r
            if self.last_ok_deploy is not None:
                self.verified_patch = self.last_ok_deploy
                return ToolResult(structured_content={"ok": True, "ready": [{"service": "web", "ready": True}], "requests": [{"service": "web", "path": "/api/health", "status": 200, "ms": 9, "error": None}], "failure": None})
            return ToolResult(structured_content={"ok": False, "ready": [{"service": "web", "ready": False}], "requests": [], "failure": {"stage": "verify", "errorMessage": "no successful run_deploy in this ticket"}})

        @srv.tool
        def submit_result(result: Json) -> ToolResult:
            rec("submit_result", {"result": result})
            self.submitted.append(result)
            if result.get("status") == "verified":
                if self.verified_patch is None or json.dumps(result.get("specPatch"), sort_keys=True) != json.dumps(self.verified_patch, sort_keys=True):
                    return self._reject("INVALID_RESULT", "verified needs a run_deploy with this same specPatch followed by a passing run_verify in this ticket")
            return ToolResult(structured_content={"accepted": True})


class Counting(WrapperModel):
    """모델 요청 수 · 토큰 · 없는 도구 호출을 센다."""

    def __init__(self, wrapped: Any, stats: Json) -> None:
        super().__init__(wrapped)
        self.stats = stats

    async def request(self, messages: Any, model_settings: Any, params: Any) -> Any:
        t0 = time.monotonic()
        try:
            resp = await super().request(messages, model_settings, params)
        except Exception:
            self.stats["model_errors"] += 1
            raise
        st = self.stats
        st["model_s"] += time.monotonic() - t0
        st["requests"] += 1
        st["in_tok"] += resp.usage.input_tokens or 0
        st["out_tok"] += resp.usage.output_tokens or 0
        st["by_model"][resp.model_name or "?"] = st["by_model"].get(resp.model_name or "?", 0) + 1
        known = {t.name for t in params.function_tools} | {t.name for t in params.output_tools}
        for p in resp.parts:
            if isinstance(p, ToolCallPart):
                st["tool_calls_model"] += 1
                if p.tool_name not in known:
                    st["unknown_tools"].append(p.tool_name)
        return resp


async def run_one(models: Any, sid: str, rep: int) -> Json:
    sc = SCENARIOS[sid]()
    gw = BenchGateway(sc)
    stats: Json = {"requests": 0, "in_tok": 0, "out_tok": 0, "model_s": 0.0, "model_errors": 0,
                   "tool_calls_model": 0, "unknown_tools": [], "by_model": {}}
    counted = loop.Models(local=Counting(models.local, stats), planner=Counting(models.planner, stats))
    runner = loop.make_agent_runner(counted, lambda token: GatewayToolset(gw.server))
    ticket = Ticket.model_validate({**sc["ticket"], "ticketId": f"{sc['ticket']['ticketId']}_{rep}"})
    run = TicketRun(ticket=ticket, gateway=GatewayGrant.model_validate({"token": "bench", "expiresAt": (NOW + timedelta(minutes=30)).isoformat()}))
    t0 = time.monotonic()
    err = None
    try:
        await asyncio.wait_for(runner(run, CaseMemory(load_cases())), timeout=900)
    except Exception as e:  # 측정 기록용
        err = type(e).__name__
    elapsed = time.monotonic() - t0
    final = gw.submitted[-1] if gw.submitted else {}
    status = final.get("status")
    return {
        "scenario": sid, "rep": rep, "expect": sc["expect"], "status": status,
        "correct": status == sc["expect"], "submits": len(gw.submitted),
        "first_status": gw.submitted[0].get("status") if gw.submitted else None,
        "path": (final.get("classification") or {}).get("path"),
        "case": (final.get("classification") or {}).get("caseId"),
        "gw_calls": len([c for c in gw.calls if c[0] != "submit_result"]),
        "gw_seq": [c[0] for c in gw.calls],
        "rejects": gw.rejects, "elapsed_s": round(elapsed, 1), "error": err,
        **{k: (round(v, 1) if isinstance(v, float) else v) for k, v in stats.items()},
    }


async def main() -> None:
    label, reps = sys.argv[1], int(sys.argv[2])
    ids = sys.argv[3:] or list(SCENARIOS)
    models = loop.models_from_settings(load_settings(env_file=None))
    assert models is not None, "no LOCAL_MODEL_* settings"
    for rep in range(reps):
        for sid in ids:
            r = await run_one(models, sid, rep)
            r["label"] = label
            print("RESULT " + json.dumps(r, ensure_ascii=False), flush=True)


if __name__ == "__main__":
    asyncio.run(main())
