# -*- coding: utf-8 -*-
import json
import urllib.request

ENV = r"c:\Users\GC1\Desktop\Automação GHL\.env"
vals = {}
with open(ENV, encoding="utf-8") as f:
    for line in f:
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            vals[k.strip()] = v.strip()

KEY_AGENCY = "pit-704ae0dc-73da-4521-af39-8dad17ebd02d"
LOC_BIO = vals["GHL_BIO_LOCATION_ID"]
LOC_NEW = vals["GHL_NEW_DIGITAL_LOCATION_ID"]
COMPANY = "PIK3OmRl8Y7U0cy1tHSR"
UA = "Mozilla/5.0"


def req(key, method, url, body=None):
    data = None if body is None else json.dumps(body).encode("utf-8")
    r = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {key}",
            "Version": "2021-07-28",
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": UA,
        },
    )
    with urllib.request.urlopen(r, timeout=90) as resp:
        return json.loads(resp.read().decode("utf-8"))


ids = {
    "Luise": "ZAREnnN68tZOANwLFb23",
    "Magno": "2XSoZGstcaEJUe8SUVGj",
    "Alex": "gSOWshyA5S1OOxVGneUx",
}

for name, uid in ids.items():
    u = req(KEY_AGENCY, "GET", f"https://services.leadconnectorhq.com/users/{uid}")
    perms = dict(u.get("permissions") or {})
    for k, v in list(perms.items()):
        if not isinstance(v, bool):
            continue
        if "readonly" in k.lower() or k == "assignedDataOnly":
            perms[k] = False
        else:
            perms[k] = True
    perms["appointmentsEnabled"] = True
    perms["marketingEnabled"] = True
    perms["settingsEnabled"] = True
    body = {
        "companyId": COMPANY,
        "firstName": u.get("firstName"),
        "lastName": u.get("lastName") or "",
        "email": u.get("email"),
        "type": "account",
        "role": "admin",
        "locationIds": [LOC_BIO, LOC_NEW],
        "permissions": perms,
    }
    out = req(KEY_AGENCY, "PUT", f"https://services.leadconnectorhq.com/users/{uid}", body)
    user = out.get("user", out)
    offs = [k for k, v in (user.get("permissions") or {}).items() if v is False]
    print(name, "role", user.get("roles", {}).get("role"), "locs", user.get("roles", {}).get("locationIds"))
    print("  OFF", offs)
    print("  appt", user.get("permissions", {}).get("appointmentsEnabled"), "mkt", user.get("permissions", {}).get("marketingEnabled"), "settings", user.get("permissions", {}).get("settingsEnabled"))
