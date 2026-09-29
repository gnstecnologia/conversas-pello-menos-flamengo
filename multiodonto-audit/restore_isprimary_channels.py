# -*- coding: utf-8 -*-
"""Restaura isPrimary por canal na Letícia, mantendo o prompt novo."""
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ENV = Path(r"c:\Users\GC1\Desktop\Automação GHL\.env")
OUT = Path(r"c:\Users\GC1\Desktop\Automação GHL\multiodonto-audit")
key = None
for line in ENV.read_text(encoding="utf-8").splitlines():
    if line.startswith("GHL_MULTIODONTO_API_KEY="):
        key = line.split("=", 1)[1].strip()
        break

AGENT = "3Fzfmx7ViwyD9v16h4DR"
BASE = "https://services.leadconnectorhq.com"
H = {
    "Authorization": f"Bearer {key}",
    "Version": "2021-07-28",
    "Accept": "application/json",
    "Content-Type": "application/json; charset=utf-8",
    "User-Agent": "Mozilla/5.0",
    "Location-Id": "3R4hY0j3TJyj2SkmSQL3",
}


def req(method, path, body=None, extra=None):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    headers = dict(H)
    if extra:
        headers.update(extra)
    request = urllib.request.Request(BASE + path, data=data, method=method, headers=headers)
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


def search():
    st, r = req("GET", "/conversation-ai/agents/search?limit=20")
    print("SEARCH", st)
    if not isinstance(r, dict):
        print(str(r)[:400])
        return
    for ag in r.get("agents") or []:
        ch = ag.get("channels")
        print(
            ag.get("name"),
            ag.get("id"),
            "topPrimary=",
            ag.get("isPrimary"),
            "mode=",
            ag.get("mode"),
            "channels=",
            ch,
        )


print("=== BEFORE ===")
search()

st, agent = req("GET", f"/conversation-ai/agents/{AGENT}")
a = unwrap(agent)
print("GET instr has ERRO GRAVE:", "ERRO GRAVE 01/09/2026" in (a.get("instructions") or ""))

PERSONALITY = (OUT / "personality-new.txt").read_text(encoding="utf-8").strip()
GOAL = (OUT / "goal-new.txt").read_text(encoding="utf-8").strip()
INSTRUCTIONS = (OUT / "instructions-new.txt").read_text(encoding="utf-8").strip()

variants = [
    {
        "name": a.get("name") or "Letícia IA Agendamento",
        "personality": PERSONALITY,
        "goal": GOAL,
        "instructions": INSTRUCTIONS,
        "isPrimary": True,
        "mode": a.get("mode") or "auto-pilot",
        "knowledgeBaseIds": a.get("knowledgeBaseIds") or ["HjJZbTH2w5riiz6GeC5y"],
        "autoPilotMaxMessages": a.get("autoPilotMaxMessages") or 100,
        "channels": [
            {"name": "SMS", "isPrimary": True},
            {"name": "IG", "isPrimary": True},
            {"name": "FB", "isPrimary": True},
            {"name": "WhatsApp", "isPrimary": True},
        ],
    },
    {
        "name": a.get("name") or "Letícia IA Agendamento",
        "personality": PERSONALITY,
        "goal": GOAL,
        "instructions": INSTRUCTIONS,
        "isPrimary": True,
        "mode": a.get("mode") or "auto-pilot",
        "knowledgeBaseIds": a.get("knowledgeBaseIds") or ["HjJZbTH2w5riiz6GeC5y"],
        "autoPilotMaxMessages": a.get("autoPilotMaxMessages") or 100,
        "channels": ["SMS", "IG", "FB", "WhatsApp"],
    },
]

for i, body in enumerate(variants):
    print(f"\n=== PUT variant {i} ===")
    st, resp = req("PUT", f"/conversation-ai/agents/{AGENT}", body)
    print("PUT", st)
    if st not in (200, 201):
        print(str(resp)[:800])
        continue
    r = unwrap(resp) if isinstance(resp, dict) else {}
    print(" PUT returned isPrimary", r.get("isPrimary") if isinstance(r, dict) else None)
    print(" PUT channels", r.get("channels") if isinstance(r, dict) else None)
    print("=== AFTER variant", i, "===")
    search()
    st2, s2 = req("GET", "/conversation-ai/agents/search?limit=20")
    ok = False
    if isinstance(s2, dict):
        for ag in s2.get("agents") or []:
            if ag.get("id") != AGENT:
                continue
            ch = ag.get("channels") or []
            if isinstance(ch, list) and ch and isinstance(ch[0], dict):
                wa = next((c for c in ch if c.get("name") == "WhatsApp"), None)
                if wa and wa.get("isPrimary") is True:
                    ok = True
            if ag.get("isPrimary") is True:
                ok = True
    if ok:
        print("RESTORED isPrimary")
        (OUT / "agent-after-dentista-dia.json").write_text(
            json.dumps(unwrap(resp), ensure_ascii=False, indent=2) if isinstance(resp, dict) else str(resp),
            encoding="utf-8",
        )
        break
else:
    print("FALHOU restaurar isPrimary nos canais")
