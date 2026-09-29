# -*- coding: utf-8 -*-
import json
import urllib.request
import urllib.error

ENV = r"c:\Users\GC1\Desktop\Automação GHL\.env"
vals = {}
with open(ENV, encoding="utf-8") as f:
    for line in f:
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            vals[k.strip()] = v.strip()

KEY = vals["GHL_GAMMA_API_KEY"]
LOC = vals["GHL_GAMMA_LOCATION_ID"]
UA = "Mozilla/5.0"


def req(method, url, version="2021-04-15"):
    r = urllib.request.Request(
        url,
        method=method,
        headers={
            "Authorization": f"Bearer {KEY}",
            "Version": version,
            "Accept": "application/json",
            "User-Agent": UA,
        },
    )
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print("ERR", method, url, e.code, e.read().decode("utf-8", errors="replace")[:500])
        return None


data = req("GET", f"https://services.leadconnectorhq.com/calendars/?locationId={LOC}")
cals = (data or {}).get("calendars") or []
print("count", len(cals))
for c in cals:
    tms = c.get("teamMembers") or []
    uids = [m.get("userId") for m in tms]
    print(c.get("id"), "|", c.get("name"), "| type=", c.get("calendarType"), "| users=", uids, "| slot=", c.get("slotDuration"))
