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

pairs = [
    ("PELLO", vals.get("GHL_PELLO_API_KEY"), vals.get("GHL_PELLO_LOCATION_ID")),
    ("PELLO_URG", vals.get("GHL_PELLO_URG_API_KEY"), vals.get("GHL_PELLO_URG_LOCATION_ID")),
    ("PELLO_MODELO", vals.get("GHL_PELLO_MODELO_API_KEY"), vals.get("GHL_PELLO_MODELO_LOCATION_ID")),
]


def req(key, url, method="GET", body=None):
    data = None if body is None else json.dumps(body).encode()
    r = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {key}",
            "Version": "2021-07-28",
            "Accept": "application/json",
            "Content-Type": "application/json",
            "User-Agent": "Mozilla/5.0",
        },
    )
    try:
        with urllib.request.urlopen(r, timeout=45) as resp:
            return json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return {"error": e.code, "body": e.read().decode("utf-8", "replace")[:800]}


for name, key, loc in pairs:
    print("\n====", name, loc, "====")
    if not key or not loc:
        print(" missing key/loc")
        continue
    locd = req(key, f"https://services.leadconnectorhq.com/locations/{loc}")
    o = locd.get("location", locd) if isinstance(locd, dict) else {}
    print("LOC", o.get("name"), "|", o.get("email"), "|", o.get("city"), "|", o.get("address"))
    print("loc email fields", {k: o.get(k) for k in o.keys() if "mail" in k.lower() or k in ("name", "phone", "website")})
    users = req(key, f"https://services.leadconnectorhq.com/users/?locationId={loc}")
    ulist = users.get("users") or []
    print("users", len(ulist), "err", users.get("error"))
    for u in ulist:
        nm = " ".join(filter(None, [u.get("firstName"), u.get("lastName")])) or u.get("name") or ""
        em = u.get("email") or ""
        role = (u.get("roles") or {}).get("role")
        print(" ", nm, "|", em, "|", role, "|", u.get("id"))
        blob = (nm + " " + em).lower()
        if any(x in blob for x in ("bot", "hut", "botafogo", "pello")):
            print("   *** match")
