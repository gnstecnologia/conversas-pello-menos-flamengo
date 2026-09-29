#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import json, subprocess
from pathlib import Path

TOKEN = "pit-7f81ae98-ee67-4025-a4d6-1c4f8b5bcef7"
LOC = "MhplIQf1baCvRBNGPTOj"
AGENT = "nEndeX5NE4uDJG7414RF"
OUT = Path(r"c:\Users\GC1\Desktop\Automação GHL\gamma-vet\audit")
OUT.mkdir(parents=True, exist_ok=True)


def curl(method, url, data=None):
    cmd = [
        "curl.exe", "-s", "-w", "\nHTTP:%{http_code}", "-X", method, url,
        "-H", f"Authorization: Bearer {TOKEN}",
        "-H", "Version: 2021-07-28",
        "-H", "Accept: application/json",
        "-H", "User-Agent: Mozilla/5.0",
    ]
    if data is not None:
        tmp = OUT / "req.json"
        tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        cmd += ["-H", "Content-Type: application/json", "--data-binary", f"@{tmp}"]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    body = r.stdout
    code = "?"
    if "HTTP:" in body:
        body, code = body.rsplit("HTTP:", 1)
        code = code.strip()
    return code, body


# list actions
for p in [
    f"/conversation-ai/actions?agentId={AGENT}",
    f"/conversation-ai/actions?locationId={LOC}&agentId={AGENT}",
    f"/conversation-ai/agents/{AGENT}/action",
]:
    code, body = curl("GET", f"https://services.leadconnectorhq.com{p}")
    print("GET", p, code, body[:250].replace("\n", " "))

code, body = curl("GET", "https://services.leadconnectorhq.com/conversation-ai/actions/KM2hdh1Sm6u83AyDGaCy")
print("GET booking", code)
(OUT / "booking-action.json").write_text(body, encoding="utf-8")
print(body[:3000])

# tags
code, body = curl("GET", f"https://services.leadconnectorhq.com/locations/{LOC}/tags")
tags = json.loads(body).get("tags") or []
print("TAGS", len(tags))
for t in tags:
    print("-", t.get("id"), t.get("name"))

# custom fields full
code, body = curl("GET", f"https://services.leadconnectorhq.com/locations/{LOC}/customFields")
fields = json.loads(body).get("customFields") or []
print("FIELDS", len(fields))
for f in fields:
    print("-", f.get("id"), "|", f.get("name"), "|", f.get("dataType"), "|", f.get("fieldKey"))

# calendars summary with open hours if present
code, body = curl("GET", f"https://services.leadconnectorhq.com/calendars/?locationId={LOC}")
cals = json.loads(body).get("calendars") or []
for c in cals:
    cid = c["id"]
    code2, body2 = curl("GET", f"https://services.leadconnectorhq.com/calendars/{cid}")
    full = json.loads(body2).get("calendar", json.loads(body2))
    (OUT / f"cal-{cid}.json").write_text(json.dumps(full, ensure_ascii=False, indent=2), encoding="utf-8")
    oh = full.get("openHours") or full.get("availability") or full.get("schedules")
    print(
        "CAL",
        full.get("name"),
        "dur",
        full.get("slotDuration"),
        "type",
        full.get("calendarType"),
        "autoConfirm",
        full.get("autoConfirm"),
        "keys_oh",
        list(full.keys())[:25],
    )
