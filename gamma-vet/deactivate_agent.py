# -*- coding: utf-8 -*-
import json
import urllib.request
import urllib.error
from pathlib import Path

ENV = Path(r"c:\Users\GC1\Desktop\Automação GHL\.env")
vals = {}
for line in ENV.read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()

KEY = vals["GHL_GAMMA_API_KEY"]
LOC = vals["GHL_GAMMA_LOCATION_ID"]
AGENT = vals["GHL_GAMMA_AGENT_ID"]
UA = "Mozilla/5.0"


def req(method, url, body=None):
    data = None if body is None else json.dumps(body).encode("utf-8")
    r = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {KEY}",
            "Version": "2021-07-28",
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": UA,
        },
    )
    try:
        with urllib.request.urlopen(r, timeout=90) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(err)
        except Exception:
            parsed = err
        return e.code, parsed


print("=== search POST ===")
for body in [
    {"locationId": LOC},
    {"locationId": LOC, "query": ""},
    {"locationId": LOC, "limit": 20},
]:
    code, data = req("POST", "https://services.leadconnectorhq.com/conversation-ai/agents/search", body)
    print("POST search", code, body, str(data)[:300] if not isinstance(data, dict) else list(data.keys()))
    if isinstance(data, dict):
        agents = data.get("agents") or data.get("data") or []
        print(" n", len(agents) if isinstance(agents, list) else type(agents))
        for a in agents if isinstance(agents, list) else []:
            print("  ", a.get("id"), a.get("name"), a.get("isPrimary"), a.get("mode"), a.get("channels"))
    if str(code).startswith("2"):
        break

code, cur = req("GET", f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}")
agent = cur.get("agent", cur) if isinstance(cur, dict) else {}

tries = [
    {"name": agent.get("name"), "isPrimary": True, "mode": "off", "channels": ["WebChat"]},
    {"name": agent.get("name"), "isPrimary": True, "mode": "off", "channels": ["Live_Chat"]},
    {"name": agent.get("name"), "isPrimary": True, "mode": "off"},
]
for i, payload in enumerate(tries, 1):
    payload["instructions"] = agent.get("instructions") or ""
    payload["goal"] = agent.get("goal") or ""
    payload["personality"] = agent.get("personality") or ""
    payload["knowledgeBaseIds"] = agent.get("knowledgeBaseIds") or []
    print(f"\nTRY {i}", {k: payload[k] for k in ("mode", "isPrimary", "channels") if k in payload})
    code, body = req("PUT", f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}", payload)
    print(" ", code, body.get("message") if isinstance(body, dict) else str(body)[:200])
    if str(code).startswith("2"):
        break

code, after = req("GET", f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}")
after = after.get("agent", after) if isinstance(after, dict) else {}
print("\nDEPOIS primary", after.get("isPrimary"), "mode", after.get("mode"), "channels", after.get("channels"))
Path(r"c:\Users\GC1\Desktop\Automação GHL\gamma-vet\agent-live-now.json").write_text(
    json.dumps(after, ensure_ascii=False, indent=2), encoding="utf-8"
)
