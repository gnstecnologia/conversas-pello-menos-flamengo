# -*- coding: utf-8 -*-
import json, sys, urllib.request
from pathlib import Path
sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ENV = Path(r"c:\Users\GC1\Desktop\Automação GHL\.env")
key = None
for line in ENV.read_text(encoding="utf-8").splitlines():
    if line.startswith("GHL_MULTIODONTO_API_KEY="):
        key = line.split("=", 1)[1].strip()
        break
H = {
    "Authorization": f"Bearer {key}",
    "Version": "2021-07-28",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0",
    "Location-Id": "3R4hY0j3TJyj2SkmSQL3",
}

def get(path):
    r = urllib.request.Request("https://services.leadconnectorhq.com" + path, headers=H)
    with urllib.request.urlopen(r, timeout=60) as resp:
        return json.loads(resp.read().decode())

a = get("/conversation-ai/agents/3Fzfmx7ViwyD9v16h4DR")
instr = a.get("instructions") or ""
print("name", a.get("name"))
print("mode", a.get("mode"))
print("channels", a.get("channels"))
print("isPrimary GET", a.get("isPrimary"))
print("instr ERRO GRAVE", "ERRO GRAVE 01/09/2026" in instr)
print("instr terça SIM", "Terça: SIM Scherres" in instr)
print("instr NÃO Castro terça", "NÃO Castro, Thais, Giovanna, Rafael" in instr)
print("personality HOJE", "HOJE" in (a.get("personality") or ""))
print("goal Scherres", "Scherres" in (a.get("goal") or ""))

act = get("/conversation-ai/agents/3Fzfmx7ViwyD9v16h4DR/actions/zeWiS2QJD0LcF6UOaejG")
d = (act.get("data") or act).get("details") or {}
print("\naction desc has Ter SÓ / terça:", "Scherres" in (d.get("aiDescription") or "") and "HOJE" in (d.get("aiDescription") or ""))
print("action desc snippet:", (d.get("aiDescription") or "")[:220].replace("\n", " | "))
print("triggers:")
for c in d.get("calendarIds") or []:
    print(" -", (c.get("triggerCondition") or "")[:110])

s = get("/conversation-ai/agents/search?limit=20")
print("\nSEARCH")
for ag in s.get("agents") or []:
    print(ag.get("name"), "mode", ag.get("mode"), "topPrimary", ag.get("isPrimary"), "ch", ag.get("channels"))
