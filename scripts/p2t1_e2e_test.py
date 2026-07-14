#!/usr/bin/env python3
"""P2T1 End-to-end workflow test via HTTP API against running backend."""
import json, sys, urllib.request, urllib.error, time

BASE = "http://localhost:8000"


def req(method, path, data=None, token=None):
    url = f"{BASE}{path}"
    body = json.dumps(data).encode() if data else None
    headers = {"Content-Type": "application/json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    r = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def log(msg):
    print(f"[{time.strftime('%H:%M:%S')}] {msg}", flush=True)


# 1. Health check
log("=== HEALTH CHECK ===")
status, body = req("GET", "/health")
log(f"Health: {status}")

# 2. Login as researcher
log("=== LOGIN ===")
status, body = req("POST", "/api/v1/auth/login",
                   {"username": "researcher", "password": "researcher123"})
token = body.get("data", {}).get("access_token", "") or body.get("access_token", "")
log(f"Login: {status}, token={token[:20]}..." if token else f"Login: {status}")

if not token:
    log("FAILED TO LOGIN - check credentials")
    sys.exit(1)

# 3. Create research session
log("=== CREATE SESSION ===")
status, body = req("POST", "/api/v4/research/session",
                   {"title": "P2T1 E2E Test"},
                   token=token)
log(f"Session: {status}, success={body.get('success')}")
if body.get("success"):
    session_id = body.get("data", {}).get("session_id", "")
    log(f"Session ID: {session_id}")
else:
    log(f"Error: {body.get('message')}")
    sys.exit(1)

# 4. Execute research workflow
log("=== EXECUTE WORKFLOW ===")
TOPIC = "《针灸甲乙经》的成书特点是什么？"
status, body = req("POST", "/api/v4/research/workflow",
                   {"session_id": session_id, "topic": TOPIC,
                    "workflow_type": "full_research_flow"},
                   token=token)

log(f"Workflow: {status}, success={body.get('success')}")
success = body.get("success", False)
steps = body.get("data", {}).get("steps", [])

for step in steps:
    name = step.get("name", "?")
    st = step.get("status", "?")
    result = step.get("result", {})
    log(f"  Step {name}: {st} -> {json.dumps(result, ensure_ascii=False)[:120]}")

# 5. Get runs
log("=== GET RUNS ===")
status, body = req("GET", f"/api/v4/research/session/{session_id}/runs",
                   token=token)
log(f"Runs: {status}, success={body.get('success')}")
runs = body.get("data", {}).get("runs", [])
log(f"Run count: {len(runs)}")
citation_count = body.get("traceability", {}).get("citation_count", 0)
log(f"Citation count: {citation_count}")

# 6. Overall
log(f"\n=== RESULT ===")
log(f"workflow_success: {success}")
log(f"citation_count: {citation_count}")
if success and citation_count > 0:
    log("E2E WORKFLOW: PASS")
    sys.exit(0)
else:
    log("E2E WORKFLOW: FAIL")
    sys.exit(1)
