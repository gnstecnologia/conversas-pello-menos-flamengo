# -*- coding: utf-8 -*-
import json, urllib.request
from pathlib import Path
vals={}
for line in Path(r"c:\Users\GC1\Desktop\Automação GHL\.env").read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k,v=line.split("=",1); vals[k.strip()]=v.strip()
KEY=vals["GHL_GAMMA_API_KEY"]; LOC=vals["GHL_GAMMA_LOCATION_ID"]
h={"Authorization":f"Bearer {KEY}","Version":"2021-07-28","Accept":"application/json","User-Agent":"Mozilla/5.0"}
r=urllib.request.Request(f"https://services.leadconnectorhq.com/users/?locationId={LOC}", headers=h)
with urllib.request.urlopen(r, timeout=60) as resp:
    users=json.loads(resp.read().decode()).get("users") or []
print("n", len(users))
for u in users:
    uid=u["id"]
    r2=urllib.request.Request(f"https://services.leadconnectorhq.com/users/{uid}", headers=h)
    with urllib.request.urlopen(r2, timeout=60) as resp:
        full=json.loads(resp.read().decode())
    p=full.get("permissions") or {}
    print(full.get("email"), "role=", (full.get("roles") or {}).get("role"),
          "conv=", p.get("conversationsEnabled"), "tags=", p.get("tagsEnabled"), "phone=", p.get("phoneCallEnabled"))
