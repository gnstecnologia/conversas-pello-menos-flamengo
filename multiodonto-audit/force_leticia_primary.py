# -*- coding: utf-8 -*-
"""Força Letícia como isPrimary (pedido expresso do usuário)."""
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
LOC = "3R4hY0j3TJyj2SkmSQL3"

PERSONALITY = (OUT / "personality-new.txt").read_text(encoding="utf-8").strip()
GOAL = (OUT / "goal-new.txt").read_text(encoding="utf-8").strip()
INSTRUCTIONS = (OUT / "instructions-new.txt").read_text(encoding="utf-8").strip()


def req(method, path, body=None, version="2021-07-28"):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    headers = {
        "Authorization": f"Bearer {key}",
        "Version": version,
        "Accept": "application/json",
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": "Mozilla/5.0",
        "Location-Id": LOC,
    }
    request = urllib.request.Request(BASE + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(request, timeout=90) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw[:800]


def unwrap(payload):
    if isinstance(payload, dict) and "instructions" in payload:
        return payload
    if isinstance(payload, dict):
        return payload.get("data") or payload.get("agent") or payload
    return payload


def dump_search(label, version):
    st, r = req("GET", "/conversation-ai/agents/search?limit=20", version=version)
    print(f"\n{label} SEARCH ver={version} {st}")
    if not isinstance(r, dict):
        print(str(r)[:400])
        return
    for ag in r.get("agents") or []:
        print(
            " ",
            ag.get("name"),
            ag.get("id"),
            "topPrimary=",
            ag.get("isPrimary"),
            "mode=",
            ag.get("mode"),
            "ch=",
            ag.get("channels"),
        )


print("=== GET current (2021 + v3) ===")
for ver in ("2021-07-28", "v3"):
    st, a = req("GET", f"/conversation-ai/agents/{AGENT}", version=ver)
    a = unwrap(a) if isinstance(a, dict) else {}
    print(
        ver,
        st,
        "isPrimary=",
        a.get("isPrimary") if isinstance(a, dict) else None,
        "mode=",
        a.get("mode") if isinstance(a, dict) else None,
        "channels=",
        a.get("channels") if isinstance(a, dict) else None,
        "keys_has_isPrimary=",
        isinstance(a, dict) and "isPrimary" in a,
        "instr ERRO GRAVE=",
        "ERRO GRAVE 01/09/2026" in (a.get("instructions") or "") if isinstance(a, dict) else False,
    )
    dump_search("before", ver)

st, cur = req("GET", f"/conversation-ai/agents/{AGENT}")
a = unwrap(cur)
assert isinstance(a, dict) and a.get("instructions")

# payload completo no formato da doc (não apagar prompt)
full = {
    "name": a.get("name") or "Letícia IA Agendamento",
    "businessName": a.get("businessName") or "Multiodonto Clínica Odontológica",
    "mode": "auto-pilot",
    "channels": ["SMS", "IG", "FB", "WhatsApp"],
    "isPrimary": True,
    "waitTime": a.get("waitTime") if a.get("waitTime") is not None else 2,
    "waitTimeUnit": a.get("waitTimeUnit") or "seconds",
    "personality": PERSONALITY,
    "goal": GOAL,
    "instructions": INSTRUCTIONS,
    "autoPilotMaxMessages": a.get("autoPilotMaxMessages") or 100,
    "knowledgeBaseIds": a.get("knowledgeBaseIds") or ["HjJZbTH2w5riiz6GeC5y"],
    "respondToImages": True if a.get("respondToImages") is None else a.get("respondToImages"),
    "respondToAudio": True if a.get("respondToAudio") is None else a.get("respondToAudio"),
    "sleepOnManualMessage": bool(a.get("sleepOnManualMessage")),
    "sleepOnWorkflowMessage": bool(a.get("sleepOnWorkflowMessage")),
}

print("\n=== PUT full isPrimary true ===")
ok = False
for ver in ("2021-07-28", "v3"):
    st, resp = req("PUT", f"/conversation-ai/agents/{AGENT}", full, version=ver)
    print(f"PUT ver={ver} {st}")
    if st not in (200, 201):
        print(str(resp)[:600])
        continue
    r = unwrap(resp) if isinstance(resp, dict) else {}
    print(
        " PUT isPrimary=",
        r.get("isPrimary") if isinstance(r, dict) else None,
        "in_keys=",
        isinstance(r, dict) and "isPrimary" in r,
        "mode=",
        r.get("mode") if isinstance(r, dict) else None,
        "channels=",
        r.get("channels") if isinstance(r, dict) else None,
    )
    st2, after = req("GET", f"/conversation-ai/agents/{AGENT}", version=ver)
    a2 = unwrap(after)
    print(
        " GET isPrimary=",
        a2.get("isPrimary") if isinstance(a2, dict) else None,
        "in_keys=",
        isinstance(a2, dict) and "isPrimary" in a2,
        "mode=",
        a2.get("mode") if isinstance(a2, dict) else None,
        "ERRO GRAVE=",
        "ERRO GRAVE 01/09/2026" in (a2.get("instructions") or "") if isinstance(a2, dict) else False,
    )
    dump_search("after", ver)
    # success if GET/PUT/search shows true
    ch_ok = False
    st3, s = req("GET", "/conversation-ai/agents/search?limit=20", version=ver)
    if isinstance(s, dict):
        for ag in s.get("agents") or []:
            if ag.get("id") != AGENT:
                continue
            if ag.get("isPrimary") is True:
                ch_ok = True
            for c in ag.get("channels") or []:
                if isinstance(c, dict) and c.get("name") == "WhatsApp" and c.get("isPrimary") is True:
                    ch_ok = True
    if (isinstance(r, dict) and r.get("isPrimary") is True) or (
        isinstance(a2, dict) and a2.get("isPrimary") is True
    ) or ch_ok:
        print("OK primary restored with version", ver)
        ok = True
        (OUT / "agent-after-primary-fix.json").write_text(
            json.dumps(a2 if isinstance(a2, dict) else r, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        break

if not ok:
    print("\nAINDA NÃO CONFIRMOU isPrimary=true no GET/search")
    # last dump
    dump_search("final", "2021-07-28")
    dump_search("final", "v3")
