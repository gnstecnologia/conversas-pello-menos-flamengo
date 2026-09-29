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
r = urllib.request.Request(
    "https://services.leadconnectorhq.com/conversation-ai/agents/search?limit=20",
    headers={
        "Authorization": f"Bearer {key}",
        "Version": "2021-07-28",
        "Accept": "application/json",
        "Location-Id": "3R4hY0j3TJyj2SkmSQL3",
        "User-Agent": "Mozilla/5.0",
    },
)
with urllib.request.urlopen(r, timeout=60) as resp:
    data = json.loads(resp.read().decode())
for ag in data.get("agents") or []:
    print("===", ag.get("name"), ag.get("id"))
    print("keys:", sorted(ag.keys()))
    for k in ag:
        if "prim" in k.lower() or "channel" in k.lower() or k in ("mode", "isPrimary", "primary"):
            print(f"  {k}={ag[k]!r}")
    # nested
    for k, v in ag.items():
        if isinstance(v, dict):
            for k2 in v:
                if "prim" in k2.lower():
                    print(f"  {k}.{k2}={v[k2]!r}")
Path(r"c:\Users\GC1\Desktop\Automação GHL\multiodonto-audit\agents-search-hoje.json").write_text(
    json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
)
print("wrote agents-search-hoje.json")
