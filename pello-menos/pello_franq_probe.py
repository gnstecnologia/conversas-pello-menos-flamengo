# -*- coding: utf-8 -*-
import json
import sys
import urllib.error
import urllib.request

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
KEY = "pit-7331cc7a-71ca-4f50-983c-420a4b70290b"


def req(url, ver="2021-07-28"):
    r = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {KEY}",
            "Version": ver,
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
        },
    )
    try:
        with urllib.request.urlopen(r, timeout=45) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = raw
        return e.code, parsed


print("=== agents ===")
st, data = req("https://services.leadconnectorhq.com/conversation-ai/agents/search?limit=20", "2021-04-15")
print("HTTP", st)
agents = (data or {}).get("agents") or [] if isinstance(data, dict) else []
locs = set()
for a in agents:
    print(" AG", a.get("id"), a.get("name"), a.get("locationId"), a.get("mode"))
    if a.get("locationId"):
        locs.add(a["locationId"])

print("=== locations/search ===")
st, data = req("https://services.leadconnectorhq.com/locations/search?limit=20")
print("HTTP", st, str(data)[:250] if not isinstance(data, dict) else list(data.keys()))
if isinstance(data, dict):
    for x in data.get("locations") or []:
        print(" LOC", x.get("id"), x.get("name"))
        locs.add(x["id"])

if not locs:
    print("no loc from search/agents")

for loc in locs:
    print("\n=== location", loc, "===")
    st, data = req(f"https://services.leadconnectorhq.com/locations/{loc}")
    L = data.get("location") or data if isinstance(data, dict) else {}
    print("name", L.get("name") if isinstance(L, dict) else data)
    st, data = req(f"https://services.leadconnectorhq.com/users/?locationId={loc}")
    users = (data or {}).get("users") or [] if isinstance(data, dict) else []
    print("users HTTP", st, "n", len(users) if isinstance(users, list) else data)
    if isinstance(users, list):
        for u in users:
            roles = u.get("roles") or {}
            print(" ", u.get("id"), "|", u.get("name"), "|", u.get("email"), "|", roles.get("role"), roles.get("type"))
