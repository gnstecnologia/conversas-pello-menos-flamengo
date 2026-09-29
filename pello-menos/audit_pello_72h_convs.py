# -*- coding: utf-8 -*-
"""Pello: locations via users + conversas de anúncio + tipo de mensagem (template vs session)."""
import json
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ENV = Path(r"c:\Users\GC1\Desktop\Automação GHL\.env")
OUT = Path(r"c:\Users\GC1\Desktop\Automação GHL\pello-menos")
vals = {}
for line in ENV.read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()

FK = vals["GHL_PELLO_API_KEY"]
FLOC = vals["GHL_PELLO_LOCATION_ID"]
BRT = timezone(timedelta(hours=-3))


def req(key, path, version="2021-07-28", location_id=None):
    headers = {
        "Authorization": f"Bearer {key}",
        "Version": version,
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0",
    }
    if location_id:
        headers["Location-Id"] = location_id
    r = urllib.request.Request("https://services.leadconnectorhq.com" + path, headers=headers)
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode() or "{}")
    except urllib.error.HTTPError as e:
        raw = e.read().decode(errors="replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"_raw": raw[:300]}
    except Exception as ex:
        return 0, {"_err": str(ex)}


print("=== USERS / LOCATIONS ===")
st, users = req(FK, f"/users/?locationId={FLOC}", location_id=FLOC)
print("users", st)
locs = {}
for u in (users.get("users") or []) if isinstance(users, dict) else []:
    for lid in ((u.get("roles") or {}).get("locationIds") or []):
        locs.setdefault(lid, []).append(u.get("name") or u.get("email"))
print("unique locs from users", len(locs))
for lid in sorted(locs):
    st, d = req(FK, f"/locations/{lid}", location_id=lid)
    L = d.get("location") or d if isinstance(d, dict) else {}
    name = L.get("name") if isinstance(L, dict) else "?"
    print(f" {lid} | {name} | users={len(locs[lid])}")


def extract_msgs(payload):
    m = payload.get("messages") or payload.get("data") or []
    if isinstance(m, dict):
        m = m.get("messages") or m.get("data") or []
    return m if isinstance(m, list) else []


print("\n=== RECENT CONVERSATIONS ===")
st, convs = req(
    FK,
    f"/conversations/search?locationId={FLOC}&limit=40&sort=desc&sortBy=last_message_date",
    version="2021-04-15",
    location_id=FLOC,
)
print("search", st)
rows = convs.get("conversations") or [] if isinstance(convs, dict) else []
print("n", len(rows))

ad_like = []
for c in rows:
    last = (c.get("lastMessageBody") or "")[:90]
    name = c.get("contactName") or ""
    print(
        f" {c.get('id')} | {name} | type={c.get('type')} lastType={c.get('lastMessageType')} src={c.get('lastMessageType')} | {last}"
    )

# dump first 12 conversations' first 8 messages with ALL interesting keys
print("\n=== MESSAGE META (first 12 convs) ===")
summary = []
for c in rows[:12]:
    cid = c.get("id")
    st, payload = req(FK, f"/conversations/{cid}/messages?limit=30", version="2021-04-15", location_id=FLOC)
    msgs = extract_msgs(payload)
    msgs = sorted(msgs, key=lambda x: str(x.get("dateAdded") or x.get("timestamp") or ""))
    print(f"\n----- {c.get('contactName')} {cid} n={len(msgs)} -----")
    rec = {"id": cid, "name": c.get("contactName"), "msgs": []}
    for m in msgs[:10]:
        ts = m.get("dateAdded") or ""
        try:
            dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00")).astimezone(BRT)
            tss = dt.strftime("%d/%m %H:%M")
        except Exception:
            tss = str(ts)[:16]
        interesting = {
            k: m.get(k)
            for k in m
            if any(
                x in k.lower()
                for x in (
                    "template",
                    "type",
                    "source",
                    "direction",
                    "channel",
                    "whatsapp",
                    "meta",
                    "content",
                    "status",
                    "alt",
                    "provider",
                    "campaign",
                    "workflow",
                    "ad",
                    "referral",
                    "ctwa",
                    "window",
                    "conversation",
                )
            )
        }
        body = (m.get("body") or "")[:140].replace("\n", " | ")
        direction = m.get("direction")
        print(f" [{tss}] {direction} type={m.get('type')} src={m.get('source')} | {body}")
        extra = {k: v for k, v in interesting.items() if k not in ("type", "source", "direction") and v not in (None, "", [], {})}
        if extra:
            print("   extra", {k: (str(v)[:120]) for k, v in extra.items()})
        rec["msgs"].append({"t": tss, "dir": direction, "type": m.get("type"), "source": m.get("source"), "body": body, "extra": extra})
    summary.append(rec)
    time.sleep(0.15)

(OUT / "pello-72h-msg-sample.json").write_text(json.dumps(summary, ensure_ascii=False, indent=2, default=str), encoding="utf-8")

print("\n=== LOOK FOR AD ATTRIBUTION ON CONTACTS ===")
# sample a few contact ids
seen = 0
for c in rows[:20]:
    cid = c.get("contactId") or c.get("id")
    # conversation search objects often have contactId
    contact_id = c.get("contactId")
    if not contact_id:
        continue
    st, cd = req(FK, f"/contacts/{contact_id}", location_id=FLOC)
    contact = (cd.get("contact") or cd) if isinstance(cd, dict) else {}
    source = contact.get("source")
    attrib = contact.get("attributionSource") or contact.get("lastAttributionSource")
    tags = contact.get("tags")
    custom = contact.get("customField") or contact.get("customFields")
    # print if ad-like
    blob = json.dumps({"source": source, "attrib": attrib, "tags": tags}, ensure_ascii=False)
    flag = ""
    low = blob.lower()
    if any(x in low for x in ("ad", "facebook", "instagram", "fb ", "anun", "ctwa", "whatsapp")):
        flag = " ***AD?***"
    print(f" {contact.get('firstName')} src={source} attrib={str(attrib)[:120]} tags={tags}{flag}")
    seen += 1
print("contacts checked", seen)
