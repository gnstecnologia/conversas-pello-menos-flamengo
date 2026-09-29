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

KEY_BIO = vals["GHL_BIO_API_KEY"]
KEY_NEW = vals["GHL_NEW_DIGITAL_API_KEY"]
KEY_AGENCY = "pit-704ae0dc-73da-4521-af39-8dad17ebd02d"
LOC_BIO = vals["GHL_BIO_LOCATION_ID"]
LOC_NEW = vals["GHL_NEW_DIGITAL_LOCATION_ID"]
COMPANY = "PIK3OmRl8Y7U0cy1tHSR"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"

TARGETS = {
    "luise": "luisemecompany@gmail.com",
    "magno": "magnosandes.ms@gmail.com",
    "alex": "alexgruponew@gmail.com",
}


def req(key, method, url, body=None):
    data = None if body is None else json.dumps(body).encode("utf-8")
    last = None
    for attempt in range(4):
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
        try:
            with urllib.request.urlopen(r, timeout=90) as resp:
                raw = resp.read().decode("utf-8")
                return json.loads(raw) if raw else {}
        except urllib.error.HTTPError as e:
            err = e.read().decode("utf-8", errors="replace")
            last = RuntimeError(f"{method} {url} {e.code} {err[:800]}")
            if "timed out" in err.lower() or e.code in (429, 502, 503, 504):
                continue
            raise last
    raise last


def list_users(key, loc):
    return req(key, "GET", f"https://services.leadconnectorhq.com/users/?locationId={loc}").get("users") or []


def get_user(key, uid):
    return req(key, "GET", f"https://services.leadconnectorhq.com/users/{uid}")


def full_permissions(existing):
    perms = dict(existing or {})
    for k, v in list(perms.items()):
        if not isinstance(v, bool):
            continue
        name = k.lower()
        if "readonly" in name or name == "assigneddataonly":
            perms[k] = False
        else:
            perms[k] = True
    return perms


bio_users = list_users(KEY_BIO, LOC_BIO)
new_users = list_users(KEY_NEW, LOC_NEW)

print("=== BIO ===")
for u in bio_users:
    print(u.get("id"), u.get("email"), u.get("name"), u.get("roles", {}).get("role"))
print("=== NEW DIGITAL ===")
for u in new_users:
    print(u.get("id"), u.get("email"), u.get("name"), u.get("roles", {}).get("role"))

by_email = {}
for u in bio_users + new_users:
    em = (u.get("email") or "").lower()
    by_email.setdefault(em, u)

found = {}
for label, em in TARGETS.items():
    u = by_email.get(em.lower())
    if not u:
        print("MISSING", label, em)
    else:
        found[label] = u
        print("FOUND", label, u.get("id"), u.get("email"))

if len(found) != 3:
    raise SystemExit("Nao achei os 3 usuarios")

def put_user(key, uid, cur, location_ids, perms):
    body = {
        "companyId": COMPANY,
        "firstName": cur.get("firstName") or "",
        "lastName": cur.get("lastName") or "",
        "email": cur.get("email"),
        "type": "account",
        "role": "admin",
        "locationIds": location_ids,
        "permissions": perms,
    }
    return req(key, "PUT", f"https://services.leadconnectorhq.com/users/{uid}", body)


for label, u in found.items():
    uid = u["id"]
    locs = list(u.get("roles", {}).get("locationIds") or [])
    key = KEY_NEW if LOC_NEW in locs else KEY_BIO
    cur = get_user(key, uid)
    perms = full_permissions(cur.get("permissions") or u.get("permissions"))
    current_locs = list((cur.get("roles") or {}).get("locationIds") or locs)

    print(f"\n=== PUT admin+full {label} {uid} locs={current_locs} ===")
    user = None
    try:
        # location PIT so aceita as locations que o token enxerga
        loc_for_token = [x for x in current_locs if (key == KEY_NEW and x == LOC_NEW) or (key == KEY_BIO and x == LOC_BIO)]
        if not loc_for_token:
            loc_for_token = [LOC_NEW if key == KEY_NEW else LOC_BIO]
        out = put_user(key, uid, cur, loc_for_token, perms)
        user = out.get("user", out)
        print("loc PUT role", (user.get("roles") or {}).get("role"), "locs", (user.get("roles") or {}).get("locationIds"))
    except RuntimeError as e:
        print("loc PUT skip", str(e)[:200])
        user = cur

    both = [LOC_BIO, LOC_NEW]
    have = set((user.get("roles") or {}).get("locationIds") or current_locs)
    print("tentando agency admin nas duas contas")
    try:
        out2 = put_user(KEY_AGENCY, uid, user if user.get("email") else cur, both, perms)
        user = out2.get("user", out2)
        print("agency OK role", (user.get("roles") or {}).get("role"), "locs", (user.get("roles") or {}).get("locationIds"))
    except RuntimeError as e:
        print("agency FAIL", str(e)[:400])

    offs = [k for k, v in (user.get("permissions") or {}).items() if v is False]
    ons = [k for k, v in (user.get("permissions") or {}).items() if v is True]
    print("ON count", len(ons), "OFF", offs)

print("\n=== CONFERE LISTAS ===")
for loc_name, key, loc in [("BIO", KEY_BIO, LOC_BIO), ("NEW", KEY_NEW, LOC_NEW)]:
    users = list_users(key, loc)
    print(loc_name)
    for u in users:
        em = (u.get("email") or "").lower()
        if em in TARGETS.values():
            print(" ", u.get("name"), u.get("roles", {}).get("role"), u.get("id"))
