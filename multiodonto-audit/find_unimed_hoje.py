# -*- coding: utf-8 -*-
import json
import sys
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ENV = Path(r"c:\Users\GC1\Desktop\Automação GHL\.env")
key = None
for line in ENV.read_text(encoding="utf-8").splitlines():
    if line.startswith("GHL_MULTIODONTO_API_KEY="):
        key = line.split("=", 1)[1].strip()
LOC = "3R4hY0j3TJyj2SkmSQL3"
BASE = "https://services.leadconnectorhq.com"
BRT = timezone(timedelta(hours=-3))
OUT = Path(r"c:\Users\GC1\Desktop\Automação GHL\multiodonto-audit")
CALS = {
    "Scherres": "fUvShjVjDVERgGZUuNls",
    "Thais": "bOur6KKgSm1cQvIxYnwQ",
    "Castro": "dpnGTRPb4wLTjWxPfO3M",
    "Giovanna": "ACcmwEr9OeexBtiU4yl6",
    "Rafael": "Sq4S1RHRaAoVfLbcb6Gj",
    "Juliana": "1X5AaBX8WCmn4FpAuMxJ",
}


def req(path, ver="2021-07-28"):
    r = urllib.request.Request(
        BASE + path,
        headers={
            "Authorization": f"Bearer {key}",
            "Version": ver,
            "Accept": "application/json",
            "User-Agent": "Mozilla/5.0",
        },
    )
    with urllib.request.urlopen(r, timeout=90) as resp:
        return json.loads(resp.read().decode())


start = int(datetime(2026, 9, 25, 0, 0, tzinfo=BRT).timestamp() * 1000)
end = int(datetime(2026, 9, 26, 0, 0, tzinfo=BRT).timestamp() * 1000)
rows = []
for name, cid in CALS.items():
    ev = req(f"/calendars/events?locationId={LOC}&startTime={start}&endTime={end}&calendarId={cid}")
    for e in ev.get("events") or []:
        stt = e.get("startTime") or ""
        try:
            hm = datetime.fromisoformat(stt.replace("Z", "+00:00")).astimezone(BRT).strftime("%H:%M")
        except Exception:
            hm = stt[:16]
        title = e.get("title") or ""
        notes = (e.get("notes") or "").replace("\n", " ")
        status = e.get("appointmentStatus")
        print(f"{hm} {name:10} {status:12} {title[:55]} | {notes[:90]}")
        cid_contact = e.get("contactId")
        conv = ""
        if cid_contact:
            try:
                c = req(f"/contacts/{cid_contact}")
                contact = c.get("contact") or c
                fields = contact.get("customFields") or []
                bits = []
                for f in fields:
                    val = f.get("value") or f.get("fieldValue") or ""
                    if val and ("unimed" in str(val).lower() or "conv" in str(f.get("id") or "").lower() or len(str(val)) < 40):
                        bits.append(str(val)[:60])
                name_c = ((contact.get("firstName") or "") + " " + (contact.get("lastName") or "")).strip()
                tags = ",".join(contact.get("tags") or [])
                conv = f"{name_c} tags={tags[:80]} fields={bits[:8]}"
            except Exception as ex:
                conv = str(ex)[:80]
        print("   ", conv[:220])
        rows.append(
            {
                "hm": hm,
                "cal": name,
                "status": status,
                "title": title,
                "notes": notes,
                "contactId": cid_contact,
                "id": e.get("id"),
                "dateAdded": e.get("dateAdded"),
                "createdBy": e.get("createdBy") or e.get("source"),
                "contact": conv,
            }
        )

(OUT / "unimed-hoje-events.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")
print("TOTAL", len(rows))
