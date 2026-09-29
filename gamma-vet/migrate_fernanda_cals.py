# -*- coding: utf-8 -*-
"""Cria agendas service_booking com o mesmo user (Fernanda US + RX + TC)."""
import json
import urllib.request
import urllib.error
from datetime import datetime, timedelta, timezone
from pathlib import Path

ENV = r"c:\Users\GC1\Desktop\Automação GHL\.env"
OUT = Path(r"c:\Users\GC1\Desktop\Automação GHL\gamma-vet")
vals = {}
with open(ENV, encoding="utf-8") as f:
    for line in f:
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            vals[k.strip()] = v.strip()

KEY = vals["GHL_GAMMA_API_KEY"]
LOC = vals["GHL_GAMMA_LOCATION_ID"]
UID = "LxQOtMzWVhRqNLlWnLCI"
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"

OLD = {
    "fernanda": "67dUBkMOw78GdahUsc1t",
    "rx": "sZ984nPHX1C8X6ntMw1d",
    "tomo": "xxgHhAzTmq6GgntlmYV5",
    "luciana": "djzQjTsrDhXWaj3LzjU6",
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
            return json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        print("ERR", method, url, e.code, e.read().decode("utf-8", errors="replace")[:1000])
        return None


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


def tm():
    return [
        {
            "priority": 0.5,
            "selected": True,
            "userId": UID,
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
    parts = []
    for block in oh or []:
        ds = ",".join(names.get(int(x), str(x)) for x in block.get("daysOfTheWeek", []))
        hs = [
            f"{h['openHour']:02d}:{h['openMinute']:02d}-{h['closeHour']:02d}:{h['closeMinute']:02d}"
            for h in block.get("hours", [])
        ]
        parts.append(f"{ds}:{';'.join(hs)}")
    return " | ".join(parts) or "(vazio)"


fernanda_hours = hours([1, 2, 3, 5], 8, 30, 18, 0)
rx_tc_hours = merge(hours([1, 2, 3, 4, 5], 8, 30, 18, 0), hours([6], 8, 0, 13, 0))
luciana_hours = hours([1, 2, 3, 4, 5], 8, 30, 18, 0)
cintilo_hours = hours([1, 4], 9, 30, 16, 0)

creates = {
    "fernanda": {
        "name": "US - Dra. Fernanda",
        "description": (
            "Ultrassonografia Dra. Fernanda. Segunda, terça, quarta e sexta 8:30-18:00. "
            "NÃO atende quinta. Sábados alternados só com datas informadas pela equipe. "
            "Na segunda também conduz RX e TC — horários não podem coincidir."
        ),
        "slotDuration": 30,
        "openHours": fernanda_hours,
        "eventTitle": "{{contact.pet_1_nome}} | US Fernanda | {{contact.procedimento_interesse}}",
    },
    "rx": {
        "name": "Raio-X",
        "description": (
            "Raio-X / radiografia. Seg-sex 8:30-18:00; sábado 8:00-13:00. "
            "Na segunda compartilha profissional com US Fernanda e Tomografia."
        ),
        "slotDuration": 30,
        "openHours": rx_tc_hours,
        "eventTitle": "{{contact.pet_1_nome}} | Raio-X | {{contact.procedimento_interesse}}",
    },
    "tomo": {
        "name": "Tomografia",
        "description": (
            "Tomografia computadorizada. Slot 60 min (TC simples). "
            "TC + citologia = 90 min (dois slots ou equipe). "
            "Na segunda compartilha profissional com US Fernanda e Raio-X."
        ),
        "slotDuration": 60,
        "openHours": rx_tc_hours,
        "eventTitle": "{{contact.pet_1_nome}} | Tomografia | {{contact.procedimento_interesse}}",
    },
}

new_ids = {}
print("=== CRIAR service_booking ===")
for key, spec in creates.items():
    payload = {
        "locationId": LOC,
        "name": spec["name"],
        "description": spec["description"],
        "calendarType": "service_booking",
        "eventType": "RoundRobin_OptimizeForEqualDistribution",
        "slotDuration": spec["slotDuration"],
        "slotDurationUnit": "mins",
        "slotInterval": 30,
        "slotIntervalUnit": "mins",
        "appointmentPerSlot": 1,
        "openHours": spec["openHours"],
        "teamMembers": tm(),
        "isActive": True,
        "autoConfirm": True,
        "eventTitle": spec["eventTitle"],
        "allowReschedule": True,
        "allowCancellation": True,
    }
    created = req("POST", "https://services.leadconnectorhq.com/calendars/", payload)
    if not created:
        raise SystemExit(f"falhou criar {key}")
    cal = created.get("calendar", created)
    cid = cal.get("id")
    new_ids[key] = cid
    members = [m.get("userId") for m in (cal.get("teamMembers") or [])]
    print(
        key,
        cid,
        "slot",
        cal.get("slotDuration"),
        "days",
        summarize(cal.get("openHours")),
        "user",
        members,
    )

# desativar agendas event antigas (não apagar — tem 1 evento passado na Fernanda)
print("\n=== DESATIVAR event antigas ===")
renames = {
    "fernanda": "OLD event — US Fernanda (não usar)",
    "rx": "OLD event — Raio-X (não usar)",
    "tomo": "OLD event — Tomografia (não usar)",
}
for key, old_id in renames.items():
    old = req("GET", f"https://services.leadconnectorhq.com/calendars/{OLD[key]}")
    old = (old or {}).get("calendar", old)
    payload = {
        "name": renames[key],
        "isActive": False,
        "openHours": old.get("openHours") or creates[key]["openHours"],
        "slotDuration": old.get("slotDuration") or creates[key]["slotDuration"],
        "slotDurationUnit": "mins",
    }
    out = req("PUT", f"https://services.leadconnectorhq.com/calendars/{OLD[key]}", payload)
    cal = (out or {}).get("calendar", out) or {}
    print(key, "active=", cal.get("isActive"), "name=", cal.get("name"))

# Luciana e Cintilo: só horas/descrição, SEM teamMembers (event type rejeita array vazio)
print("\n=== PUT Luciana / Cintilo (sem teamMembers) ===")
for key, cid, spec in [
    (
        "luciana",
        OLD["luciana"],
        {
            "openHours": luciana_hours,
            "slotDuration": 30,
            "slotDurationUnit": "mins",
            "description": (
                "Ultrassonografia Dra. Luciana. Inclui quinta (única médica de US na quinta). "
                "Fallback nos demais dias se Fernanda indisponível ou a pedido do tutor."
            ),
        },
    ),
    (
        "cintilo",
        OLD["cintilo"],
        {
            "openHours": cintilo_hours,
            "slotDuration": 90,
            "slotDurationUnit": "mins",
            "description": (
                "Cintilografias. SOMENTE segunda e quinta, 9:30-16:00. "
                "Não oferecer quarta nem outros dias. Tireoide antes de radioiodo."
            ),
        },
    ),
]:
    out = req("PUT", f"https://services.leadconnectorhq.com/calendars/{cid}", spec)
    cal = (out or {}).get("calendar", out) or {}
    print(key, "days=", summarize(cal.get("openHours")), "slot=", cal.get("slotDuration"))

ids_path = OUT / "calendar-ids-live.json"
payload_ids = {
    "fernanda": new_ids["fernanda"],
    "luciana": OLD["luciana"],
    "rx": new_ids["rx"],
    "tomo": new_ids["tomo"],
    "cintilo": OLD["cintilo"],
    "radio": "DFrcSX7SDJ5uJbz3qZ3C",
    "eco": "T5uEa6vjDhpZUI1lZO1z",
    "ecg": "AxyMBOCfMaeb0yjEGtJ6",
    "endo": "D1e35F8TiJCsBqsqAJPz",
    "prereserva": "XmdN5Odpbe063UXOo8YV",
    "old_event": OLD,
    "sharedUserFernanda": UID,
}
ids_path.write_text(json.dumps(payload_ids, indent=2), encoding="utf-8")
print("\nsalvo", ids_path)

tz = timezone(timedelta(hours=-3))
print("\n=== SLOTS ===")
days = ["2026-08-17", "2026-08-18", "2026-08-19", "2026-08-20", "2026-08-21", "2026-08-22"]
keys = ["fernanda", "luciana", "rx", "tomo", "cintilo"]
cals = {
    "fernanda": new_ids["fernanda"],
    "luciana": OLD["luciana"],
    "rx": new_ids["rx"],
    "tomo": new_ids["tomo"],
    "cintilo": OLD["cintilo"],
}
print("data       " + " ".join(f"{k:>9}" for k in keys))
for day_s in days:
    start = datetime.fromisoformat(f"{day_s}T00:00:00").replace(tzinfo=tz)
    s = int(start.timestamp() * 1000)
    e = int((start + timedelta(days=1)).timestamp() * 1000)
    parts = [day_s]
    for key in keys:
        sl = req(
            "GET",
            f"https://services.leadconnectorhq.com/calendars/{cals[key]}/free-slots?startDate={s}&endDate={e}",
            version="2021-07-28",
        ) or {}
        n = len((sl.get(day_s) or {}).get("slots") or [])
        parts.append(f"{n:9d}")
    print(" ".join(parts))
