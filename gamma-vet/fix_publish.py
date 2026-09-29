# -*- coding: utf-8 -*-
"""Corrige Fernanda (sem qui/sáb), PUT agente, booking e FAQs que falharam."""
import json
import re
import urllib.request
import urllib.error
import shutil
from datetime import datetime, timedelta, timezone
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
SID = "qFMZOj1GjAfLRsORSMj7"
UID = "LxQOtMzWVhRqNLlWnLCI"
CAL = json.loads((OUT / "calendar-ids-live.json").read_text(encoding="utf-8"))
UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"


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


def summarize(oh):
    names = {0: "Dom", 1: "Seg", 2: "Ter", 3: "Qua", 4: "Qui", 5: "Sex", 6: "Sab"}
    parts = []
    for block in oh or []:
        ds = ",".join(names.get(int(x), str(x)) for x in block.get("daysOfTheWeek", []))
        parts.append(ds)
    return ",".join(parts)


# 1) tirar associação de Work Hours da Fernanda (senão abre qui/sáb)
print("=== unassoc Fernanda ===")
code, body = req("DELETE", f"https://services.leadconnectorhq.com/calendars/schedules/{SID}/associations/{CAL['fernanda']}")
print("unassoc", code, body if not isinstance(body, dict) else body.get("success", body.get("message", list(body)[:5])))

print("=== PUT Fernanda hours 1,2,3,5 + user ===")
code, body = req(
    "PUT",
    f"https://services.leadconnectorhq.com/calendars/{CAL['fernanda']}",
    {
        "openHours": hours([1, 2, 3, 5], 8, 30, 18, 0),
        "slotDuration": 30,
        "slotDurationUnit": "mins",
        "slotInterval": 30,
        "slotIntervalUnit": "mins",
        "teamMembers": tm(),
        "isActive": True,
        "description": (
            "Ultrassonografia Dra. Fernanda. Segunda, terça, quarta e sexta 8:30-18:00. "
            "NÃO atende quinta. Sábados só com datas da equipe."
        ),
    },
)
cal = body.get("calendar", body) if isinstance(body, dict) else {}
print("fernanda", code, "days", summarize(cal.get("openHours")), "users", [m.get("userId") for m in (cal.get("teamMembers") or [])])

# 2) agente
print("\n=== PUT agent ===")
instructions = (OUT / "system-prompt-completo.md").read_text(encoding="utf-8")
payload = {
    "name": "Assistente Gamma Vet",
    "isPrimary": True,
    "mode": "off",
    "instructions": instructions,
    "goal": (
        "Conduzir o responsável até o agendamento do exame: na primeira resposta já entregar o pacote "
        "(dias, valor, sinal, preparo, exames prévios); coletar dados; consultar agenda real no calendário "
        "correto; oferecer horários só nos dias permitidos e confirmar no sistema. "
        "Não oferecer Fernanda na quinta, cintilo fora de seg/qui, nem radioiodo antes da cintilo de tireoide. "
        "Em dúvida, transferir para humano."
    ),
    "personality": (
        "Formal porém acolhedor. Use animalzinho, seu pet e responsável pelo paciente. "
        "Fale do Gamma Vet no masculino (o centro). Sempre se apresente como assistente virtual do Gamma Vet. "
        "Agradeça a preferência. Respostas curtas, claras, estilo WhatsApp, em português do Brasil. "
        "Áudio: peça texto; você não transcreve áudio de WhatsApp."
    ),
    "knowledgeBaseIds": [KB],
    "channels": ["WebChat"],
    "autoPilotMaxMessages": 100,
    "sleepEnabled": False,
    "sleepOnManualMessage": True,
    "sleepOnWorkflowMessage": False,
}
code, body = req("PUT", f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}", payload, version="2021-07-28")
print("agent PUT", code, str(body)[:200] if not isinstance(body, dict) else body.get("message", "ok"))
code, agent = req("GET", f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}", version="2021-07-28")
agent = agent.get("agent", agent) if isinstance(agent, dict) else {}
inst = agent.get("instructions") or ""
print("isPrimary", agent.get("isPrimary"), "pacote" , "Pacote na 1ª resposta" in inst, "R$350", "R$350" in inst)
(OUT / "agent-live-now.json").write_text(json.dumps(agent, ensure_ascii=False, indent=2), encoding="utf-8")

# 3) booking — GET, merge, PUT com calendarId singular
print("\n=== PUT booking ===")
code, raw = req(
    "GET",
    f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}/actions/{BOOKING}",
    version="2021-04-15",
)
action = raw.get("data", raw) if isinstance(raw, dict) else {}
details = dict(action.get("details") or {})
details["calendarId"] = CAL["fernanda"]
details["calendarIds"] = [
    {
        "id": CAL["fernanda"],
        "triggerCondition": (
            "Ultrassonografia / US / abdominal / cervical / microbolhas / cistocentese com Dra. Fernanda. "
            "Fernanda: segunda, terça, quarta e sexta. NÃO usar na quinta nem no sábado."
        ),
    },
    {
        "id": CAL["luciana"],
        "triggerCondition": (
            "Ultrassonografia / US com Dra. Luciana. OBRIGATÓRIO na quinta (única médica de US na quinta). "
            "Fallback se Fernanda indisponível ou a pedido do tutor."
        ),
    },
    {"id": CAL["eco"], "triggerCondition": "Ecocardiograma / eco / pré-anestésico cardíaco"},
    {"id": CAL["ecg"], "triggerCondition": "Eletrocardiograma / eletro / ECG"},
    {"id": CAL["rx"], "triggerCondition": "Raio-X / radiografia / RX / uretrografia / uretrocistografia / urografia"},
    {
        "id": CAL["tomo"],
        "triggerCondition": "Tomografia / TC. Slot 60 min. TC+citologia 90 min (dois slots ou transferir).",
    },
    {"id": CAL["endo"], "triggerCondition": "Endoscopia / colonoscopia / rinoscopia / broncoscopia"},
    {
        "id": CAL["cintilo"],
        "triggerCondition": (
            "Cintilografia / medicina nuclear. SOMENTE segunda e quinta. NÃO oferecer quarta. "
            "Se pedirem radioiodo, usar ESTA agenda primeiro (cintilo antes da terapia)."
        ),
    },
    {
        "id": CAL["radio"],
        "triggerCondition": (
            "Radioiodoterapia. SOMENTE se a cintilografia de tireoide já tiver sido realizada. "
            "NÃO usar na primeira resposta de quem pede radioiodo. Preferência terças."
        ),
    },
    {"id": CAL["prereserva"], "triggerCondition": "Pré-reserva / fallback / confirmação humana"},
]
details["aiDescription"] = (
    "Agenda exames do Gamma Vet no calendário correto. "
    "US: Dra. Fernanda seg/ter/qua/sex (NUNCA quinta). Quinta de US = Dra. Luciana. "
    "Cintilografia só segunda e quinta. Radioiodoterapia só depois da cintilo de tireoide (terças). "
    "Na segunda, Fernanda faz US 30 min + RX 30 min + TC 1 h (TC+cito 1h30) — horários não coincidem. "
    "Na primeira resposta, informar dias, valor, sinal, preparo e exames prévios. "
    "Só oferecer horários reais da ferramenta."
)
details["fallbackCalendar"] = True
details["fallbackCalendarId"] = CAL["prereserva"]
payload = {"type": "appointmentBooking", "name": "Agendamento Gamma Vet", "details": details}
code, body = req(
    "PUT",
    f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}/actions/{BOOKING}",
    payload,
    version="2021-04-15",
)
print("booking PUT", code, str(body)[:250] if not isinstance(body, dict) else (body.get("message") or body.get("data", {}).get("id") or "ok"))
code, raw = req(
    "GET",
    f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}/actions/{BOOKING}",
    version="2021-04-15",
)
action = raw.get("data", raw) if isinstance(raw, dict) else {}
ids = [c.get("id") for c in ((action.get("details") or {}).get("calendarIds") or [])]
print("booking ids", ids)
print("aiDescription head", ((action.get("details") or {}).get("aiDescription") or "")[:120])
(OUT / "audit" / "booking-action-full.json").write_text(json.dumps(action, ensure_ascii=False, indent=2), encoding="utf-8")

# 4) FAQs: atualizar as que já existem + criar as novas
print("\n=== FAQs upsert ===")
code, data = req(
    "GET",
    f"https://services.leadconnectorhq.com/knowledge-base/faqs?locationId={LOC}&knowledgeBaseId={KB}&limit=100",
    version="2021-07-28",
)
existing = (data or {}).get("faqs") or []
by_q = {(f.get("question") or "").strip().lower(): f for f in existing}
print("existing", len(existing))

faqs_plan = json.loads((OUT / "faqs-plan.json").read_text(encoding="utf-8"))
updated = created = skipped = 0
for f in faqs_plan:
    q = f["question"].strip()
    hit = by_q.get(q.lower())
    if hit:
        fid = hit.get("id") or hit.get("_id")
        code, body = req(
            "PUT",
            f"https://services.leadconnectorhq.com/knowledge-base/faqs/{fid}",
            {"question": q, "answer": f["answer"], "locationId": LOC, "knowledgeBaseId": KB},
            version="2021-07-28",
        )
        if str(code).startswith("2"):
            updated += 1
        else:
            print("PUT faq fail", code, q[:60], str(body)[:120])
    else:
        code, body = req(
            "POST",
            "https://services.leadconnectorhq.com/knowledge-base/faqs",
            {"locationId": LOC, "knowledgeBaseId": KB, "question": q, "answer": f["answer"]},
            version="2021-07-28",
        )
        if str(code).startswith("2"):
            created += 1
        else:
            print("POST faq fail", code, q[:60], str(body)[:120])
print("faqs updated", updated, "created", created)

# 5) upload md
print("\n=== file upload md ===")
md_path = OUT / "Procedimentos_GammaVet_KB.md"
# urllib multipart is painful; use curl via subprocess
import subprocess
cmd = [
    "curl.exe", "-s", "-w", "\nHTTP:%{http_code}",
    "-X", "POST",
    f"https://services.leadconnectorhq.com/knowledge-base/files?locationId={LOC}&knowledgeBaseId={KB}",
    "-H", f"Authorization: Bearer {KEY}",
    "-H", "Version: 2021-07-28",
    "-H", "Accept: application/json",
    "-H", "User-Agent: Mozilla/5.0",
    "-F", f"file=@{md_path}",
    "-F", f"locationId={LOC}",
    "-F", f"knowledgeBaseId={KB}",
    "-F", "name=Procedimentos_GammaVet_KB",
]
r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
print("md upload", r.stdout[-400:].replace("\n", " "))

# 6) slots
print("\n=== SLOTS ===")
tz = timezone(timedelta(hours=-3))
days = ["2026-08-17", "2026-08-18", "2026-08-19", "2026-08-20", "2026-08-21", "2026-08-22"]
keys = ["fernanda", "luciana", "rx", "tomo", "cintilo", "radio"]
print("data       " + " ".join(f"{k:>9}" for k in keys))
for day_s in days:
    start = datetime.fromisoformat(f"{day_s}T00:00:00").replace(tzinfo=tz)
    s = int(start.timestamp() * 1000)
    e = int((start + timedelta(days=1)).timestamp() * 1000)
    parts = [day_s]
    for key in keys:
        code, sl = req(
            "GET",
            f"https://services.leadconnectorhq.com/calendars/{CAL[key]}/free-slots?startDate={s}&endDate={e}",
            version="2021-07-28",
        )
        n = 0
        if isinstance(sl, dict):
            n = len((sl.get(day_s) or {}).get("slots") or [])
        parts.append(f"{n:9d}")
    print(" ".join(parts))
print("Esperado: Fernanda qui=0 sáb=0; Luciana qui>0; Cintilo só seg/qui; Radio só ter.")
