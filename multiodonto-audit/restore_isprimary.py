# -*- coding: utf-8 -*-
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ENV = Path(r"c:\Users\GC1\Desktop\Automação GHL\.env")
key = None
for line in ENV.read_text(encoding="utf-8").splitlines():
    if line.startswith("GHL_MULTIODONTO_API_KEY="):
        key = line.split("=", 1)[1].strip()
        break

AGENT = "3Fzfmx7ViwyD9v16h4DR"
LOC = "3R4hY0j3TJyj2SkmSQL3"
OUT = Path(r"c:\Users\GC1\Desktop\Automação GHL\multiodonto-audit")
BASE = "https://services.leadconnectorhq.com"


def req(method, path, body=None):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {key}",
            "Version": "2021-07-28",
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "Mozilla/5.0",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")


def unwrap(payload):
    if isinstance(payload, dict) and "instructions" in payload:
        return payload
    if isinstance(payload, dict):
        return payload.get("data") or payload.get("agent") or payload
    return payload


st, search = req(
    "GET",
    f"/conversation-ai/agents/search?locationId={LOC}&limit=20",
)
print("SEARCH", st)
agents = []
if isinstance(search, dict):
    agents = (
        search.get("agents")
        or (search.get("data") or {}).get("agents")
        or search.get("data")
        or []
    )
    if isinstance(agents, dict):
        agents = agents.get("agents") or []
if isinstance(agents, list):
    for ag in agents:
        if isinstance(ag, dict):
            print(
                " search:",
                ag.get("name"),
                ag.get("id"),
                "primary=",
                ag.get("isPrimary"),
                "mode=",
                ag.get("mode"),
            )

st, agent = req("GET", f"/conversation-ai/agents/{AGENT}")
a = unwrap(agent)
print("\nGET Letícia isPrimary", a.get("isPrimary"), "mode", a.get("mode"))

payloads = [
    {
        "name": a.get("name") or "Letícia IA Agendamento",
        "personality": a.get("personality"),
        "goal": a.get("goal"),
        "instructions": a.get("instructions"),
        "isPrimary": True,
        "mode": a.get("mode") or "auto-pilot",
        "knowledgeBaseIds": a.get("knowledgeBaseIds") or ["HjJZbTH2w5riiz6GeC5y"],
        "autoPilotMaxMessages": a.get("autoPilotMaxMessages") or 100,
        "channels": a.get("channels") or ["SMS", "IG", "FB", "WhatsApp"],
    },
    {
        "name": a.get("name") or "Letícia IA Agendamento",
        "isPrimary": True,
        "mode": a.get("mode") or "auto-pilot",
    },
]

for i, body in enumerate(payloads):
    st, resp = req("PUT", f"/conversation-ai/agents/{AGENT}", body)
    print(f"\nPUT variant {i}", st)
    if isinstance(resp, dict):
        r = unwrap(resp)
        print("  PUT returned isPrimary", r.get("isPrimary") if isinstance(r, dict) else None)
    else:
        print(str(resp)[:500])
    st, agent2 = req("GET", f"/conversation-ai/agents/{AGENT}")
    a2 = unwrap(agent2)
    print("  GET isPrimary", a2.get("isPrimary"), "mode", a2.get("mode"))
    if a2.get("isPrimary") is True:
        print("RESTORED")
        (OUT / "agent-live-20260831.json").write_text(
            json.dumps(a2, ensure_ascii=False, indent=2), encoding="utf-8"
        )
        break
else:
    print("FALHOU restaurar isPrimary")
    (OUT / "agent-live-20260831.json").write_text(
        json.dumps(a2, ensure_ascii=False, indent=2), encoding="utf-8"
    )
