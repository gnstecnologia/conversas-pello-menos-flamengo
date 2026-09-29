# -*- coding: utf-8 -*-
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
vals = {}
for line in Path(r"c:\Users\GC1\Desktop\Automação GHL\.env").read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()

KEY = vals["GHL_PELLO_API_KEY"]
AGENCY = vals.get("GHL_AGENCY_API_KEY") or KEY
LOC = vals["GHL_PELLO_LOCATION_ID"]
COMPANY = vals.get("GHL_AGENCY_COMPANY_ID") or "PIK3OmRl8Y7U0cy1tHSR"
BASE = "https://services.leadconnectorhq.com"


def req(token, method, path, body=None, ver="2021-07-28"):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    headers = {
        "Authorization": "Bearer " + token,
        "Version": ver,
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0",
        "Location-Id": LOC,
    }
    if body is not None:
        headers["Content-Type"] = "application/json; charset=utf-8"
    r = urllib.request.Request(BASE + path, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(r, timeout=40) as resp:
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"raw": raw[:300]}


paths = [
    (KEY, "GET", "/locations/" + LOC, None, "2021-07-28"),
    (AGENCY, "GET", "/saas/get-saas-subscription/" + LOC + "?companyId=" + COMPANY, None, "2021-04-15"),
    (AGENCY, "GET", "/saas/location/" + LOC, None, "2021-04-15"),
    (AGENCY, "GET", "/locations/" + LOC + "/rebilling", None, "2021-07-28"),
    (KEY, "GET", "/locations/" + LOC + "/rebilling", None, "2021-07-28"),
    (AGENCY, "GET", "/wallet/" + COMPANY, None, "2021-04-15"),
    (AGENCY, "GET", "/billing/wallet?companyId=" + COMPANY, None, "2021-04-15"),
    (AGENCY, "GET", "/saas/company/" + COMPANY, None, "2021-04-15"),
    (KEY, "GET", "/emails/statistics?locationId=" + LOC, None, "2021-07-28"),
    (KEY, "GET", "/conversations/messages/export?locationId=" + LOC, None, "2021-04-15"),
    (AGENCY, "GET", "/phone-system/numbers?locationId=" + LOC, None, "2021-04-15"),
    (KEY, "GET", "/phone-system/numbers?locationId=" + LOC, None, "2021-04-15"),
    (AGENCY, "GET", "/twilio/account?locationId=" + LOC, None, "2021-04-15"),
    (KEY, "GET", "/campaigns/?locationId=" + LOC, None, "2021-07-28"),
]
for token, method, path, body, ver in paths:
    who = "LOC" if token == KEY else "AGY"
    st, d = req(token, method, path, body, ver)
    snippet = json.dumps(d, ensure_ascii=False)[:350] if isinstance(d, dict) else str(d)[:350]
    print(who, method, path[:70], st, snippet.replace("\n", " "))
    print()
