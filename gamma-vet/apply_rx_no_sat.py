# -*- coding: utf-8 -*-
"""Fecha sábado do Raio-X; US Fernanda continua intercalado. Agente permanece mode=off."""
import json
import subprocess
import urllib.request
import urllib.error
from datetime import date, datetime, timedelta, timezone
from pathlib import Path

OUT = Path(r"c:\Users\GC1\Desktop\Automação GHL\gamma-vet")
ENV = Path(r"c:\Users\GC1\Desktop\Automação GHL\.env")
vals = {}
for line in ENV.read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()

KEY = vals["GHL_GAMMA_API_KEY"]
LOC = vals["GHL_GAMMA_LOCATION_ID"]
AGENT = vals["GHL_GAMMA_AGENT_ID"]
KB = vals["GHL_GAMMA_KB_ID"]
BOOKING = "g4K4spRJdKq1zpMr2LLb"
CAL = json.loads((OUT / "calendar-ids-live.json").read_text(encoding="utf-8"))
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
TZ = timezone(timedelta(hours=-3))
UID = CAL["sharedUserFernanda"]


def req(method, url, body=None, version="2021-04-15"):
    data = None if body is None else json.dumps(body).encode("utf-8")
    r = urllib.request.Request(
        url,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {KEY}",
            "Version": version,
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": UA,
        },
    )
    try:
        with urllib.request.urlopen(r, timeout=90) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(err)
        except Exception:
            parsed = err
        return e.code, parsed


def hours(days, oh, om, ch, cm):
    return [
        {
            "daysOfTheWeek": [d],
            "hours": [{"openHour": oh, "openMinute": om, "closeHour": ch, "closeMinute": cm}],
        }
        for d in days
    ]


def tm():
    return [
        {
            "priority": 0.5,
            "selected": True,
            "userId": UID,
            "isPrimary": True,
            "isZoomAdded": "false",
            "locationConfigurations": [
                {"kind": "custom", "location": "", "position": 0, "zoomOauthId": "", "meetingId": "custom_0"}
            ],
        }
    ]


def slot_count(cid, day_s):
    start = datetime.fromisoformat(f"{day_s}T00:00:00").replace(tzinfo=TZ)
    s = int(start.timestamp() * 1000)
    e = int((start + timedelta(days=1)).timestamp() * 1000)
    code, sl = req(
        "GET",
        f"https://services.leadconnectorhq.com/calendars/{cid}/free-slots?startDate={s}&endDate={e}",
        version="2021-07-28",
    )
    n = 0
    if isinstance(sl, dict):
        n = len((sl.get(day_s) or {}).get("slots") or [])
    return n


print("=== PUT Raio-X sem sábado ===")
code, body = req(
    "PUT",
    f"https://services.leadconnectorhq.com/calendars/{CAL['rx']}",
    {
        "openHours": hours([1, 2, 3, 4, 5], 8, 30, 18, 0),
        "slotDuration": 30,
        "slotDurationUnit": "mins",
        "slotInterval": 30,
        "slotIntervalUnit": "mins",
        "teamMembers": tm(),
        "isActive": True,
        "description": (
            "Raio-X / radiografia (tórax, abdômen e demais). Seg-sex 8:30-18:00. "
            "NÃO realizar no sábado."
        ),
    },
)
cal = body.get("calendar", body) if isinstance(body, dict) else {}
print(
    code,
    "days",
    [x.get("daysOfTheWeek") for x in (cal.get("openHours") or [])],
    "user",
    [m.get("userId") for m in (cal.get("teamMembers") or [])],
)

print("\n=== SLOTS ===")
print("data       Fernanda       RX")
for d in [date(2026, 8, 21), date(2026, 8, 22), date(2026, 8, 29), date(2026, 9, 5)]:
    print(d.isoformat(), slot_count(CAL["fernanda"], d.isoformat()), slot_count(CAL["rx"], d.isoformat()))

# prompt + booking + FAQ; agente permanece off
md = (OUT / "Procedimentos_GammaVet_KB.md").read_text(encoding="utf-8")
(OUT / "Procedimentos_GammaVet_KB.txt").write_text(md, encoding="utf-8")
instructions = (OUT / "system-prompt-completo.md").read_text(encoding="utf-8")

print("\n=== agent (mode off, sem WhatsApp) ===")
code, cur = req("GET", f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}", version="2021-07-28")
agent = cur.get("agent", cur) if isinstance(cur, dict) else {}
code, body = req(
    "PUT",
    f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}",
    {
        "name": agent.get("name") or "Assistente Gamma Vet",
        "isPrimary": True,
        "mode": "off",
        "channels": ["WebChat"],
        "instructions": instructions,
        "goal": agent.get("goal") or "",
        "personality": agent.get("personality") or "",
        "knowledgeBaseIds": agent.get("knowledgeBaseIds") or [KB],
        "autoPilotMaxMessages": agent.get("autoPilotMaxMessages") or 100,
        "sleepEnabled": agent.get("sleepEnabled", False),
        "sleepOnManualMessage": agent.get("sleepOnManualMessage", True),
        "sleepOnWorkflowMessage": agent.get("sleepOnWorkflowMessage", False),
    },
    version="2021-07-28",
)
print("PUT", code, body.get("message") if isinstance(body, dict) else "ok")
code, after = req("GET", f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}", version="2021-07-28")
after = after.get("agent", after) if isinstance(after, dict) else {}
print("mode", after.get("mode"), "channels", after.get("channels"), "primary", after.get("isPrimary"))
(OUT / "agent-live-now.json").write_text(json.dumps(after, ensure_ascii=False, indent=2), encoding="utf-8")

print("\n=== booking ===")
code, raw = req(
    "GET",
    f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}/actions/{BOOKING}",
)
action = raw.get("data", raw) if isinstance(raw, dict) else {}
details = dict(action.get("details") or {})
cals = list(details.get("calendarIds") or [])
for c in cals:
    cid = c.get("id")
    if cid == CAL["fernanda"]:
        c["triggerCondition"] = (
            "Ultrassonografia abdominal e cervical (e US em geral) com Dra. Fernanda. "
            "Seg/ter/qua/sex. NÃO quinta. "
            "Sábados intercalados (22/08/2026 aberto, 29/08 fechado) — US abdominal e cervical LIVRES nesses sábados abertos. "
            "Só oferecer sábado se a ferramenta devolver slot."
        )
    elif cid == CAL["rx"]:
        c["triggerCondition"] = (
            "Raio-X / radiografia / RX tórax / RX abdômen / uretrografia / urografia. "
            "SOMENTE segunda a sexta. NÃO oferecer sábado."
        )
details["calendarIds"] = cals
details["aiDescription"] = (
    "Agenda exames do Gamma Vet no calendário correto. "
    "US abdominal/cervical: Dra. Fernanda seg/ter/qua/sex e sábados intercalados (22/08 aberto, 29/08 fechado). NUNCA quinta. "
    "Quinta de US = Dra. Luciana. "
    "Raio-X (tórax, abdômen e demais): NÃO sábado, só seg–sex. "
    "Cintilografia só segunda e quinta. Radioiodo só depois da cintilo. "
    "Só oferecer horários reais da ferramenta."
)
code, body = req(
    "PUT",
    f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}/actions/{BOOKING}",
    {"type": "appointmentBooking", "name": "Agendamento Gamma Vet", "details": details},
)
print("booking", code, body.get("message") if isinstance(body, dict) else "ok")

print("\n=== FAQ ===")
code, data = req(
    "GET",
    f"https://services.leadconnectorhq.com/knowledge-base/faqs?locationId={LOC}&knowledgeBaseId={KB}&limit=100",
    version="2021-07-28",
)
faqs = (data or {}).get("faqs") or []
rx_answer = (
    "Raio-X (tórax, abdômen e demais regiões) é segunda a sexta, 8:30–18:00. "
    "NÃO realizamos Raio-X no sábado."
)
us_answer = (
    "US abdominal e cervical: Dra. Fernanda seg/ter/qua/sex (sem quinta). "
    "Sábados intercalados — 22/08/2026 aberto, 29/08 fechado, e segue. "
    "Nesses sábados abertos as marcações de US abdominal e cervical estão livres, 8h–14h. "
    "Quinta de US = Dra. Luciana."
)
for f in faqs:
    q = (f.get("question") or "").lower()
    fid = f.get("id") or f.get("_id")
    if "raio" in q or "radiograf" in q:
        if "sábado" in q or "sabado" in q or "quando" in q or "agenda" in q or "procedimento" in q:
            req(
                "PUT",
                f"https://services.leadconnectorhq.com/knowledge-base/faqs/{fid}",
                {"question": f.get("question"), "answer": (f.get("answer") or "").replace("de seg a sáb", "segunda a sexta (sem sábado)").replace("sábados das 8h às 13h", "sem sábado")[:4500], "locationId": LOC, "knowledgeBaseId": KB},
                version="2021-07-28",
            )
    if "fernanda" in q:
        req(
            "PUT",
            f"https://services.leadconnectorhq.com/knowledge-base/faqs/{fid}",
            {"question": f.get("question"), "answer": us_answer, "locationId": LOC, "knowledgeBaseId": KB},
            version="2021-07-28",
        )
        print("faq fernanda", (f.get("question") or "")[:70])

req(
    "POST",
    "https://services.leadconnectorhq.com/knowledge-base/faqs",
    {
        "locationId": LOC,
        "knowledgeBaseId": KB,
        "question": "O Gamma Vet faz Raio-X no sábado? RX tórax e abdômen no sábado?",
        "answer": rx_answer,
    },
    version="2021-07-28",
)

cmd = [
    "curl.exe", "-s", "-w", " HTTP:%{http_code}",
    "-X", "POST",
    f"https://services.leadconnectorhq.com/knowledge-base/files?locationId={LOC}&knowledgeBaseId={KB}",
    "-H", f"Authorization: Bearer {KEY}",
    "-H", "Version: 2021-07-28",
    "-H", "Accept: application/json",
    "-H", "User-Agent: Mozilla/5.0",
    "-F", f"file=@{(OUT / 'Procedimentos_GammaVet_KB.md')}",
    "-F", f"locationId={LOC}",
    "-F", f"knowledgeBaseId={KB}",
]
r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
print("md", r.stdout[-70:])
print("fim mode", after.get("mode"), "ch", after.get("channels"))
