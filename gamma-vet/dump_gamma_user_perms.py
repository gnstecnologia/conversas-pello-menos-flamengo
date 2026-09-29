# -*- coding: utf-8 -*-
import json
import urllib.request
from pathlib import Path

ENV = Path(r"c:\Users\GC1\Desktop\Automação GHL\.env")
OUT = Path(r"c:\Users\GC1\Desktop\Automação GHL\gamma-vet\gamma-users-perms.json")
vals = {}
for line in ENV.read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()
KEY = vals["GHL_GAMMA_API_KEY"]
LOC = vals["GHL_GAMMA_LOCATION_ID"]
h = {
    "Authorization": f"Bearer {KEY}",
    "Version": "2021-07-28",
    "Accept": "application/json",
    "User-Agent": "Mozilla/5.0",
}

ids = [
    "LxQOtMzWVhRqNLlWnLCI",
    "Daia1y3n2C1F1VfXIdvV",
    "2XSRsWDCgmL11WFIerwr",
    "NZhcmQNt4ubbz5YruDU9",
    "XXh1AeDBl3URNuqBZgiZ",
    "N6PlrM7lGh6ej4R869sH",
    "kSZcuwcDWLcaEfX9BwEC",
]
rows = []
for uid in ids:
    r = urllib.request.Request(f"https://services.leadconnectorhq.com/users/{uid}", headers=h)
    with urllib.request.urlopen(r, timeout=60) as resp:
        u = json.loads(resp.read().decode("utf-8"))
    perms = u.get("permissions") or {}
    on = sorted([k for k, v in perms.items() if v])
    rows.append(
        {
            "id": u.get("id"),
            "name": u.get("name"),
            "email": u.get("email"),
            "role": (u.get("roles") or {}).get("role"),
            "on": on,
        }
    )

OUT.write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
print("wrote")
for x in rows:
    print(x["name"], x["role"], "|", ", ".join(x["on"]))
