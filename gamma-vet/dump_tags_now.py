# -*- coding: utf-8 -*-
import json, urllib.request
from pathlib import Path
ENV = Path(r"c:\Users\GC1\Desktop\Automação GHL\.env")
vals = {}
for line in ENV.read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k,v=line.split("=",1); vals[k.strip()]=v.strip()
KEY=vals["GHL_CARTAO_TODOS_CG_API_KEY"]; LOC=vals["GHL_CARTAO_TODOS_CG_LOCATION_ID"]
r=urllib.request.Request(f"https://services.leadconnectorhq.com/locations/{LOC}/tags", headers={"Authorization":f"Bearer {KEY}","Version":"2021-07-28","Accept":"application/json","User-Agent":"Mozilla/5.0"})
with urllib.request.urlopen(r, timeout=60) as resp:
    tags=[t.get("name") for t in json.loads(resp.read().decode("utf-8")).get("tags") or []]
hits=[n for n in tags if "trafego" in n.lower() or "legenda" in n.lower() or "cdt" in n.lower() or n.lower() in ("5-sus","sus","6-ana maria","ana mari")]
Path(r"c:\Users\GC1\Desktop\Automação GHL\gamma-vet\cartao-tags-now.json").write_text(json.dumps(hits, ensure_ascii=False, indent=2), encoding="utf-8")
