# -*- coding: utf-8 -*-
import json
import urllib.request
from datetime import datetime, timedelta, timezone

key = None
for line in open(r"c:\Users\GC1\Desktop\Automação GHL\.env", encoding="utf-8"):
    if line.startswith("GHL_MULTIODONTO_API_KEY="):
        key = line.split("=", 1)[1].strip()

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
LOC = "3R4hY0j3TJyj2SkmSQL3"
h = {
    "Authorization": "Bearer " + key,
    "Version": "2021-07-28",
    "Accept": "application/json",
    "User-Agent": UA,
}


def req(url):
    r = urllib.request.Request(url, headers=h)
    return json.loads(urllib.request.urlopen(r, timeout=60).read().decode())


def summarize(oh):
    names = {0: "Dom", 1: "Seg", 2: "Ter", 3: "Qua", 4: "Qui", 5: "Sex", 6: "Sab"}
    parts = []
    for block in oh or []:
        ds = ",".join(names.get(int(x), str(x)) for x in block.get("daysOfTheWeek", []))
        hs = []
        for x in block.get("hours", []):
            hs.append(
                f"{x.get('openHour',0):02d}:{x.get('openMinute',0):02d}-{x.get('closeHour',0):02d}:{x.get('closeMinute',0):02d}"
            )
        parts.append(f"{ds} {';'.join(hs)}")
    return " | ".join(parts) or "(vazio)"


cals = req(f"https://services.leadconnectorhq.com/calendars/?locationId={LOC}")["calendars"]
cg = []
print("=== AGENDAS CAMPO GRANDE ===")
for c in cals:
    if "Campo Grande" in (c.get("name") or "") and c.get("calendarType") == "service_booking":
        full = req(f"https://services.leadconnectorhq.com/calendars/{c['id']}")
        cal = full.get("calendar", full)
        cg.append(cal)
        short = cal["name"].replace(" | Campo Grande", "")
        print(f"- {short}")
        print(f"  hours: {summarize(cal.get('openHours'))}")
        print(f"  active={cal.get('isActive')} user={cal['teamMembers'][0].get('userId') if cal.get('teamMembers') else '?'}")

tz = timezone(timedelta(hours=-3))
wd = {0: "Seg", 1: "Ter", 2: "Qua", 3: "Qui", 4: "Sex", 5: "Sab"}
days = []
d = datetime(2026, 8, 17, tzinfo=tz)
end = datetime(2026, 8, 29, tzinfo=tz)
while d <= end:
    if d.weekday() != 6:
        days.append(d)
    d += timedelta(days=1)

names = []
for cal in cg:
    short = cal["name"].replace(" | Campo Grande", "").replace("Dr. ", "").replace("Dra. ", "").replace("Dr ", "").replace("Dra ", "")
    names.append((short.strip(), cal["id"]))

print("\n=== QUANTIDADE DE VAGAS ===")
header = f"{'Dia':<16}" + "".join(f"{n[0][:13]:>14}" for n in names)
print(header)
details = []
for day in days:
    day_s = day.strftime("%Y-%m-%d")
    label = f"{wd[day.weekday()]} {day.strftime('%d/%m')}"
    s = int(day.timestamp() * 1000)
    e = int((day + timedelta(days=1)).timestamp() * 1000)
    row = f"{label:<16}"
    line_detail = [label]
    for n, cid in names:
        sl = req(
            f"https://services.leadconnectorhq.com/calendars/{cid}/free-slots?startDate={s}&endDate={e}"
        )
        slots = (sl.get(day_s) or {}).get("slots") or []
        row += f"{len(slots):>14}"
        if slots:
            times = ", ".join(x[11:16] for x in slots)
            line_detail.append(f"{n}: {times}")
        else:
            line_detail.append(f"{n}: —")
    print(row)
    details.append(line_detail)

print("\n=== HORARIOS (quando tem vaga) ===")
for line in details:
    print(line[0])
    for item in line[1:]:
        if not item.endswith(": —"):
            print(" ", item)
