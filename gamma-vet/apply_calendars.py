# -*- coding: utf-8 -*-
"""Ajusta openHours / duração / user compartilhado das agendas Gamma Vet."""
import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path

ENV = r"c:\Users\GC1\Desktop\Automação GHL\.env"
OUT = Path(r"c:\Users\GC1\Desktop\Automação GHL\gamma-vet\audit")
vals = {}
with open(ENV, encoding="utf-8") as f:
    for line in f:
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            vals[k.strip()] = v.strip()

KEY = vals["GHL_GAMMA_API_KEY"]
LOC = vals["GHL_GAMMA_LOCATION_ID"]
UID_FERNANDA = "LxQOtMzWVhRqNLlWnLCI"  # único user da location; compartilhado US+RX+TC
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"

CAL = {
    "fernanda": "67dUBkMOw78GdahUsc1t",
    "luciana": "djzQjTsrDhXWaj3LzjU6",
    "rx": "sZ984nPHX1C8X6ntMw1d",
    "tomo": "xxgHhAzTmq6GgntlmYV5",
    "cintilo": "HeFRPrO55KkQjhfJIaNc",
}


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
        with urllib.request.urlopen(r, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        err = e.read().decode("utf-8", errors="replace")
        print("ERR", method, url, e.code, err[:800])
        return e.code, err


def hours(days, oh, om, ch, cm):
    return [
        {
            "daysOfTheWeek": [d],
            "hours": [{"openHour": oh, "openMinute": om, "closeHour": ch, "closeMinute": cm}],
        }
        for d in days
    ]


def merge(*blocks):
    by_day = {}
    for block in blocks:
        for entry in block:
            for d in entry["daysOfTheWeek"]:
                by_day.setdefault(d, []).extend(entry["hours"])
    return [{"daysOfTheWeek": [d], "hours": hs} for d, hs in sorted(by_day.items())]


def tm(uid):
    return [
        {
            "priority": 0.5,
            "selected": True,
            "userId": uid,
            "isPrimary": True,
            "isZoomAdded": "false",
            "locationConfigurations": [
                {
                    "kind": "custom",
                    "location": "",
                    "position": 0,
                    "zoomOauthId": "",
                    "meetingId": "custom_0",
                }
            ],
        }
    ]


def summarize(oh):
    names = {0: "Dom", 1: "Seg", 2: "Ter", 3: "Qua", 4: "Qui", 5: "Sex", 6: "Sab"}
    if not oh:
        return "(vazio)"
    parts = []
    for block in oh:
        ds = ",".join(names.get(int(x), str(x)) for x in block.get("daysOfTheWeek", []))
        hs = []
        for h in block.get("hours", []):
            hs.append(
                f"{h['openHour']:02d}:{h['openMinute']:02d}-{h['closeHour']:02d}:{h['closeMinute']:02d}"
            )
        parts.append(f"{ds}:{';'.join(hs)}")
    return " | ".join(parts)


def users_of(cal):
    return ",".join(m.get("userId", "") for m in (cal.get("teamMembers") or [])) or "(nenhum)"


weekday_clinic = hours([1, 2, 3, 4, 5], 8, 30, 18, 0)
fernanda_hours = hours([1, 2, 3, 5], 8, 30, 18, 0)  # sem quinta
rx_tc_hours = merge(hours([1, 2, 3, 4, 5], 8, 30, 18, 0), hours([6], 8, 0, 13, 0))
cintilo_hours = hours([1, 4], 9, 30, 16, 0)

specs = {
    "fernanda": {
        "openHours": fernanda_hours,
        "slotDuration": 30,
        "teamMembers": tm(UID_FERNANDA),
        "description": (
            "Ultrassonografia Dra. Fernanda. Segunda, terça, quarta e sexta 8:30-18:00. "
            "NÃO atende quinta. Sábados alternados só com datas informadas pela equipe. "
            "Na segunda também conduz RX e TC — horários não podem coincidir."
        ),
    },
    "luciana": {
        "openHours": weekday_clinic,
        "slotDuration": 30,
        "teamMembers": [],  # outro “user”: sem o user da Fernanda
        "description": (
            "Ultrassonografia Dra. Luciana. Inclui quinta (única médica de US na quinta). "
            "Fallback nos demais dias se Fernanda indisponível ou a pedido do tutor."
        ),
    },
    "rx": {
        "openHours": rx_tc_hours,
        "slotDuration": 30,
        "teamMembers": tm(UID_FERNANDA),
        "description": (
            "Raio-X / radiografia. Seg-sex 8:30-18:00; sábado 8:00-13:00. "
            "Na segunda compartilha profissional com US Fernanda e Tomografia."
        ),
    },
    "tomo": {
        "openHours": rx_tc_hours,
        "slotDuration": 60,
        "teamMembers": tm(UID_FERNANDA),
        "description": (
            "Tomografia computadorizada. Slot 60 min (TC simples). "
            "TC + citologia = 90 min (dois slots ou equipe). "
            "Na segunda compartilha profissional com US Fernanda e Raio-X."
        ),
    },
    "cintilo": {
        "openHours": cintilo_hours,
        "slotDuration": 90,
        "teamMembers": [],
        "description": (
            "Cintilografias. SOMENTE segunda e quinta, 9:30-16:00. "
            "Não oferecer quarta nem outros dias. Tireoide antes de radioiodo."
        ),
    },
}

print("=== PUT calendários ===")
for key, spec in specs.items():
    cid = CAL[key]
    payload = {
        "openHours": spec["openHours"],
        "slotDuration": spec["slotDuration"],
        "slotDurationUnit": "mins",
        "slotInterval": 30,
        "slotIntervalUnit": "mins",
        "description": spec["description"],
        "teamMembers": spec["teamMembers"],
    }
    code, body = req("PUT", f"https://services.leadconnectorhq.com/calendars/{cid}", payload)
    cal = body.get("calendar", body) if isinstance(body, dict) else {}
    print(
        key,
        code,
        "slot=",
        cal.get("slotDuration"),
        "days=",
        summarize(cal.get("openHours")),
        "user=",
        users_of(cal),
    )
    (OUT / f"cal-{cid}-after.json").write_text(
        json.dumps(cal, ensure_ascii=False, indent=2) if isinstance(cal, dict) else str(body),
        encoding="utf-8",
    )

tz = timezone(timedelta(hours=-3))
print("\n=== SLOTS (validação) ===")
# próximas datas: seg 17 (hoje), ter 18, qua 19, qui 20, sex 21, sáb 22
days = ["2026-08-17", "2026-08-18", "2026-08-19", "2026-08-20", "2026-08-21", "2026-08-22"]
labels = {
    "fernanda": "Fernanda",
    "luciana": "Luciana",
    "rx": "RX",
    "tomo": "TC",
    "cintilo": "Cintilo",
}
header = "data       " + " ".join(f"{labels[k]:>9}" for k in specs)
print(header)
for day_s in days:
    start = datetime.fromisoformat(f"{day_s}T00:00:00").replace(tzinfo=tz)
    s = int(start.timestamp() * 1000)
    e = int((start + timedelta(days=1)).timestamp() * 1000)
    parts = [day_s]
    for key in specs:
        cid = CAL[key]
        code, sl = req(
            "GET",
            f"https://services.leadconnectorhq.com/calendars/{cid}/free-slots?startDate={s}&endDate={e}",
            version="2021-07-28",
        )
        slots = []
        if isinstance(sl, dict):
            slots = (sl.get(day_s) or {}).get("slots") or []
        parts.append(f"{len(slots):9d}")
    print(" ".join(parts))

print("\nEsperado: Fernanda qui=0 e sáb=0; Cintilo só seg/qui; TC slots ~metade do RX (60 vs 30 min).")
