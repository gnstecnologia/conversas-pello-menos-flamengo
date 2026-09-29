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
UID = "LxQOtMzWVhRqNLlWnLCI"
UA = "Mozilla/5.0"


def req(method, url, version="2021-07-28"):
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
        print("ERR", e.code, e.read().decode("utf-8", errors="replace")[:800])
        return None


u = req("GET", f"https://services.leadconnectorhq.com/users/{UID}")
print("keys", list((u or {}).keys()) if isinstance(u, dict) else type(u))
# dump without huge scopes
if isinstance(u, dict):
    user = u.get("user", u)
    skip = {"scopes", "permissions", "roles"}
    slim = {k: user.get(k) for k in user if k not in skip}
    print(json.dumps(slim, ensure_ascii=False, indent=2)[:6000])

print("\n--- user search ---")
s = req("GET", f"https://services.leadconnectorhq.com/users/search?locationId={LOC}&query=")
if s:
    print(str(s)[:2000])
