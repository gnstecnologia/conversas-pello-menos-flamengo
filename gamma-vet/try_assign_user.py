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
UID = "LxQOtMzWVhRqNLlWnLCI"
CID = "67dUBkMOw78GdahUsc1t"
UA = "Mozilla/5.0"


def req(method, url, body=None, version="2021-04-15"):
    data = None if body is None else json.dumps(body).encode("utf-8")
    r = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {KEY}",
            "Version": version,
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": UA,
        },
    )
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        print("ERR", e.code, e.read().decode("utf-8", errors="replace")[:800])
        return None


u = req("GET", f"https://services.leadconnectorhq.com/users/{UID}", version="2021-07-28")
print("permissions", json.dumps((u or {}).get("permissions"), ensure_ascii=False, indent=2)[:2500])
print("roles", (u or {}).get("roles"))

# try assigning team member with GET-then-merge of existing openHours
cal = req("GET", f"https://services.leadconnectorhq.com/calendars/{CID}")
cal = (cal or {}).get("calendar", cal)
print("before members", cal.get("teamMembers"))

tm = [{
    "priority": 0.5,
    "selected": True,
    "userId": UID,
    "isPrimary": True,
    "isZoomAdded": False,
    "locationConfigurations": [
        {"kind": "custom", "location": "Gamma Vet", "position": 0}
    ],
}]
oh = cal.get("openHours")
# try several PUT shapes — sempre reenviar openHours para não apagar
for i, payload in enumerate([
    {"openHours": oh, "teamMembers": tm},
    {"openHours": oh, "teamMembers": [{"userId": UID, "selected": True, "priority": 0.5}]},
    {"openHours": oh, "assignedUserId": UID},
    {"openHours": oh, "userId": UID},
], 1):
    print("\nTRY", i, list(payload.keys()), payload.get("assignedUserId") or payload.get("userId") or "")
    out = req("PUT", f"https://services.leadconnectorhq.com/calendars/{CID}", payload)
    if not out:
        continue
    c = out.get("calendar", out)
    print("  members", c.get("teamMembers"), "assigned", c.get("assignedUserId"), "keys has assigned?", "assignedUserId" in c)
