# -*- coding: utf-8 -*-
import json
import urllib.request
from pathlib import Path

ENV = Path(r"c:\Users\GC1\Desktop\Automação GHL\.env")
OUT = Path(r"c:\Users\GC1\Desktop\Automação GHL\gamma-vet\ehmedical-system-prompt.txt")
vals = {}
for line in ENV.read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()

KEY = vals["GHL_EHMEDICAL_API_KEY"]
AGENT = "X4ctLzGA1JxYDopKofGa"
h = {
    "Authorization": f"Bearer {KEY}",
    "Version": "2021-07-28",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0",
}
r = urllib.request.Request(
    f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}",
    headers=h,
)
with urllib.request.urlopen(r, timeout=60) as resp:
    d = json.loads(resp.read().decode("utf-8"))
a = d.get("agent") or d

parts = []
parts.append("=== NAME ===")
parts.append(str(a.get("name")))
parts.append("=== MODE / PRIMARY ===")
parts.append(f"mode={a.get('mode')} primary={a.get('isPrimary')}")
parts.append("")
parts.append("===== PERSONALITY =====")
parts.append(a.get("personality") or "")
parts.append("")
parts.append("===== GOAL =====")
parts.append(a.get("goal") or "")
parts.append("")
parts.append("===== INSTRUCTIONS =====")
parts.append(a.get("instructions") or "")
for f in ["additionalInformation", "prompt", "systemPrompt", "role", "intent"]:
    if a.get(f):
        parts.append("")
        parts.append(f"===== {f.upper()} =====")
        parts.append(str(a.get(f)))

text = "\n".join(parts)
OUT.write_text(text, encoding="utf-8")
print("saved", OUT)
print("len personality", len(a.get("personality") or ""))
print("len goal", len(a.get("goal") or ""))
print("len instructions", len(a.get("instructions") or ""))
