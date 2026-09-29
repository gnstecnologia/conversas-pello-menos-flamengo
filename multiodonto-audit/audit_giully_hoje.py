# -*- coding: utf-8 -*-
"""Audita conversa Giully + conversas de hoje + slots terça 01/09."""
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ENV = Path(r"c:\Users\GC1\Desktop\Automação GHL\.env")
OUT = Path(r"c:\Users\GC1\Desktop\Automação GHL\multiodonto-audit")
key = None
for line in ENV.read_text(encoding="utf-8").splitlines():
    if line.startswith("GHL_MULTIODONTO_API_KEY="):
        key = line.split("=", 1)[1].strip()
        break
assert key

LOC = "3R4hY0j3TJyj2SkmSQL3"
AGENT = "3Fzfmx7ViwyD9v16h4DR"
ACTION = "zeWiS2QJD0LcF6UOaejG"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
BRT = timezone(timedelta(hours=-3))
BASE = "https://services.leadconnectorhq.com"

CALS = {
    "Scherres": "fUvShjVjDVERgGZUuNls",
    "Castro": "dpnGTRPb4wLTjWxPfO3M",
    "Thais": "bOur6KKgSm1cQvIxYnwQ",
    "Giovanna": "ACcmwEr9OeexBtiU4yl6",
    "Rafael": "Sq4S1RHRaAoVfLbcb6Gj",
}


def req(method, path, body=None, ver="2021-07-28"):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    r = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {key}",
            "Version": ver,
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": UA,
        },
    )
    for i in range(5):
        try:
            with urllib.request.urlopen(r, timeout=90) as resp:
                return resp.status, json.loads(resp.read().decode("utf-8") or "{}")
        except urllib.error.HTTPError as e:
            raw = e.read().decode("utf-8", errors="replace")
            if e.code in (429, 502, 503) and i < 4:
                time.sleep(2 + i * 2)
                continue
            try:
                return e.code, json.loads(raw)
            except Exception:
                return e.code, {"_raw": raw[:2000]}
        except Exception as ex:
            if i < 4:
                time.sleep(1)
                continue
            return 0, {"_err": str(ex)}
    return 0, {"_err": "timeout"}


def extract_msgs(payload):
    m = payload.get("messages") or payload.get("data") or []
    if isinstance(m, dict):
        m = m.get("messages") or m.get("data") or []
    return m if isinstance(m, list) else []


def fmt_msg(m):
    ts = m.get("dateAdded") or m.get("timestamp") or ""
    try:
        dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00")).astimezone(BRT)
        tss = dt.strftime("%d/%m %H:%M")
    except Exception:
        tss = str(ts)[:16]
    direction = m.get("direction") or ""
    src = m.get("source") or m.get("type") or ""
    user = m.get("userId") or m.get("userName") or ""
    body = (m.get("body") or m.get("message") or m.get("text") or "").replace("\n", " | ")
    role = "PAC" if direction == "inbound" else "OUT"
    if m.get("altId") or "bot" in str(src).lower() or m.get("conversationProviderId"):
        pass
    return f"[{tss}] {role} src={src} user={user} | {body[:500]}"


print("=== AGENT LIVE ===")
st, agent = req("GET", f"/conversation-ai/agents/{AGENT}")
print("GET agent", st)
a = agent if "instructions" in agent else (agent.get("data") or agent)
inst = a.get("instructions") or ""
print("name:", a.get("name"), "isPrimary:", a.get("isPrimary"), "mode:", a.get("mode"))
print("instr_len:", len(inst))
print("has MAPA POR DIA:", "MAPA POR DIA" in inst)
print("has Terça Scherres:", "Terça: Dr. Lucas Scherres" in inst)
print("has ANTI-PADRÃO:", "ANTI-PADRÃO" in inst or "ANTI-PADRAO" in inst)

st, act = req("GET", f"/conversation-ai/agents/{AGENT}/actions/{ACTION}")
print("\nGET action", st)
data = act.get("data") or act
details = data.get("details") or {}
print("aiDescription:\n", details.get("aiDescription") or "")
print("updatedAt:", data.get("updatedAt"))
for c in details.get("calendarIds") or []:
    print(" -", c.get("id"), "|", (c.get("triggerCondition") or "")[:160])

print("\n=== SLOTS HOJE 01/09/2026 (terça) ===")
day = datetime(2026, 9, 1, tzinfo=BRT)
s = int(day.timestamp() * 1000)
e = int((day + timedelta(days=1)).timestamp() * 1000)
for name, cid in CALS.items():
    st, sl = req(
        "GET",
        f"/calendars/{cid}/free-slots?startDate={s}&endDate={e}&timezone=America/Sao_Paulo",
    )
    slots = []
    if isinstance(sl, dict):
        # various shapes
        for k, v in sl.items():
            if k in ("slots", "traceId"):
                continue
            if isinstance(v, dict) and "slots" in v:
                slots.extend(v["slots"] if isinstance(v["slots"], list) else [])
            elif isinstance(v, list):
                slots.extend(v)
        if not slots and isinstance(sl.get("slots"), list):
            slots = sl["slots"]
    print(f"{name:10} status={st} n={len(slots)} first={slots[:3]}")

print("\n=== SEARCH Giully / Giuli ===")
found = []
for q in ["Giully", "Giuli", "Giully", "giully"]:
    st, d = req(
        "GET",
        f"/conversations/search?locationId={LOC}&limit=20&query={urllib.parse.quote(q)}",
        ver="2021-04-15",
    )
    convs = (d.get("conversations") or []) if isinstance(d, dict) else []
    print(f"query={q!r} status={st} n={len(convs)}")
    for c in convs:
        found.append(c)
        print(
            " ",
            c.get("id"),
            c.get("contactName") or c.get("fullName"),
            c.get("phone"),
            c.get("lastMessageBody", "")[:80],
        )

print("\n=== CONTACTS SEARCH Giully ===")
for q in ["Giully", "Giuli"]:
    st, d = req("GET", f"/contacts/?locationId={LOC}&query={urllib.parse.quote(q)}&limit=20")
    contacts = (d.get("contacts") or []) if isinstance(d, dict) else []
    print(f"contact q={q!r} status={st} n={len(contacts)}")
    for c in contacts:
        print(" ", c.get("id"), c.get("firstName"), c.get("lastName"), c.get("phone"), c.get("email"))
        cid = c.get("id")
        st2, sr = req(
            "GET",
            f"/conversations/search?locationId={LOC}&contactId={cid}&limit=5",
            ver="2021-04-15",
        )
        for conv in (sr.get("conversations") or []) if isinstance(sr, dict) else []:
            found.append(conv)
            print("   conv", conv.get("id"), (conv.get("lastMessageBody") or "")[:80])

print("\n=== CONVERSAS RECENTES (hoje) ===")
st, d = req(
    "GET",
    f"/conversations/search?locationId={LOC}&limit=50&sort=desc&sortBy=last_message_date",
    ver="2021-04-15",
)
convs = d.get("conversations") or [] if isinstance(d, dict) else []
print("recent n", len(convs), "status", st)
today_convs = []
for c in convs:
    ts = c.get("lastMessageDate") or c.get("dateUpdated") or 0
    try:
        if isinstance(ts, (int, float)):
            dt = datetime.fromtimestamp(ts / 1000 if ts > 1e12 else ts, tz=BRT)
        else:
            dt = datetime.fromisoformat(str(ts).replace("Z", "+00:00")).astimezone(BRT)
    except Exception:
        dt = None
    name = c.get("contactName") or c.get("fullName") or ""
    last = (c.get("lastMessageBody") or "")[:100]
    is_today = dt and dt.date() == datetime(2026, 9, 1, tzinfo=BRT).date()
    flag = "HOJE" if is_today else ""
    print(f" {flag} {dt} | {name} | {c.get('id')} | {last}")
    if is_today or "giul" in name.lower() or "thais" in last.lower() or "castro" in last.lower():
        today_convs.append(c)
        found.append(c)

# unique convs
seen = set()
uniq = []
for c in found + today_convs:
    cid = c.get("id")
    if cid and cid not in seen:
        seen.add(cid)
        uniq.append(c)

print(f"\n=== DUMP {len(uniq)} CONVERSAS ===")
dump = []
for c in uniq:
    cid = c.get("id")
    st, payload = req("GET", f"/conversations/{cid}/messages?limit=100", ver="2021-04-15")
    msgs = extract_msgs(payload)
    print(f"\n----- {c.get('contactName') or c.get('fullName')} {cid} msgs={len(msgs)} st={st} -----")
    lines = []
    for m in msgs:
        line = fmt_msg(m)
        lines.append(line)
        print(line)
    dump.append({"meta": c, "messages": msgs, "text": "\n".join(lines)})

(OUT / "audit-giully-hoje.json").write_text(
    json.dumps(dump, ensure_ascii=False, indent=2, default=str), encoding="utf-8"
)
print("\nWrote audit-giully-hoje.json")
