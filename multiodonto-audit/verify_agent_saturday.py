# -*- coding: utf-8 -*-
import json
import urllib.request
from datetime import datetime, timedelta, timezone

key = None
for line in open(r"c:\Users\GC1\Desktop\Automação GHL\.env", encoding="utf-8"):
    if line.startswith("GHL_MULTIODONTO_API_KEY="):
        key = line.split("=", 1)[1].strip()

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
AGENT = "3Fzfmx7ViwyD9v16h4DR"
ACTION = "zeWiS2QJD0LcF6UOaejG"
NAMES = {
    "fUvShjVjDVERgGZUuNls": "Scherres CG",
    "dpnGTRPb4wLTjWxPfO3M": "Castro CG",
    "ACcmwEr9OeexBtiU4yl6": "Giovanna CG",
    "bOur6KKgSm1cQvIxYnwQ": "Thais CG",
    "Sq4S1RHRaAoVfLbcb6Gj": "Rafael CG",
    "1X5AaBX8WCmn4FpAuMxJ": "Juliana Barra",
}


def req(method, url, body=None, version="2021-07-28"):
    data = None if body is None else json.dumps(body).encode("utf-8")
    r = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {key}",
            "Version": version,
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": UA,
        },
    )
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        print("ERR", method, url, e.code, err[:400])
        return None


a = req("GET", f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}")
print("=== AGENTE ===")
print("nome:", a.get("name"), "primary:", a.get("isPrimary"), "mode:", a.get("mode"))
inst = a.get("instructions") or ""
for needle in ["sábado", "sabado", "Campo Grande", "Scherres", "Castro", "Giovanna"]:
    print(f"prompt tem '{needle}':", needle.lower() in inst.lower() or needle in inst)

act = req("GET", f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}/actions/{ACTION}")
data = (act or {}).get("data") or act or {}
details = data.get("details") or {}
cals = details.get("calendarIds") or []
print("\n=== BOOKING ACTION ===")
print("ids:")
for c in cals:
    cid = c.get("id") if isinstance(c, dict) else c
    print(" -", NAMES.get(cid, cid), cid)

tz = timezone(timedelta(hours=-3))
print("\n=== O QUE A ACTION VERIA (free-slots) ===")
sat_ids = [
    ("Scherres", "fUvShjVjDVERgGZUuNls"),
    ("Castro", "dpnGTRPb4wLTjWxPfO3M"),
    ("Giovanna", "ACcmwEr9OeexBtiU4yl6"),
]
for day_s in ["2026-08-22", "2026-08-29"]:
    start = datetime.fromisoformat(f"{day_s}T00:00:00").replace(tzinfo=tz)
    s = int(start.timestamp() * 1000)
    e = int((start + timedelta(days=1)).timestamp() * 1000)
    print(day_s)
    for name, cid in sat_ids:
        sl = req(
            "GET",
            f"https://services.leadconnectorhq.com/calendars/{cid}/free-slots?startDate={s}&endDate={e}",
        )
        slots = ((sl or {}).get(day_s) or {}).get("slots") or []
        print(f"  {name}: {len(slots)}", [x[11:16] for x in slots])

# try test/chat endpoints
print("\n=== TENTATIVA TESTE AGENTE ===")
for url in [
    f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}/test",
    f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}/chat",
    f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}/preview",
    f"https://services.leadconnectorhq.com/conversation-ai/test",
]:
    for method, body in [
        ("POST", {"message": "Quero agendar sabado em Campo Grande clinico geral Amil", "locationId": "3R4hY0j3TJyj2SkmSQL3"}),
        ("GET", None),
    ]:
        r = req(method, url, body)
        if r is not None:
            print(method, url, json.dumps(r, ensure_ascii=False)[:300])
