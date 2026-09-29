# -*- coding: utf-8 -*-
import json
import urllib.request

ENV = r"c:\Users\GC1\Desktop\Automação GHL\.env"
key = None
with open(ENV, encoding="utf-8") as f:
    for line in f:
        if line.startswith("GHL_MULTIODONTO_API_KEY="):
            key = line.split("=", 1)[1].strip()
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
UID_CARLOS = "QNUDmXSAzlzngGr04uep"

ids = [
    "G4tcW29iJqqIlinvVyDj",  # Castro 09:00
    "gE1KWHZ2CwGsZXj69k1R",  # Giovanna 09:30
    "6wphbrhqzZhe18GojQH8",  # Giovanna 10:30
    "TXKDMETzJv1exsMBXZVA",  # Giovanna 11:00
    "VUpmtrCdAmt5574oLjNO",  # Giovanna 11:30
]


def req(method, url, body=None):
    data = None if body is None else json.dumps(body).encode("utf-8")
    r = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {key}",
            "Version": "2021-04-15",
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": UA,
        },
    )
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        return {"error": e.code, "body": e.read().decode("utf-8", errors="replace")[:400]}


for aid in ids:
    got = req("GET", f"https://services.leadconnectorhq.com/calendars/events/appointments/{aid}")
    appt = got.get("appointment", got) if isinstance(got, dict) else {}
    print("GET", aid, appt.get("startTime"), appt.get("assignedUserId"), appt.get("title", "")[:40])
    for body in [
        {"assignedUserId": UID_CARLOS, "ignoreDateRange": True, "ignoreFreeSlotAvailability": True},
        {"assignedUserId": UID_CARLOS, "ignoreDateRange": True, "ignoreFreeSlotValidation": True},
        {"assignedUserId": UID_CARLOS},
    ]:
        resp = req("PUT", f"https://services.leadconnectorhq.com/calendars/events/appointments/{aid}", body)
        if resp.get("error"):
            print("  fail", body.keys(), resp.get("error"), resp.get("body", "")[:180])
            continue
        ap = resp.get("appointment", resp)
        print("  OK", ap.get("assignedUserId"), ap.get("startTime"))
        break
