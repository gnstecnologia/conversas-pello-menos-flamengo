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

FK = vals["GHL_PELLO_API_KEY"]
FLOC = vals["GHL_PELLO_LOCATION_ID"]
KEY = vals["GHL_PELLO_FRANQ_API_KEY"]
LOC = vals["GHL_PELLO_FRANQ_LOCATION_ID"]
UID = "HpVTiwskOWDTtqTOAAlN"
EMAIL = vals["GHL_WEB_EMAIL"]
PASSWORD = vals["GHL_WEB_PASSWORD"]


def req(key, method, url, body=None, extra=None, ver="2021-07-28"):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json; charset=utf-8",
        "User-Agent": "Mozilla/5.0",
    }
    if key:
        headers["Authorization"] = f"Bearer {key}"
        headers["Version"] = ver
    if extra:
        headers.update(extra)
    r = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(r, timeout=45) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}, dict(resp.headers)
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = raw
        return e.code, parsed, {}


for label, key, lid in [("franch", FK, FLOC), ("franq", KEY, LOC)]:
    st, data, _ = req(key, "GET", f"https://services.leadconnectorhq.com/locations/{lid}")
    L = data.get("location") or data if isinstance(data, dict) else {}
    print(label, L.get("name"), "company", L.get("companyId"), "id", L.get("id"))

st, data, _ = req(FK, "GET", f"https://services.leadconnectorhq.com/users/?locationId={FLOC}")
filipe = next((u for u in (data.get("users") or []) if "filipe" in (u.get("name") or "").lower()), None)
print("filipe franch", filipe.get("id") if filipe else None, filipe.get("email") if filipe else None)

# PUT variants
st, u, _ = req(FK, "GET", f"https://services.leadconnectorhq.com/users/{UID}")
perms = u.get("permissions") or {}
variants = [
    ("franq+loc header", KEY, {"type": "account", "role": "admin", "locationIds": [LOC]}, {"Location-Id": LOC}),
    ("franq min", KEY, {"role": "admin", "locationIds": [LOC], "type": "account"}, None),
    ("franq first/last", KEY, {"firstName": "Natasha", "lastName": "Souza", "type": "account", "role": "admin", "locationIds": [LOC], "permissions": perms}, None),
]
for name, key, body, extra in variants:
    st, b, _ = req(key, "PUT", f"https://services.leadconnectorhq.com/users/{UID}", body, extra)
    msg = b.get("message") if isinstance(b, dict) else str(b)[:180]
    roles = (b.get("roles") if isinstance(b, dict) else None)
    print("VAR", name, st, msg, roles)

# web login tries
login_bodies = [
    ("https://backend.leadconnectorhq.com/users/login", {"email": EMAIL, "password": PASSWORD}),
    ("https://backend.leadconnectorhq.com/oauth/login", {"email": EMAIL, "password": PASSWORD}),
    ("https://services.leadconnectorhq.com/users/login", {"email": EMAIL, "password": PASSWORD}),
]
for url, body in login_bodies:
    st, b, hdrs = req(None, "POST", url, body, extra={"Source": "WEB_USER", "Channel": "APP", "Origin": "https://app.gohighlevel.com"})
    keys = list(b.keys())[:12] if isinstance(b, dict) else type(b)
    print("LOGIN", url.split(".com")[1], st, keys, str(b)[:250].replace("\n", " "))
