# -*- coding: utf-8 -*-
import json
import urllib.request
from pathlib import Path

ENV = Path(r"c:\Users\GC1\Desktop\Automação GHL\.env")
key = None
for line in ENV.read_text(encoding="utf-8").splitlines():
    if line.startswith("GHL_MULTIODONTO_API_KEY="):
        key = line.split("=", 1)[1].strip()
        break

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
AGENT = "3Fzfmx7ViwyD9v16h4DR"
ACTION = "zeWiS2QJD0LcF6UOaejG"
LOC = "3R4hY0j3TJyj2SkmSQL3"
OUT = Path(r"c:\Users\GC1\Desktop\Automação GHL\multiodonto-audit")


def req(method, url, body=None):
    data = None if body is None else json.dumps(body).encode("utf-8")
    r = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {key}",
            "Version": "2021-07-28",
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": UA,
        },
    )
    try:
        with urllib.request.urlopen(r, timeout=90) as resp:
            return resp.status, json.loads(resp.read().decode())
    except Exception as e:
        if hasattr(e, "read"):
            return getattr(e, "code", 0), e.read().decode(errors="replace")[:2000]
        return 0, str(e)


import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

st, agent = req("GET", f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}")
print("GET agent", st)
if isinstance(agent, dict):
    (OUT / "agent-live-20260831.json").write_text(
        json.dumps(agent, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    a = agent if "instructions" in agent else agent.get("data") or agent
    inst = a.get("instructions") or ""
    print("name:", a.get("name"))
    print("isPrimary:", a.get("isPrimary"))
    print("mode:", a.get("mode"))
    print("kb:", a.get("knowledgeBaseIds"))
    print("instr_len:", len(inst))
    needles = [
        "Bianca",
        "legado",
        "nao atende mais",
        "Endodontia",
        "canal",
        "Appai",
        "APPAI",
        "hoje",
        "mesmo dia",
        "SulAmerica",
        "Hapvida",
    ]
    for n in needles:
        print(f"  prompt has [{n}]:", n.lower() in inst.lower())
    print("--- BIANCA CONTEXT ---")
    i = inst.lower().find("bianca")
    if i >= 0:
        print(inst[max(0, i - 80) : i + 180])
    print("--- APPAI CONTEXT ---")
    for needle in ["Appai", "APPAI", "bloqueados"]:
        i = inst.find(needle)
        if i >= 0:
            print(inst[i : i + 500])
            break
    print("--- ENDO CONTEXT ---")
    i = inst.lower().find("endodont")
    if i >= 0:
        print(inst[max(0, i - 80) : i + 280])
    print("--- CONV BLOCK ---")
    i = inst.lower().find("conv")
    j = inst.lower().find("convenios bloqueados")
    if j >= 0:
        print(inst[j : j + 700])

st, act = req("GET", f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}/actions/{ACTION}")
print("\nGET action", st)
if isinstance(act, dict):
    (OUT / "action-live-20260831.json").write_text(
        json.dumps(act, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    data = act.get("data") or act
    details = data.get("details") or {}
    cals = details.get("calendarIds") or []
    print("aiDescription:", (details.get("aiDescription") or "")[:800])
    print("calendar count:", len(cals))
    for c in cals:
        cid = c.get("id") if isinstance(c, dict) else c
        trig = c.get("triggerCondition", "") if isinstance(c, dict) else ""
        print(" -", cid, "|", trig[:120])

st, cals = req("GET", f"https://services.leadconnectorhq.com/calendars/?locationId={LOC}")
print("\nGET cals", st)
if isinstance(cals, dict):
    (OUT / "cals-live-20260831.json").write_text(
        json.dumps(cals, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    rows = cals.get("calendars") or []
    print("total calendars:", len(rows))
    print("--- ALL CAL NAMES ---")
    for c in rows:
        name = c.get("name") or ""
        line = f"  {c.get('calendarType')} | {c.get('id')} | {name} | active={c.get('isActive')}"
        print(line)
        low = name.lower()
        if "bianca" in low or "goes" in low or "legado" in low:
            print("  *** BIANCA/LEGADO MATCH ***")

st, users = req("GET", f"https://services.leadconnectorhq.com/users/?locationId={LOC}")
print("\nGET users", st)
if isinstance(users, dict):
    for u in users.get("users") or []:
        fn = f"{u.get('firstName','')} {u.get('lastName','')}".strip()
        print(" user:", fn, u.get("id"), "deleted" if u.get("deleted") else "")
        if "bianca" in fn.lower() or "goes" in fn.lower():
            print("  *** BIANCA USER ***")
