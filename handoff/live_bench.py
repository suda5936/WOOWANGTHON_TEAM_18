"""실서비스 측정: app.stairnoworks.com의 실제 흐름(배포 저장 → 시작 → 파이프라인 → AI 에이전트)을 돌리고
결과를 모은다. 계정은 env(DEMO_EMAIL, DEMO_PASSWORD)에서만 읽고 출력하지 않는다.

usage: python3 live_bench.py <label> <scenario> <n>
  scenario: A1 | B3 | B4 | B5w
출력: results/<label>-<scenario>-<n>.json
"""

import json
import os
import re
import subprocess
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import boto3

API = "https://api.stairnoworks.com"
SUPA = "https://dowhtvfzzzeijgqotjny.supabase.co"
APP = "https://app.stairnoworks.com"
REPO = "suda5936/WOOWANGTHON_TEST_2"
IID = "i-01eeae171d57f9615"
VLLM = "http://100.117.191.92:18000/metrics"
HERE = Path(__file__).parent

# 시나리오 = TEST_2의 커밋 + 배포 설정. 고장은 레포에 있고 배포 설정은 학생이 확정한 값 그대로다.
SCENARIOS = {
    "A1": {"commit": "c37ed32391f4f78541614ab3950c45e7eb77329c", "port": 8080, "expect": "verified"},
    "B3": {"commit": "0d806dad1f80d7be8a6525e9679d5d70f94b5e8a", "port": 3000, "expect": "needs_user"},
    "B4": {"commit": "da3ab573e37c366bd17a39e5281c7665d416dee2", "port": 3000, "expect": "needs_user"},
    "B5w": {"commit": "412268ac6c0a86763c06fbcdff64bee4eb2fbfab", "port": 3000, "expect": "needs_user"},
}


def now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def curl(method: str, url: str, headers: dict[str, str], body: object | None = None) -> tuple[int, object]:
    # python urllib은 403을 받는다(이전 세션 확인). curl로 보낸다.
    args = ["curl", "-sS", "-X", method, url, "-w", "\n%{http_code}"]
    for k, v in headers.items():
        args += ["-H", f"{k}: {v}"]
    if body is not None:
        args += ["-H", "content-type: application/json", "--data-binary", "@-"]
    out = subprocess.run(args, input=json.dumps(body) if body is not None else None, capture_output=True, text=True, check=True).stdout
    text, code = out.rsplit("\n", 1)
    try:
        return int(code), json.loads(text) if text else None
    except json.JSONDecodeError:
        return int(code), text[:500]


def publishable_key() -> str:
    html = subprocess.run(["curl", "-sS", APP + "/"], capture_output=True, text=True, check=True).stdout
    js = re.search(r'/assets/index-[^"]+\.js', html).group(0)
    bundle = subprocess.run(["curl", "-sS", APP + js], capture_output=True, text=True, check=True).stdout
    return re.search(r"sb_publishable_[A-Za-z0-9_-]+", bundle).group(0)


def login() -> str:
    key = publishable_key()
    code, body = curl("POST", f"{SUPA}/auth/v1/token?grant_type=password", {"apikey": key},
                      {"email": os.environ["DEMO_EMAIL"], "password": os.environ["DEMO_PASSWORD"]})
    assert code == 200, f"login {code}"
    return body["access_token"]


def ssm(cmd: str) -> str:
    c = boto3.client("ssm")
    cid = c.send_command(InstanceIds=[IID], DocumentName="AWS-RunShellScript", Parameters={"commands": [cmd]})["Command"]["CommandId"]
    while True:
        time.sleep(2)
        try:
            o = c.get_command_invocation(CommandId=cid, InstanceId=IID)
        except c.exceptions.InvocationDoesNotExist:
            continue
        if o["Status"] not in ("Pending", "InProgress", "Delayed"):
            return o["StandardOutputContent"]


def vllm() -> dict[str, float]:
    out = ssm(f"curl -sS --max-time 5 {VLLM} | grep -E '^vllm:(prompt_tokens_total|generation_tokens_total|request_success_total)'")
    m: dict[str, float] = {}
    for line in out.splitlines():
        name, val = line.rsplit(" ", 1)
        key = name.split("{")[0].removeprefix("vllm:")
        if key == "request_success_total":
            key = "req_" + re.search(r'finished_reason="(\w+)"', name).group(1)
        m[key] = float(val)
    return m


def spec(slug: str, port: int) -> dict:
    return {
        "project": {"repo": REPO, "slug": slug},
        "services": [{
            "dir": ".", "name": "web", "role": "be",
            "build": {"context": ".", "dockerfile": "Dockerfile", "framework": None, "nodeVersion": None,
                      "install": None, "build": None, "start": None, "outputDir": None, "buildEnv": {}},
            "runtime": {"kind": "server", "port": port,
                        "health": {"type": "http", "path": "/api/health", "startupTimeoutSeconds": 30},
                        "env": {}, "secretKeys": [], "links": [], "ingressPath": "/", "stripPrefix": False,
                        "resources": None},
        }],
    }


def main() -> None:
    label, sid, n = sys.argv[1], sys.argv[2], sys.argv[3]
    sc = SCENARIOS[sid]
    slug = f"bench-{sid.lower()}-{label}-{n}"
    token = login()
    auth = {"authorization": f"Bearer {token}"}
    before = vllm()
    rec: dict = {"label": label, "scenario": sid, "n": n, "slug": slug, "expect": sc["expect"], "commit": sc["commit"],
                 "events": [], "vllm_before": before}
    code, body = curl("POST", f"{API}/api/deploys", auth,
                      {"repoUrl": f"https://github.com/{REPO}", "commit": sc["commit"], "spec": spec(slug, sc["port"])})
    assert code in (200, 201), (code, body)
    did = body["deployId"] if "deployId" in body else body["id"]
    rec["deployId"] = did
    curl("GET", f"{API}/api/deploys/{did}/secrets", auth)
    code, body = curl("POST", f"{API}/api/deploys/{did}/start", auth, {})
    assert code == 202, (code, body)
    rec["started"] = now()
    t0 = time.monotonic()
    last = None
    while time.monotonic() - t0 < 50 * 60:
        if time.monotonic() - t0 > 40 * 60:
            token, auth = login(), None
            auth = {"authorization": f"Bearer {token}"}
        code, st = curl("GET", f"{API}/api/deploys/{did}/status", auth)
        if code == 401:
            token = login(); auth = {"authorization": f"Bearer {token}"}; continue
        key = (st["status"], st["stage"], (st.get("agent") or {}).get("status"))
        if key != last:
            rec["events"].append({"t": round(time.monotonic() - t0, 1), "at": now(), "status": st["status"], "stage": st["stage"],
                                  "agent": (st.get("agent") or {}).get("status"), "failure": (st.get("failure") or {}).get("code")})
            last = key
            print(json.dumps(rec["events"][-1], ensure_ascii=False), flush=True)
        if st["status"] in ("succeeded", "failed", "needs_user"):
            rec["final"] = st
            break
        time.sleep(5)
    rec["total_s"] = round(time.monotonic() - t0, 1)
    time.sleep(3)
    rec["vllm_after"] = vllm()
    rec["vllm_delta"] = {k: rec["vllm_after"].get(k, 0) - before.get(k, 0) for k in rec["vllm_after"]}
    out = HERE / "results" / f"{label}-{sid}-{n}.json"
    out.parent.mkdir(exist_ok=True)
    out.write_text(json.dumps(rec, ensure_ascii=False, indent=1))
    print("WROTE", out, "final", (rec.get("final") or {}).get("status"), (rec.get("final") or {}).get("agent", {}) and rec["final"]["agent"].get("status"), rec["total_s"])


if __name__ == "__main__":
    main()
