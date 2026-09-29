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

UA = "Mozilla/5.0"


def req(key, url, method="GET", body=None, version="2021-07-28"):
    data = None if body is None else json.dumps(body).encode("utf-8")
    r = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {key}",
            "Version": version,
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": UA,
        },
    )
    try:
        with urllib.request.urlopen(r, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"error": e.code, "body": e.read().decode("utf-8", errors="replace")[:400]}


pairs = [
    ("PELLO", vals.get("GHL_PELLO_API_KEY"), vals.get("GHL_PELLO_LOCATION_ID")),
    ("PELLO_URG", vals.get("GHL_PELLO_URG_API_KEY"), vals.get("GHL_PELLO_URG_LOCATION_ID")),
]

for name, key, loc in pairs:
    print("\n====", name, "====")
    loc_data = req(key, f"https://services.leadconnectorhq.com/locations/{loc}")
    loc_obj = loc_data.get("location", loc_data) if isinstance(loc_data, dict) else {}
    print("id:", loc)
    print("name:", loc_obj.get("name"))
    print("address:", loc_obj.get("address"), loc_obj.get("city"), loc_obj.get("state"))
    print("companyId:", loc_obj.get("companyId"))
    searched = req(
        key,
        "https://services.leadconnectorhq.com/locations/search",
        method="POST",
        body={"companyId": loc_obj.get("companyId"), "query": "Pello"},
    )
    print("search", searched.get("error") if isinstance(searched, dict) and searched.get("error") else "ok")
    locs = []
    if isinstance(searched, dict):
        locs = searched.get("locations") or searched.get("data") or []
        if searched.get("error"):
            print(" ", searched.get("body", "")[:200])
    for L in locs[:30] if isinstance(locs, list) else []:
        print(" -", L.get("id"), "|", L.get("name"), "|", L.get("address"), L.get("city"))
