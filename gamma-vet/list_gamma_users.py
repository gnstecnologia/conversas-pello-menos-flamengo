# -*- coding: utf-8 -*-
import json
import urllib.request
from pathlib import Path

ENV = Path(r"c:\Users\GC1\Desktop\Automação GHL\.env")
OUT = Path(r"c:\Users\GC1\Desktop\Automação GHL\gamma-vet\gamma-users-live.json")
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

r = urllib.request.Request(
    f"https://services.leadconnectorhq.com/users/?locationId={LOC}",
    headers=h,
)
with urllib.request.urlopen(r, timeout=60) as resp:
    data = json.loads(resp.read().decode("utf-8"))

users = data.get("users") or []
rows = []
for u in users:
    roles = u.get("roles") or {}
    rows.append(
        {
            "id": u.get("id"),
            "name": u.get("name") or f"{u.get('firstName') or ''} {u.get('lastName') or ''}".strip(),
            "email": u.get("email"),
            "role": roles.get("role"),
            "type": roles.get("type"),
            "deleted": u.get("deleted"),
        }
    )

OUT.write_text(json.dumps({"locationId": LOC, "count": len(rows), "users": rows}, ensure_ascii=False, indent=2), encoding="utf-8")
print("count", len(rows))
for x in rows:
    print(f"{x['name']}\t{x['email']}\t{x['role']}\t{x['type']}\t{x['id']}")
