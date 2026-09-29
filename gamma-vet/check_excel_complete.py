# -*- coding: utf-8 -*-
import json
import re
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from zoneinfo import ZoneInfo

import openpyxl

sys.stdout.reconfigure(encoding="utf-8")
OUT = Path(r"c:\Users\GC1\Desktop\Automação GHL\gamma-vet")
vals = {}
for line in Path(r"c:\Users\GC1\Desktop\Automação GHL\.env").read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()
TOKEN = vals["GHL_GAMMA_API_KEY"]
LOC = vals["GHL_GAMMA_LOCATION_ID"]
AGENT = vals["GHL_GAMMA_AGENT_ID"]
CAL = json.loads((OUT / "calendar-ids-live.json").read_text(encoding="utf-8"))
PROMPT = (OUT / "system-prompt-completo.md").read_text(encoding="utf-8")
KB = (OUT / "Procedimentos_GammaVet_KB.md").read_text(encoding="utf-8")


def curl(url, ver="2021-04-15"):
    cmd = [
        "curl.exe", "-s", url,
        "-H", f"Authorization: Bearer {TOKEN}",
        "-H", f"Version: {ver}",
        "-H", "Accept: application/json",
        "-H", "User-Agent: Mozilla/5.0",
    ]
    return subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace").stdout


wb = openpyxl.load_workbook(
    Path(r"c:\Users\GC1\Downloads\Procedimentos_GammaVet (1) (1).xlsx"), data_only=True
)
ws = wb["Procedimentos"]

print("=== AGENT LIVE ===")
a = json.loads(curl(f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}?locationId={LOC}")).get(
    "agent"
) or {}
inst = a.get("instructions") or ""
print("mode", a.get("mode"), "channels", a.get("channels"), "primary", a.get("isPrimary"))
checks = [
    ("15:30 no prompt live", "15:30" in inst),
    ("sinal R$250", "R$250" in inst or "R$ 250" in inst),
    ("ECG R$110", "R$110" in inst or "R$ 110" in inst),
    ("RX +R$50", "R$50" in inst or "R$ 50" in inst),
    ("microbolhas 20 kg", "20 kg" in inst),
    ("RX permite sabado", "Raio-X:** segunda a sábado" in inst or "RX:** segunda a sábado" in inst or "segunda a sábado" in inst),
    ("nao citar Gabapentina", "Gabapentina" in inst),
]
for n, ok in checks:
    print(("OK" if ok else "FALTA"), n)

print("\n=== KB ===")
kb_checks = [
    ("microbolhas ate 20kg", "até 20kg" in KB or "animais até 20kg" in KB),
    ("ECG valor 110", "**Valor:**\n110" in KB),
    ("RX +50", "região adicional R$ 50" in KB),
    ("RX seg a sab", "de seg a sáb" in KB),
    ("sinal felina 250", "Sinal: R$ 250,00" in KB),
    ("tireoide 15:30 lista", "13:30 / 15:30" in KB),
    ("sem lista 16:00 tireoide", "13:30 / 16:00" not in KB),
]
for n, ok in kb_checks:
    print(("OK" if ok else "FALTA"), n)

print("\n=== RESQUICIOS RUINS ===")
bad = [
    ("KB micro 10kg antiga", "até **10 kg**" in KB or "Até **10 kg**" in KB),
    ("KB RX +80", "região adicional R$ 80" in KB),
    ("prompt micro 10kg", "até 10 kg" in PROMPT),
    ("prompt ECG 120", "ECG **R$120**" in PROMPT),
    ("prompt RX +80", "R$80**/região" in PROMPT or "R$80**/" in PROMPT),
]
for n, flag in bad:
    print(("AINDA TEM" if flag else "limpo"), n)

print("\n=== CALENDARIOS ===")
for key in ["cintilo", "rx", "tomo"]:
    c = json.loads(curl(f"https://services.leadconnectorhq.com/calendars/{CAL[key]}", "2021-07-28")).get("calendar") or {}
    days = sorted({d for b in (c.get("openHours") or []) for d in (b.get("daysOfTheWeek") or [])})
    print(key, "days", days, "slot", c.get("slotDuration"), "users", len(c.get("teamMembers") or []))

TZ = ZoneInfo("America/Sao_Paulo")
now = datetime.now(TZ).replace(hour=0, minute=0, second=0, microsecond=0)
s = int(now.timestamp() * 1000)
e = int((now + timedelta(days=12)).timestamp() * 1000)

print("\n=== CINTILO SLOTS ===")
d = json.loads(
    curl(
        f"https://services.leadconnectorhq.com/calendars/{CAL['cintilo']}/free-slots?startDate={s}&endDate={e}",
        "2021-07-28",
    )
)
all_ok = True
for k, v in sorted(d.items()):
    if k == "traceId" or not isinstance(v, dict):
        continue
    slots = [x[11:16] for x in (v.get("slots") or [])]
    wd = datetime.fromisoformat(k).weekday()
    print(" ", k, "wd", wd, slots)
    if "16:00" in slots:
        all_ok = False
        print("   !! ainda tem 16:00")
    if wd in (0, 3) and slots and "15:30" not in slots and len(slots) >= 4:
        print("   !! seg/qui sem 15:30?")
print("cintilo sem 16:00?", all_ok)

print("\n=== RX SABADO SLOTS ===")
d = json.loads(
    curl(
        f"https://services.leadconnectorhq.com/calendars/{CAL['rx']}/free-slots?startDate={s}&endDate={e}",
        "2021-07-28",
    )
)
sats = []
for k, v in sorted(d.items()):
    if k == "traceId" or not isinstance(v, dict):
        continue
    if datetime.fromisoformat(k).weekday() == 5:
        sats.append((k, len(v.get("slots") or [])))
print("sabados com slot:", sats if sats else "NENHUM (openHours tem sab, user schedule bloqueia)")

print("\n=== BOOKING ===")
b = json.loads(curl(f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}/actions/g4K4spRJdKq1zpMr2LLb"))
details = (b.get("data") or b).get("details") or {}
cint = next((x for x in details.get("calendarIds") or [] if x.get("id") == CAL["cintilo"]), {})
rx = next((x for x in details.get("calendarIds") or [] if x.get("id") == CAL["rx"]), {})
print("cintilo 15:30?", "15:30" in (cint.get("triggerCondition") or ""))
print("cintilo 16:00?", "16:00" in (cint.get("triggerCondition") or ""))
print("rx sab?", "sábado" in (rx.get("triggerCondition") or "").lower())

print("\n=== EXCEL vs SISTEMA (pontos que Excel tem e podem faltar) ===")
faltas = []
# Luciana sem user
luc = json.loads(curl(f"https://services.leadconnectorhq.com/calendars/{CAL['luciana']}", "2021-07-28")).get("calendar") or {}
if not (luc.get("teamMembers") or []):
    faltas.append("US Luciana sem usuario (teamMembers vazio)")
cin = json.loads(curl(f"https://services.leadconnectorhq.com/calendars/{CAL['cintilo']}", "2021-07-28")).get("calendar") or {}
if not (cin.get("teamMembers") or []):
    faltas.append("Cintilo sem usuario (teamMembers vazio) — slots aparecem, booking pode falhar")
if not sats:
    faltas.append("RX: openHours tem sabado, mas free-slots nao geram sabado (agenda do usuario)")
# Excel radioiodo hours 15:30 - radio calendar
rad = json.loads(curl(f"https://services.leadconnectorhq.com/calendars/{CAL['radio']}", "2021-07-28")).get("calendar") or {}
print("radio openHours", json.dumps(rad.get("openHours"), ensure_ascii=False)[:200])
# Excel US abdominal = seg a sex only — Fernanda has sat intercalated (operational extra, ok)
# Excel cistocentese seg a sab — uses Fernanda cal which has sat intercalated — partial
faltas.append("Cistocentese no Excel e seg-sab; na pratica usa agenda Fernanda (sab intercalado) — ok operacional")
faltas.append("Agente mode=off: nao da para testar conversa WhatsApp ao vivo")
# Excel regras: nao enviar orcamento no 1o contato — IA envia valores (produto)
faltas.append("Aba regras Excel: 'nao enviar orcamento' / transferir humano — IA atual agenda e informa valor (intencional)")
for f in faltas:
    print("-", f)
