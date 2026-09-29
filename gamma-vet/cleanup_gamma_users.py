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
KEY = vals["GHL_GAMMA_API_KEY"]
LOC = vals["GHL_GAMMA_LOCATION_ID"]
OFFICIAL = {
    "marcello.comodo@gammavet.com.br",
    "mariana.gantois@gammavet.com.br",
    "gustavo.cobucci@gammavet.com.br",
    "marcella_rosa@me.com",
    "nanda.meirelles1@gmail.com",
    "agendamento@gammavet.com.br",
}


def req(method, url, body=None):
    data = None if body is None else json.dumps(body).encode("utf-8")
    r = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {KEY}",
            "Version": "2021-07-28",
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "Mozilla/5.0",
        },
    )
    try:
        with urllib.request.urlopen(r, timeout=90) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = raw
        return e.code, parsed
    except Exception as ex:
        return 0, str(ex)


code, data = req("GET", f"https://services.leadconnectorhq.com/users/?locationId={LOC}")
users = (data or {}).get("users") or []
print("BEFORE", code, len(users))
for u in users:
    email = (u.get("email") or "").lower()
    print("-", u.get("name"), email, (u.get("roles") or {}).get("role"), u.get("id"))
    if email not in OFFICIAL:
        print("  DELETE", email)
        dcode, dbody = req("DELETE", f"https://services.leadconnectorhq.com/users/{u['id']}")
        print("  ->", dcode, str(dbody)[:220])

code2, data2 = req("GET", f"https://services.leadconnectorhq.com/users/?locationId={LOC}")
users2 = (data2 or {}).get("users") or []
print("AFTER", code2, len(users2))
for u in users2:
    print("KEEP", u.get("name"), u.get("email"), (u.get("roles") or {}).get("role"), u.get("id"))
