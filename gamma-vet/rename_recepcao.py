# -*- coding: utf-8 -*-
import json, urllib.request, urllib.error
from pathlib import Path
vals={}
for line in Path(r"c:\Users\GC1\Desktop\Automação GHL\.env").read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k,v=line.split("=",1); vals[k.strip()]=v.strip()
KEY=vals["GHL_GAMMA_API_KEY"]; LOC=vals["GHL_GAMMA_LOCATION_ID"]
body={"firstName":"Raquel e Yasmin","lastName":"Recepcao","role":"user","type":"account","locationIds":[LOC]}
req=urllib.request.Request(
    "https://services.leadconnectorhq.com/users/kSZcuwcDWLcaEfX9BwEC",
    data=json.dumps(body).encode("utf-8"),
    method="PUT",
    headers={"Authorization":f"Bearer {KEY}","Version":"2021-07-28","Accept":"application/json","Content-Type":"application/json; charset=utf-8","User-Agent":"Mozilla/5.0"},
)
with urllib.request.urlopen(req, timeout=60) as resp:
    u=json.loads(resp.read().decode())
print(u.get("name"), u.get("email"), (u.get("roles") or {}).get("role"))
