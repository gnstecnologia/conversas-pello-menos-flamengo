# -*- coding: utf-8 -*-
import json
import urllib.error
import urllib.request
from pathlib import Path

ENV = Path(r"c:\Users\GC1\Desktop\Automação GHL\.env")
vals = {}
for line in ENV.read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()

NEW = "pit-386e1357-bc11-4b1a-be39-a6dfa5ed08eb"
FK = vals["GHL_PELLO_API_KEY"]


def get(key, url):
    r = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {key}",
            "Version": "2021-07-28",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
        },
    )
    try:
        with urllib.request.urlopen(r, timeout=45) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", errors="replace")[:200]
    except Exception as ex:
        return 0, str(ex)


# collect location ids from franchising users + Marcus
r = urllib.request.Request(
    "https://services.leadconnectorhq.com/users/?locationId=wi4al7UGFzPEEJxK3xJg",
    headers={
        "Authorization": f"Bearer {FK}",
        "Version": "2021-07-28",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0",
    },
)
with urllib.request.urlopen(r, timeout=60) as resp:
    users = json.loads(resp.read().decode()).get("users") or []
locs = set()
for u in users:
    for lid in ((u.get("roles") or {}).get("locationIds") or []):
        locs.add(lid)
print("locs", len(locs))

# also try NEW DIGITAL / all env pits for locations/search
for k, v in vals.items():
    if "API_KEY" not in k or not str(v).startswith("pit-"):
        continue
    code, data = get(v, "https://services.leadconnectorhq.com/locations/search?limit=100")
    if code == 200 and isinstance(data, dict):
        found = data.get("locations") or []
        print("search via", k, "n=", len(found))
        for L in found:
            name = (L.get("name") or "").lower()
            if "pello" in name or "modelo" in name or "m modelo" in name:
                print("  NAME HIT", L.get("id"), L.get("name"))
                locs.add(L.get("id"))

hits = []
for loc in sorted(locs):
    # try GET location
    code, data = get(NEW, f"https://services.leadconnectorhq.com/locations/{loc}")
    if code == 200 and isinstance(data, dict):
        L = data.get("location") or data
        print("LOC HIT", loc, L.get("name"))
        hits.append((loc, L.get("name")))
        continue
    # calendars
    c2, d2 = get(NEW, f"https://services.leadconnectorhq.com/calendars/?locationId={loc}")
    if c2 == 200:
        # get name with franchising key
        c3, d3 = get(FK, f"https://services.leadconnectorhq.com/locations/{loc}")
        name = ((d3.get("location") or d3).get("name") if isinstance(d3, dict) else "?")
        print("CAL HIT", loc, name, "cals", len((d2 or {}).get("calendars") or []))
        hits.append((loc, name))

print("TOTAL HITS", len(hits))
for h in hits:
    print(h)
