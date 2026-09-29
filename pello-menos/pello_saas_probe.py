# -*- coding: utf-8 -*-
"""Probe SaaS mode + billing on Pello MODELO / Franqueadora / Franchising."""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
ENV = Path(r"c:\Users\GC1\Desktop\Automação GHL\.env")
OUT = Path(r"c:\Users\GC1\Desktop\Automação GHL\pello-menos")
vals = {}
for line in ENV.read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()

AGENCY = vals["GHL_AGENCY_API_KEY"]
COMPANY = vals["GHL_AGENCY_COMPANY_ID"]
LOCS = {
    "MODELO": vals["GHL_PELLO_MODELO_LOCATION_ID"],
    "FRANQ": vals["GHL_PELLO_FRANQ_LOCATION_ID"],
    "FRANCH": vals["GHL_PELLO_LOCATION_ID"],
    "URG": vals["GHL_PELLO_URG_LOCATION_ID"],
}


def req(url, key=AGENCY, ver="2021-07-28"):
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
        with urllib.request.urlopen(r, timeout=45) as resp:
            return resp.status, json.loads(resp.read().decode("utf-8") or "{}")
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = raw
        return e.code, parsed


def pick(d, keys):
    if not isinstance(d, dict):
        return d
    return {k: d.get(k) for k in keys if k in d or True}


print("=== COMPANY ===")
st, data = req(f"https://services.leadconnectorhq.com/companies/{COMPANY}")
print("GET company", st)
co = data.get("company") or data if isinstance(data, dict) else {}
if isinstance(co, dict):
    interesting = [
        "id", "name", "email", "customerType", "plan", "isReselling",
        "upgradeEnabledForClients", "cancelEnabledForClients", "autoSuspendEnabled",
        "saasSettings", "stripeConnectId", "locationCount", "status", "premiumUpgraded",
        "isEnterpriseAccount",
    ]
    slim = {k: co.get(k) for k in interesting}
    print(json.dumps(slim, ensure_ascii=False, indent=2)[:2500])
    (OUT / "agency-company.json").write_text(json.dumps(co, ensure_ascii=False, indent=2), encoding="utf-8")

print("\n=== LOCATIONS SEARCH (pello) ===")
st, data = req("https://services.leadconnectorhq.com/locations/search?limit=100")
print("search", st)
locs = (data.get("locations") if isinstance(data, dict) else []) or []
print("count", len(locs))
for x in locs:
    n = (x.get("name") or "")
    if "pello" in n.lower() or "modelo" in n.lower() or "franq" in n.lower():
        print(" ", x.get("id"), n, "saas", x.get("saasSettings") or x.get("settings", {}).get("saasSettings") if isinstance(x.get("settings"), dict) else None)

print("\n=== PER LOCATION ===")
for label, lid in LOCS.items():
    print(f"\n--- {label} {lid} ---")
    st, data = req(f"https://services.leadconnectorhq.com/locations/{lid}")
    print("location", st)
    L = data.get("location") or data if isinstance(data, dict) else {}
    if isinstance(L, dict):
        print(" name", L.get("name"))
        print(" saasSettings", json.dumps(L.get("saasSettings"), ensure_ascii=False)[:800])
        settings = L.get("settings") or {}
        if isinstance(settings, dict) and settings.get("saasSettings"):
            print(" settings.saas", json.dumps(settings.get("saasSettings"), ensure_ascii=False)[:500])
        extra = {k: L.get(k) for k in L if "saas" in k.lower() or "stripe" in k.lower() or "bill" in k.lower() or "wallet" in k.lower()}
        print(" extra keys", extra)
    for path, ver in [
        (f"/saas/get-saas-subscription/{lid}?companyId={COMPANY}", "2021-04-15"),
        (f"/saas-api/public-api/get-saas-subscription/{lid}?companyId={COMPANY}", "2021-04-15"),
        (f"/saas/location/{lid}", "2021-04-15"),
        (f"/saas/locations/{lid}", "2021-07-28"),
        (f"/saas/company/{COMPANY}", "2021-04-15"),
    ]:
        st2, d2 = req("https://services.leadconnectorhq.com" + path, ver=ver)
        snippet = json.dumps(d2, ensure_ascii=False)[:350] if not isinstance(d2, str) else d2[:350]
        print(f"  {path.split('?')[0]} {st2} {snippet.replace(chr(10),' ')}")

print("\n=== SAAS PLANS / COMPANY ===")
for path, ver in [
    (f"/saas/plans?companyId={COMPANY}", "2021-04-15"),
    (f"/saas/company/{COMPANY}/plans", "2021-04-15"),
    (f"/saas-api/public-api/plans?companyId={COMPANY}", "2021-04-15"),
    (f"/saas/locations?companyId={COMPANY}", "2021-04-15"),
    (f"/snapshots?companyId={COMPANY}", "2021-04-15"),
]:
    st, d = req("https://services.leadconnectorhq.com" + path, ver=ver)
    snippet = json.dumps(d, ensure_ascii=False)[:400] if not isinstance(d, str) else d[:400]
    print(path, st, snippet.replace("\n", " "))
