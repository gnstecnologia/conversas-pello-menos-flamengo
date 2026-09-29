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
        with urllib.request.urlopen(r, timeout=30) as resp:
            return json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        return {"error": e.code, "body": e.read().decode("utf-8", "replace")[:600]}


NEEDLES = ("jose", "josé", "sjc", "campos", "icatu", "spsjc", "sao jose")
pairs = [
    ("PELLO", vals["GHL_PELLO_API_KEY"], vals["GHL_PELLO_LOCATION_ID"]),
    ("PELLO_URG", vals["GHL_PELLO_URG_API_KEY"], vals["GHL_PELLO_URG_LOCATION_ID"]),
]

for name, key, loc in pairs:
    print("\n====", name, loc, "====")
    locd = req(key, f"https://services.leadconnectorhq.com/locations/{loc}")
    o = locd.get("location", locd) if isinstance(locd, dict) else {}
    print("LOC", o.get("name"), "|", o.get("city"), "|", o.get("address"))
    users = req(key, f"https://services.leadconnectorhq.com/users/?locationId={loc}")
    ulist = users.get("users") or []
    print("users", len(ulist), "err", users.get("error"))
    for u in ulist:
        nm = " ".join(filter(None, [u.get("firstName"), u.get("lastName")])) or u.get("name") or ""
        em = u.get("email") or ""
        blob = (nm + " " + em).lower()
        flag = " <== SJC?" if any(n in blob for n in NEEDLES) else ""
        role = (u.get("roles") or {}).get("role")
        print(" ", u.get("id"), "|", nm, "|", em, "|", role, flag)

    for q in ("Sao Jose", "SJC", "Pello", "Campos"):
        searched = req(
            key,
            "https://services.leadconnectorhq.com/locations/search",
            method="POST",
            body={"companyId": o.get("companyId"), "query": q},
        )
        locs = searched.get("locations") or searched.get("data") or []
        print("search", q, searched.get("error") or (len(locs) if isinstance(locs, list) else searched))
        if isinstance(locs, list):
            for L in locs:
                print("  loc", L.get("id"), "|", L.get("name"), "|", L.get("city"), "|", L.get("address"))
