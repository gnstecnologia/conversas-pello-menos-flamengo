# -*- coding: utf-8 -*-
import json
import sys
import urllib.parse
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
vals = {}
for line in Path(r"c:\Users\GC1\Desktop\Automação GHL\.env").read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()

AG = vals["GHL_AGENCY_API_KEY"]
COMPANY = vals["GHL_AGENCY_COMPANY_ID"]
BASE = "https://services.leadconnectorhq.com"


def search(q, limit=100):
    url = BASE + "/locations/search?" + urllib.parse.urlencode(
        {"companyId": COMPANY, "query": q, "limit": limit}
    )
    r = urllib.request.Request(
        url,
        headers={
            "Authorization": "Bearer " + AG,
            "Version": "2021-07-28",
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
        },
    )
    with urllib.request.urlopen(r, timeout=60) as resp:
        return json.loads(resp.read().decode()).get("locations") or []


seen = {}
for q in ["Pello", "Pello Menos", "PELLO", "Franquia", "MODELO"]:
    for L in search(q):
        name = (L.get("name") or "").lower()
        if "pello" not in name and "franquia" not in name:
            continue
        lid = L.get("id")
        if lid and lid not in seen:
            seen[lid] = L

rows = sorted(seen.values(), key=lambda x: (x.get("name") or "").lower())
print("total", len(rows))
for i, L in enumerate(rows, 1):
    name = (L.get("name") or "").strip()
    city = (L.get("city") or "").strip()
    print(f"{i}. {name} | {L.get('id')} | {city}")
