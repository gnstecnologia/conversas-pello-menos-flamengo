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

NEW = "pit-99664f1b-3ac9-4d3b-8499-ef28287b656b"
AGENCY = vals.get("GHL_AGENCY_API_KEY")
COMPANY = vals.get("GHL_AGENCY_COMPANY_ID", "PIK3OmRl8Y7U0cy1tHSR")
MODELO_KEY = vals["GHL_PELLO_MODELO_API_KEY"]
MODELO_LOC = vals["GHL_PELLO_MODELO_LOCATION_ID"]


def req(key, url, ver="2021-07-28"):
    r = urllib.request.Request(
        url,
        headers={
            "Authorization": f"Bearer {key}",
            "Version": ver,
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
        },
    )
    try:
        with urllib.request.urlopen(r, timeout=40) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw


def loc_from_token(key):
    st, data = req(key, "https://services.leadconnectorhq.com/conversation-ai/agents/search?limit=20", "2021-04-15")
    agents = (data or {}).get("agents") or [] if isinstance(data, dict) else []
    lids = {a.get("locationId") for a in agents if a.get("locationId")}
    if lids:
        return list(lids)
    st, data = req(key, "https://services.leadconnectorhq.com/locations/search?limit=20")
    locs = (data or {}).get("locations") or [] if isinstance(data, dict) else []
    return [x.get("id") for x in locs if x.get("id")]


print("=== NEW FRANQ TOKEN ===")
lids = loc_from_token(NEW)
print("lids", lids)
if not lids and AGENCY:
    st, data = req(AGENCY, "https://services.leadconnectorhq.com/locations/search?limit=100")
    locs = (data or {}).get("locations") or [] if isinstance(data, dict) else []
    print("agency loc count", len(locs))
    for x in locs:
        print(" ", x.get("id"), x.get("name"))

# try GET locations with new token against known pello ids + agency list
known = [MODELO_LOC, vals.get("GHL_PELLO_FRANQ_LOCATION_ID"), vals.get("GHL_PELLO_LOCATION_ID")]
if AGENCY:
    st, data = req(AGENCY, "https://services.leadconnectorhq.com/locations/search?limit=100")
    locs = (data or {}).get("locations") or [] if isinstance(data, dict) else []
    for x in locs:
        known.append(x.get("id"))

seen = set()
hits = []
for lid in known:
    if not lid or lid in seen:
        continue
    seen.add(lid)
    st, data = req(NEW, f"https://services.leadconnectorhq.com/locations/{lid}")
    if st == 200:
        L = data.get("location") or data
        hits.append((lid, L.get("name") if isinstance(L, dict) else L))
        print("HIT", lid, L.get("name") if isinstance(L, dict) else "")

print("hits", hits)


def dump(label, key, lid):
    print(f"\n==== {label} {lid} ====")
    st, data = req(key, f"https://services.leadconnectorhq.com/locations/{lid}")
    L = data.get("location") or data if isinstance(data, dict) else {}
    print("name", L.get("name") if isinstance(L, dict) else data)
    settings = (L.get("settings") or {}) if isinstance(L, dict) else {}
    print("saas settings", json.dumps(settings.get("saasSettings"), ensure_ascii=False)[:700])
    st, data = req(
        AGENCY or key,
        f"https://services.leadconnectorhq.com/saas/get-saas-subscription/{lid}?companyId={COMPANY}",
        "2021-04-15",
    )
    print("saas sub", st, json.dumps(data.get("data") if isinstance(data, dict) else data, ensure_ascii=False)[:500])
    # whatsapp / integrations
    for path, ver in [
        (f"/whatsapp/businesses?locationId={lid}", "2021-07-28"),
        (f"/conversations/providers?locationId={lid}", "2021-04-15"),
        (f"/location/{lid}/billing", "2021-07-28"),
        (f"/saas/location/{lid}/rebilling", "2021-04-15"),
    ]:
        st, d = req(key, "https://services.leadconnectorhq.com" + path, ver)
        print(path, st, str(d)[:180].replace("\n", " "))


if hits:
    dump("NEW", NEW, hits[0][0])
dump("MODELO", MODELO_KEY, MODELO_LOC)
