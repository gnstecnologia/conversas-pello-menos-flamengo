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


paths = [
    ("/users/me", "2021-07-28"),
    ("/oauth/installedLocations?limit=20", "2021-07-28"),
    ("/calendars/?limit=5", "2021-04-15"),
    ("/contacts/?limit=1", "2021-07-28"),
    ("/conversations/search?limit=1", "2021-04-15"),
    ("/opportunities/search?limit=1", "2021-07-28"),
    ("/workflows/?limit=5", "2021-07-28"),
    ("/locations/", "2021-07-28"),
]
for path, ver in paths:
    st, data = req("https://services.leadconnectorhq.com" + path, ver)
    snippet = ""
    if isinstance(data, dict):
        snippet = json.dumps({k: data.get(k) for k in list(data)[:8]}, ensure_ascii=False)[:400]
        # hunt locationId
        blob = json.dumps(data)
        if "locationId" in blob or '"id"' in blob:
            pass
    else:
        snippet = str(data)[:300]
    print(path, st, snippet)
    print()
