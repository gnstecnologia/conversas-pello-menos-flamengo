# -*- coding: utf-8 -*-
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
vals = {}
for line in Path(r"c:\Users\GC1\Desktop\Automação GHL\.env").read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()
KEY = vals["GHL_AGENCY_API_KEY"]
BASE = "https://services.leadconnectorhq.com"
r = urllib.request.Request(
    BASE + "/locations/search?limit=100",
    headers={
        "Authorization": "Bearer " + KEY,
        "Version": "2021-07-28",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0",
    },
)
try:
    with urllib.request.urlopen(r, timeout=60) as resp:
        data = json.loads(resp.read().decode())
except urllib.error.HTTPError as e:
    print("ERR", e.code, e.read().decode(errors="replace")[:300])
    raise SystemExit(1)
locs = data.get("locations") or []
print("n", len(locs), "keys", list(data)[:8])
for loc in locs:
    name = loc.get("name") or ""
    blob = name.lower()
    if "pello" in blob or "copa" in blob:
        print(loc.get("id"), "|", name, "|", loc.get("companyId"))
