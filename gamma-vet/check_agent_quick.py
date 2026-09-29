# -*- coding: utf-8 -*-
import json
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
vals = {}
for line in Path(r"c:\Users\GC1\Desktop\Automação GHL\.env").read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()
TOKEN = vals["GHL_GAMMA_API_KEY"]
AGENT = vals["GHL_GAMMA_AGENT_ID"]
LOC = vals["GHL_GAMMA_LOCATION_ID"]


def get(url):
    cmd = [
        "curl.exe", "-s", url,
        "-H", f"Authorization: Bearer {TOKEN}",
        "-H", "Version: 2021-04-15",
        "-H", "Accept: application/json",
        "-H", "User-Agent: Mozilla/5.0",
    ]
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace").stdout


raw = get(f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}?locationId={LOC}")
d = json.loads(raw)
a = d.get("agent") or d.get("data") or d
print("top", list(d.keys())[:8])
print("mode", a.get("mode"), "channels", a.get("channels"), "primary", a.get("isPrimary"))
inst = a.get("instructions") or ""
print("inst len", len(inst), "15:30", "15:30" in inst, "250", "250" in inst, "110", "110" in inst)

raw = get(f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}/actions/g4K4spRJdKq1zpMr2LLb")
b = json.loads(raw)
details = (b.get("data") or b).get("details") or {}
for x in details.get("calendarIds") or []:
    t = x.get("triggerCondition") or ""
    if "TIREOIDE" in t or "Cintilo" in t or "Raio-X" in t:
        print("---")
        print(t)
print("aiDesc:", (details.get("aiDescription") or "")[:300])
