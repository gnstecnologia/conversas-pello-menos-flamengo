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
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        print("ERR", method, url, e.code, e.read().decode("utf-8", errors="replace")[:1200])
        return None


url = f"https://services.leadconnectorhq.com/calendars/schedules/search?locationId={LOC}&userId={UID}"
print("GET", url)
data = req("GET", url)
print(json.dumps(data, ensure_ascii=False, indent=2)[:8000] if data else "none")
