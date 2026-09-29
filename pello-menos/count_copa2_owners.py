# -*- coding: utf-8 -*-
"""Lista usuários da franchising e marca quem parece Copa 2."""
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ENV = Path(r"c:\Users\GC1\Desktop\Automação GHL\.env")
vals = {}
for line in ENV.read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.startswith("#"):
        k, v = line.split("=", 1)
        vals[k] = v.strip()

pairs = [
    ("franchising", vals["GHL_PELLO_API_KEY"], vals["GHL_PELLO_LOCATION_ID"]),
    ("franquia_matriz", vals["GHL_PELLO_FRANQUIA_API_KEY"], vals["GHL_PELLO_FRANQUIA_LOCATION_ID"]),
]
OUT = Path(r"c:\Users\GC1\Desktop\Automação GHL\pello-menos")


def get(key, url):
    r = urllib.request.Request(
        url,
        headers={
            "Authorization": "Bearer " + key,
            "Version": "2021-07-28",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
        },
    )
    try:
        with urllib.request.urlopen(r, timeout=90) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")[:400]


for label, key, loc in pairs:
    st, data = get(key, f"https://services.leadconnectorhq.com/users/?locationId={loc}")
    print("===", label, loc, st)
    if not isinstance(data, dict):
        print(str(data)[:300])
        continue
    users = data.get("users") or []
    print("n", len(users))
    rows = []
    for u in users:
        email = (u.get("email") or "").lower()
        name = " ".join(
            x for x in (u.get("name"), u.get("firstName"), u.get("lastName")) if x
        )
        blob = (email + " " + name).lower()
        hit = any(x in blob for x in ("scl", "copa", "copacabana", "siqueira"))
        mark = " *" if hit else ""
        print(u.get("id"), email, name, mark)
        rows.append({"id": u.get("id"), "email": email, "name": name, "hit": hit})
    (OUT / f"users-{label}.json").write_text(
        json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8"
    )
