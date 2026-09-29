# -*- coding: utf-8 -*-
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ENV = Path(r"c:\Users\GC1\Desktop\Automação GHL\.env")
vals = {}
for line in ENV.read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()

FK = vals["GHL_PELLO_API_KEY"]
FLOC = vals["GHL_PELLO_LOCATION_ID"]
FRANQ = vals["GHL_PELLO_FRANQ_API_KEY"]


def req(key, url, ver="2021-07-28"):
    r = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {key}",
            "Version": ver,
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
        },
    )
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = raw
        return e.code, parsed


st, data = req(FK, f"https://services.leadconnectorhq.com/users/?locationId={FLOC}")
users = (data or {}).get("users") or []
ids = set()
for u in users:
    roles = u.get("roles") or {}
    if roles.get("type") == "agency":
        for lid in roles.get("locationIds") or []:
            ids.add(lid)
        print("agency", u.get("name"), "locs", len(roles.get("locationIds") or []))

print("unique locs", len(ids))
hit = None
for lid in sorted(ids):
    st, data = req(FRANQ, f"https://services.leadconnectorhq.com/locations/{lid}")
    if st == 200 and isinstance(data, dict):
        L = data.get("location") or data
        name = L.get("name") if isinstance(L, dict) else ""
        print("HIT", lid, name)
        hit = (lid, name, L)
        break
    elif st not in (401, 403):
        print("other", lid, st, str(data)[:120])

if not hit:
    print("no location accepted this PIT among agency locationIds")
else:
    lid, name, L = hit
    st, data = req(FRANQ, f"https://services.leadconnectorhq.com/users/?locationId={lid}")
    users = (data or {}).get("users") or [] if isinstance(data, dict) else []
    print("users", st, len(users) if isinstance(users, list) else data)
    if isinstance(users, list):
        for u in users:
            roles = u.get("roles") or {}
            print(" ", u.get("id"), "|", u.get("name"), "|", u.get("email"), "|", roles.get("role"))
