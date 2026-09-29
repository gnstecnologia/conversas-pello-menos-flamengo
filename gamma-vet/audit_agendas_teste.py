# -*- coding: utf-8 -*-
"""Auditoria de agendas Gamma Vet + teste de free-slots (o que a IA enxerga)."""
from __future__ import annotations

import json
import subprocess
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

OUT = Path(r"c:\Users\GC1\Desktop\Automação GHL\gamma-vet")
ENV = Path(r"c:\Users\GC1\Desktop\Automação GHL\.env")
vals = {}
for line in ENV.read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()

TOKEN = vals["GHL_GAMMA_API_KEY"]
LOC = vals["GHL_GAMMA_LOCATION_ID"]
AGENT = vals["GHL_GAMMA_AGENT_ID"]
CAL_MAP = json.loads((OUT / "calendar-ids-live.json").read_text(encoding="utf-8"))
TZ = ZoneInfo("America/Sao_Paulo")
WEEKDAYS_PT = ["seg", "ter", "qua", "qui", "sex", "sab", "dom"]
DAY_API = {0: "dom", 1: "seg", 2: "ter", 3: "qua", 4: "qui", 5: "sex", 6: "sab"}

EXPECTED = {
    "cintilo": {
        "name": "Cintilografia (tireoide)",
        "allowed": {
            0: ["09:30", "10:00", "13:00", "13:30", "16:00"],  # seg
            1: ["13:00", "13:30", "16:00"],  # ter
            3: ["09:30", "10:00", "13:00", "13:30", "16:00"],  # qui
        },
        "forbid_days": {2, 4, 5},  # qua sex sab
    },
    "fernanda": {
        "name": "US Fernanda",
        "forbid_days": {3},  # qui = Luciana
        "note": "qui=Luciana; sab intercalado",
    },
    "luciana": {
        "name": "US Luciana",
        "prefer_days": {3},
    },
    "rx": {
        "name": "Raio-X",
        "forbid_days": {5},  # sab
    },
    "radio": {
        "name": "Radioiodo",
        "prefer_days": {1},  # ter
    },
}


def curl(method: str, url: str, data=None, version="2021-07-28"):
    cmd = [
        "curl.exe", "-s", "-w", "\nHTTP:%{http_code}",
        "-X", method, url,
        "-H", f"Authorization: Bearer {TOKEN}",
        "-H", f"Version: {version}",
        "-H", "Accept: application/json",
        "-H", "User-Agent: Mozilla/5.0",
    ]
    if data is not None:
        tmp = OUT / "audit" / "req-audit-agendas.json"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        cmd += ["-H", "Content-Type: application/json", "--data-binary", f"@{tmp}"]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    body = r.stdout
    code = "?"
    if "HTTP:" in body:
        body, code = body.rsplit("HTTP:", 1)
        code = code.strip()
    return code, body


def fmt_oh(open_hours):
    if not open_hours:
        return "SEM openHours"
    parts = []
    for block in open_hours:
        days = [DAY_API.get(d, str(d)) for d in (block.get("daysOfTheWeek") or [])]
        hrs = []
        for h in block.get("hours") or []:
            hrs.append(
                f"{h.get('openHour'):02d}:{h.get('openMinute', 0):02d}"
                f"-{h.get('closeHour'):02d}:{h.get('closeMinute', 0):02d}"
            )
        parts.append(f"{','.join(days)}: {' | '.join(hrs)}")
    return " ; ".join(parts)


def parse_slots(payload: dict):
    """GHL free-slots: { '2026-09-01': ['2026-09-01T12:30:00+00:00', ...] } ou slots/array."""
    by_day = defaultdict(list)
    if not isinstance(payload, dict):
        return by_day
    # ignore meta keys
    for k, v in payload.items():
        if k in ("traceId", "status", "message", "slots"):
            continue
        if isinstance(v, list):
            for item in v:
                if isinstance(item, str) and "T" in item:
                    try:
                        dt = datetime.fromisoformat(item.replace("Z", "+00:00")).astimezone(TZ)
                    except Exception:
                        continue
                    by_day[dt.date()].append(dt.strftime("%H:%M"))
                elif isinstance(item, dict):
                    s = item.get("startTime") or item.get("slots") or item.get("start")
                    if isinstance(s, str) and "T" in s:
                        dt = datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(TZ)
                        by_day[dt.date()].append(dt.strftime("%H:%M"))
        elif isinstance(v, dict) and "slots" in v:
            for s in v.get("slots") or []:
                if isinstance(s, str) and "T" in s:
                    dt = datetime.fromisoformat(s.replace("Z", "+00:00")).astimezone(TZ)
                    by_day[dt.date()].append(dt.strftime("%H:%M"))
    for d in by_day:
        by_day[d] = sorted(set(by_day[d]))
    return by_day


def main():
    report = {"generated_at": datetime.now(TZ).isoformat(), "calendars": [], "issues": [], "tests": {}}

    print("=== LISTA CALENDÁRIOS ===")
    code, body = curl("GET", f"https://services.leadconnectorhq.com/calendars/?locationId={LOC}")
    cals = []
    if code == "200" and body.strip().startswith("{"):
        cals = json.loads(body).get("calendars") or []
    print(f"total {len(cals)}")

    id_to_key = {}
    for k, v in CAL_MAP.items():
        if isinstance(v, str):
            id_to_key[v] = k

    # booking action live
    print("\n=== BOOKING ACTION (live) ===")
    code, body = curl(
        "GET",
        f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}?locationId={LOC}",
        version="2021-04-15",
    )
    agent = {}
    if code == "200" and body.strip().startswith("{"):
        agent = json.loads(body).get("agent") or json.loads(body)
    print("mode", agent.get("mode"), "channels", agent.get("channels"), "primary", agent.get("isPrimary"))
    actions = agent.get("actions") or []
    booking = None
    for a in actions:
        if a.get("type") == "appointmentBooking" or "calendar" in str(a).lower():
            booking = a
            break
    # try dedicated endpoint
    act_id = None
    for a in actions:
        if a.get("type") == "appointmentBooking":
            act_id = a.get("id")
            break
    if act_id:
        code2, body2 = curl(
            "GET",
            f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}/actions/{act_id}?locationId={LOC}",
            version="2021-04-15",
        )
        if code2 == "200" and body2.strip().startswith("{"):
            booking = json.loads(body2).get("action") or json.loads(body2)

    triggers = []
    if booking:
        details = booking.get("details") or booking
        for item in details.get("calendarIds") or []:
            cid = item.get("id")
            trig = item.get("triggerCondition") or ""
            key = id_to_key.get(cid, "?")
            triggers.append({"key": key, "id": cid, "trigger": trig[:160]})
            print(f"  [{key}] {cid[:8]}… → {trig[:120]}")
        report["booking_aiDescription"] = (details.get("aiDescription") or "")[:400]
        # check cintilo trigger outdated
        cint_trig = next((t["trigger"] for t in triggers if t["key"] == "cintilo"), "")
        if "terça" not in cint_trig.lower() and "terca" not in cint_trig.lower():
            report["issues"].append(
                "BOOKING: trigger Cintilografia NÃO menciona terça — IA pode achar que só seg/qui"
            )
        if "tireoide" not in cint_trig.lower():
            report["issues"].append(
                "BOOKING: trigger Cintilografia não restringe a TIREOIDE (risco de agendar renal)"
            )
        if "16:00" not in cint_trig and "16h" not in cint_trig.lower():
            report["issues"].append(
                "BOOKING: trigger Cintilografia sem horários fixos 9:30/10/13/13:30/16"
            )
    else:
        report["issues"].append("Booking action não encontrada no agente")
        print("  (sem booking detalhado — actions no agent:", len(actions), ")")

    # detail each mapped calendar + free slots
    now = datetime.now(TZ)
    start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    end = start + timedelta(days=14)
    s_ms = int(start.timestamp() * 1000)
    e_ms = int(end.timestamp() * 1000)

    print("\n=== DETALHE + FREE-SLOTS (14 dias) ===")
    for key in ["fernanda", "luciana", "rx", "tomo", "cintilo", "radio", "eco", "ecg", "endo", "prereserva"]:
        cid = CAL_MAP.get(key)
        if not cid:
            continue
        code, body = curl("GET", f"https://services.leadconnectorhq.com/calendars/{cid}")
        cal = {}
        if code == "200" and body.strip().startswith("{"):
            cal = json.loads(body).get("calendar") or json.loads(body)
        name = cal.get("name") or key
        slot_dur = cal.get("slotDuration")
        slot_int = cal.get("slotInterval")
        oh = fmt_oh(cal.get("openHours"))
        users = [m.get("userId") for m in (cal.get("teamMembers") or [])]
        print(f"\n## {key} | {name} | id={cid}")
        print(f"   type={cal.get('calendarType')} slot={slot_dur}min interval={slot_int} users={users}")
        print(f"   openHours: {oh[:220]}")

        code_s, body_s = curl(
            "GET",
            f"https://services.leadconnectorhq.com/calendars/{cid}/free-slots?startDate={s_ms}&endDate={e_ms}",
        )
        slots_by_day = {}
        raw_preview = body_s[:200].replace("\n", " ")
        if code_s == "200" and body_s.strip().startswith("{"):
            slots_by_day = parse_slots(json.loads(body_s))
        else:
            report["issues"].append(f"{key}: free-slots HTTP {code_s} {raw_preview}")
            print(f"   free-slots FAIL {code_s} {raw_preview}")

        # summarize by weekday
        by_wd = defaultdict(list)
        for d, times in sorted(slots_by_day.items()):
            wd = d.weekday()  # 0=seg
            label = f"{d.isoformat()}({WEEKDAYS_PT[wd]})"
            sample = times[:8]
            extra = f" +{len(times)-8}" if len(times) > 8 else ""
            print(f"   {label}: {', '.join(sample)}{extra}  (n={len(times)})")
            by_wd[wd].extend(times)
            # expected checks
            exp = EXPECTED.get(key)
            if exp and "forbid_days" in exp and wd in exp["forbid_days"] and times:
                report["issues"].append(
                    f"{key}: slots em dia proibido {WEEKDAYS_PT[wd]} {d}: {times[:6]}"
                )
            if key == "cintilo" and "allowed" in EXPECTED["cintilo"]:
                allowed = EXPECTED["cintilo"]["allowed"].get(wd)
                if allowed is None and times:
                    report["issues"].append(
                        f"cintilo: slots em dia sem tireoide {WEEKDAYS_PT[wd]} {d}: {times}"
                    )
                elif allowed is not None:
                    bad = [t for t in times if t not in allowed]
                    missing_hint = [t for t in allowed if t not in times]
                    if bad:
                        report["issues"].append(
                            f"cintilo: horários FORA da lista em {d}({WEEKDAYS_PT[wd]}): {bad}"
                        )
                    # only note missing if day should have some and none of allowed appear
                    if times and not any(t in allowed for t in times):
                        report["issues"].append(
                            f"cintilo: nenhum horário da lista em {d}; tool deu {times[:8]}"
                        )

        entry = {
            "key": key,
            "id": cid,
            "name": name,
            "slotDuration": slot_dur,
            "slotInterval": slot_int,
            "openHours": cal.get("openHours"),
            "users": users,
            "slots_sample": {
                d.isoformat(): times for d, times in sorted(slots_by_day.items())[:10]
            },
            "slot_days_count": len(slots_by_day),
            "total_slots": sum(len(v) for v in slots_by_day.values()),
        }
        report["calendars"].append(entry)
        if entry["total_slots"] == 0 and key not in ("prereserva",):
            report["issues"].append(f"{key}: ZERO free-slots nos próximos 14 dias — IA não consegue oferecer horário")

    # Simulação do que a IA deveria responder (cintilo)
    print("\n=== TESTE SIMULADO: o que a ferramenta devolve p/ TIREOIDE ===")
    cint = next((c for c in report["calendars"] if c["key"] == "cintilo"), None)
    if cint:
        ok_days = []
        bad_days = []
        for d_str, times in cint["slots_sample"].items():
            d = datetime.fromisoformat(d_str).date()
            wd = d.weekday()
            allowed = EXPECTED["cintilo"]["allowed"].get(wd)
            if allowed is None:
                if times:
                    bad_days.append((d_str, times))
                continue
            good = [t for t in times if t in allowed]
            bad = [t for t in times if t not in allowed]
            # filter like prompt says
            filtered = good
            ok_days.append({"date": d_str, "wd": WEEKDAYS_PT[wd], "tool": times, "ia_should_offer": filtered, "discard": bad})
            print(f"  {d_str} ({WEEKDAYS_PT[wd]}): tool={times} → IA deve oferecer={filtered} descartar={bad}")
        report["tests"]["tireoide"] = {"ok": ok_days, "bad_extra_days": bad_days}
        # verdict
        any_offer = any(x["ia_should_offer"] for x in ok_days)
        any_bad = any(x["discard"] for x in ok_days) or bool(bad_days)
        if not any_offer:
            report["issues"].append("TESTE TIREOIDE: após filtrar lista fechada, IA não teria NENHUM horário p/ oferecer")
        if any_bad:
            report["issues"].append(
                "TESTE TIREOIDE: calendário ainda gera slots fora da lista — depende 100% do filtro no prompt"
            )

    print("\n=== ISSUES ===")
    if not report["issues"]:
        print("Nenhum problema automático detectado.")
    for i in report["issues"]:
        print("!", i)

    out_path = OUT / "audit" / "agendas-teste-report.json"
    out_path.write_text(json.dumps(report, ensure_ascii=False, indent=2, default=str), encoding="utf-8")
    print("\nSalvo em", out_path)


if __name__ == "__main__":
    main()
