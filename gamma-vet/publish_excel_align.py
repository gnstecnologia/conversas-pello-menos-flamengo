# -*- coding: utf-8 -*-
"""Alinha calendário + prompt + KB ao Excel Procedimentos_GammaVet. Agente mode=off, WebChat."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

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
KB = vals["GHL_GAMMA_KB_ID"]
BOOKING = "g4K4spRJdKq1zpMr2LLb"
CAL = json.loads((OUT / "calendar-ids-live.json").read_text(encoding="utf-8"))
PROMPT = (OUT / "system-prompt-completo.md").read_text(encoding="utf-8")
UID = CAL.get("sharedUserFernanda") or "LxQOtMzWVhRqNLlWnLCI"


def curl(method: str, url: str, data=None, form=None, version="2021-07-28"):
    cmd = [
        "curl.exe", "-s", "-w", "\nHTTP:%{http_code}",
        "-X", method, url,
        "-H", f"Authorization: Bearer {TOKEN}",
        "-H", f"Version: {version}",
        "-H", "Accept: application/json",
        "-H", "User-Agent: Mozilla/5.0",
    ]
    if data is not None:
        tmp = OUT / "audit" / "req-excel-align.json"
        tmp.parent.mkdir(parents=True, exist_ok=True)
        tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        cmd += ["-H", "Content-Type: application/json", "--data-binary", f"@{tmp}"]
    if form:
        for item in form:
            cmd += ["-F", item]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    body = r.stdout
    code = "?"
    if "HTTP:" in body:
        body, code = body.rsplit("HTTP:", 1)
        code = code.strip()
    return code, body


def upload_kb():
    doc = OUT / "Procedimentos_GammaVet_KB.md"
    code, body = curl(
        "POST",
        f"https://services.leadconnectorhq.com/knowledge-base/files?locationId={LOC}&knowledgeBaseId={KB}",
        form=[f"file=@{doc}", f"locationId={LOC}", f"knowledgeBaseId={KB}", "name=Procedimentos_GammaVet_KB"],
    )
    print("kb", code, body[:180].replace("\n", " "))


def upsert_faqs():
    faqs = [
        {
            "question": "Ultrassonografia com microbolhas: valor por peso?",
            "answer": (
                "Até 20 kg: R$ 750,00. De 20 a 25 kg: R$ 850,00. Acima de 26 kg: R$ 950,00. "
                "Região ou nódulo adicional: + R$ 200,00 cada. "
                "Agenda: quartas e quintas. Laudo: até 4 dias úteis."
            ),
        },
        {
            "question": "Cintilografia de tireoide: quais horários exatos?",
            "answer": (
                "Lista fechada: 9:30, 10:00, 13:00, 13:30 e 15:30. "
                "Segunda e quinta: todos os 5. Terça: só 13:00, 13:30 e 15:30. "
                "Nunca oferecer 16:00 nem outro horário fora dessa lista."
            ),
        },
        {
            "question": "Cintilografia de tireoide felina: valor e sinal?",
            "answer": (
                "Valor R$ 1.750,00. Sinal R$ 250,00 (mín. 2 dias antes). "
                "PIX CNPJ 43608666000130. 5% desconto à vista."
            ),
        },
        {
            "question": "Raio-X: valor e sábado?",
            "answer": (
                "R$ 200,00 para 1 região. Cada região adicional R$ 50,00. "
                "Agenda: segunda a sábado (sábados 8h às 13h)."
            ),
        },
        {
            "question": "Eletrocardiograma: valor?",
            "answer": "ECG R$ 110,00. Segunda a sexta, 9h às 16h.",
        },
    ]
    code, body = curl(
        "GET",
        f"https://services.leadconnectorhq.com/knowledge-base/faqs?locationId={LOC}&knowledgeBaseId={KB}&limit=100",
    )
    existing = json.loads(body).get("faqs") or [] if code == "200" else []
    by_q = {(f.get("question") or "").strip().lower(): f for f in existing}
    for item in faqs:
        hit = by_q.get(item["question"].lower())
        payload = {"locationId": LOC, "knowledgeBaseId": KB, **item}
        if hit and hit.get("id"):
            code, body = curl(
                "PUT",
                f"https://services.leadconnectorhq.com/knowledge-base/faqs/{hit['id']}",
                data=payload,
            )
            print("faq PUT", code, item["question"][:55])
        else:
            code, body = curl("POST", "https://services.leadconnectorhq.com/knowledge-base/faqs", data=payload)
            print("faq POST", code, item["question"][:55])


def put_agent():
    payload = {
        "name": "Assistente Gamma Vet",
        "isPrimary": True,
        "mode": "off",
        "channels": ["WebChat"],
        "instructions": PROMPT,
        "goal": (
            "Agendar com pacote na 1ª resposta. Tireoide: SOMENTE 9:30/10/13/13:30/15:30 "
            "(terça sem manhã). Microbolhas: até 20kg R$750, 20-25 R$850, >26 R$950, +R$200. "
            "Sinal tireoide felina R$250. ECG R$110. RX +R$50 região; RX/TC sáb ok. "
            "Tag equipe_interna = silêncio. Renal/encaixes = humano sem Gabapentina."
        ),
        "personality": (
            "Formal porém acolhedor. Gamma Vet no masculino. Assistente virtual. "
            "Áudio: pedir texto. Horários de tireoide: lista fechada 15:30 (nunca 16:00)."
        ),
        "knowledgeBaseIds": [KB],
        "autoPilotMaxMessages": 100,
        "sleepEnabled": False,
        "sleepOnManualMessage": True,
        "sleepOnWorkflowMessage": False,
    }
    code, body = curl(
        "PUT",
        f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}",
        data=payload,
        version="2021-04-15",
    )
    print("agent PUT", code, body[:220].replace("\n", " "))
    code2, body2 = curl(
        "GET",
        f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}?locationId={LOC}",
        version="2021-04-15",
    )
    a = json.loads(body2).get("agent") or json.loads(body2)
    inst = a.get("instructions") or ""
    print(
        "after mode", a.get("mode"),
        "channels", a.get("channels"),
        "primary", a.get("isPrimary"),
        "15:30", "15:30" in inst,
        "sinal250", "R$250" in inst or "R$ 250" in inst,
        "rx50", "R$50" in inst or "R$ 50" in inst,
    )
    if a.get("mode") != "off" or a.get("channels") != ["WebChat"]:
        print("ALERTA mode/channels", a.get("mode"), a.get("channels"))
    (OUT / "agent-live-now.json").write_text(json.dumps(a, ensure_ascii=False, indent=2), encoding="utf-8")


def put_booking():
    code, body = curl(
        "GET",
        f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}/actions/{BOOKING}",
        version="2021-04-15",
    )
    action = json.loads(body).get("data", json.loads(body)) if body.strip().startswith("{") else {}
    details = dict(action.get("details") or {})
    details["calendarId"] = CAL["fernanda"]
    details["calendarIds"] = [
        {
            "id": CAL["fernanda"],
            "triggerCondition": (
                "Ultrassonografia / US / abdominal / cervical / microbolhas / cistocentese com Dra. Fernanda. "
                "Fernanda: segunda, terça, quarta e sexta. NÃO usar na quinta."
            ),
        },
        {
            "id": CAL["luciana"],
            "triggerCondition": (
                "Ultrassonografia / US com Dra. Luciana. OBRIGATÓRIO na quinta. "
                "Fallback se Fernanda indisponível ou a pedido do tutor."
            ),
        },
        {"id": CAL["eco"], "triggerCondition": "Ecocardiograma / eco / pré-anestésico cardíaco"},
        {"id": CAL["ecg"], "triggerCondition": "Eletrocardiograma / eletro / ECG"},
        {
            "id": CAL["rx"],
            "triggerCondition": (
                "Raio-X / radiografia / RX / uretrografia / uretrocistografia / urografia. "
                "Segunda a sábado (sáb 8h–13h)."
            ),
        },
        {
            "id": CAL["tomo"],
            "triggerCondition": (
                "Tomografia / TC. Slot 60 min. TC+citologia 90 min. "
                "Segunda a sábado (sáb 8h–13h)."
            ),
        },
        {"id": CAL["endo"], "triggerCondition": "Endoscopia / colonoscopia / rinoscopia / broncoscopia"},
        {
            "id": CAL["cintilo"],
            "triggerCondition": (
                "SOMENTE cintilografia de TIREOIDE (cão/gato). "
                "Segunda e quinta: 9:30/10:00/13:00/13:30/15:30. Terça: 13:00/13:30/15:30. "
                "NÃO usar para renal, óssea, shunt, paratireoide (encaixes — handoff humano). "
                "Nunca oferecer 16:00; tarde = 15:30. "
                "Se pedirem radioiodo sem cintilo de tireoide feita, usar ESTA agenda primeiro."
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
    details["calendarActionType"] = "multiple"
    details["fallbackCalendar"] = True
    details["fallbackCalendarId"] = CAL["prereserva"]
    details["aiDescription"] = (
        "Agenda exames do Gamma Vet conforme Excel. "
        "Cintilo tireoide: 9:30/10/13/13:30/15:30 (seg/qui; terça sem manhã). "
        "RX e TC: seg–sáb. Renal/encaixes = humano. Radioiodo só depois da cintilo."
    )
    payload = {"type": "appointmentBooking", "name": "Agendamento Gamma Vet", "details": details}
    code, body = curl(
        "PUT",
        f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}/actions/{BOOKING}",
        data=payload,
        version="2021-04-15",
    )
    print("booking PUT", code, body[:280].replace("\n", " "))


def put_cintilo():
    win_sq = [
        {"openHour": 9, "openMinute": 30, "closeHour": 11, "closeMinute": 0},
        {"openHour": 10, "openMinute": 0, "closeHour": 11, "closeMinute": 30},
        {"openHour": 13, "openMinute": 0, "closeHour": 14, "closeMinute": 30},
        {"openHour": 13, "openMinute": 30, "closeHour": 15, "closeMinute": 0},
        {"openHour": 15, "openMinute": 30, "closeHour": 17, "closeMinute": 0},
    ]
    win_ter = [
        {"openHour": 13, "openMinute": 0, "closeHour": 14, "closeMinute": 30},
        {"openHour": 13, "openMinute": 30, "closeHour": 15, "closeMinute": 0},
        {"openHour": 15, "openMinute": 30, "closeHour": 17, "closeMinute": 0},
    ]
    payload = {
        "openHours": [
            {"daysOfTheWeek": [1], "hours": win_sq},
            {"daysOfTheWeek": [2], "hours": win_ter},
            {"daysOfTheWeek": [4], "hours": win_sq},
        ],
        "slotDuration": 90,
        "slotDurationUnit": "mins",
        "slotInterval": 30,
        "slotIntervalUnit": "mins",
        "description": (
            "Cintilografia de TIREOIDE (Excel). "
            "Seg/qui: 9:30, 10:00, 13:00, 13:30, 15:30. "
            "Terça: 13:00, 13:30, 15:30. "
            "Renal e outros protocolos = encaixe humano (IA não agenda)."
        ),
        "teamMembers": [{
            "userId": UID,
            "priority": 0.5,
            "selected": True,
            "isPrimary": True,
        }],
    }
    cid = CAL["cintilo"]
    code, body = curl("PUT", f"https://services.leadconnectorhq.com/calendars/{cid}", data=payload)
    print("cintilo PUT", code, body[:250].replace("\n", " "))


def put_rx_with_saturday():
    """Excel: RX de seg a sáb (sáb 8h–13h)."""
    payload = {
        "openHours": [
            {"daysOfTheWeek": [1], "hours": [{"openHour": 8, "openMinute": 30, "closeHour": 18, "closeMinute": 0}]},
            {"daysOfTheWeek": [2], "hours": [{"openHour": 8, "openMinute": 30, "closeHour": 18, "closeMinute": 0}]},
            {"daysOfTheWeek": [3], "hours": [{"openHour": 8, "openMinute": 30, "closeHour": 18, "closeMinute": 0}]},
            {"daysOfTheWeek": [4], "hours": [{"openHour": 8, "openMinute": 30, "closeHour": 18, "closeMinute": 0}]},
            {"daysOfTheWeek": [5], "hours": [{"openHour": 8, "openMinute": 30, "closeHour": 18, "closeMinute": 0}]},
            {"daysOfTheWeek": [6], "hours": [{"openHour": 8, "openMinute": 0, "closeHour": 13, "closeMinute": 0}]},
        ],
        "slotDuration": 30,
        "slotDurationUnit": "mins",
        "slotInterval": 30,
        "slotIntervalUnit": "mins",
        "teamMembers": [{
            "userId": UID,
            "priority": 0.5,
            "selected": True,
            "isPrimary": True,
            "isZoomAdded": "false",
            "locationConfigurations": [
                {"kind": "custom", "location": "", "position": 0, "zoomOauthId": "", "meetingId": "custom_0"}
            ],
        }],
    }
    cid = CAL["rx"]
    code, body = curl("PUT", f"https://services.leadconnectorhq.com/calendars/{cid}", data=payload)
    print("rx PUT", code, body[:250].replace("\n", " "))


def verify_slots():
    from datetime import datetime, timedelta
    from zoneinfo import ZoneInfo
    TZ = ZoneInfo("America/Sao_Paulo")
    now = datetime.now(TZ).replace(hour=0, minute=0, second=0, microsecond=0)
    s = int(now.timestamp() * 1000)
    e = int((now + timedelta(days=10)).timestamp() * 1000)
    for key in ("cintilo", "rx"):
        cid = CAL[key]
        code, body = curl(
            "GET",
            f"https://services.leadconnectorhq.com/calendars/{cid}/free-slots?startDate={s}&endDate={e}",
        )
        print(f"slots {key}", code)
        if code != "200" or not body.strip().startswith("{"):
            continue
        data = json.loads(body)
        for k, v in sorted(data.items()):
            if k in ("traceId", "status", "message") or not isinstance(v, list):
                continue
            times = []
            for item in v:
                if isinstance(item, str) and "T" in item:
                    dt = datetime.fromisoformat(item.replace("Z", "+00:00")).astimezone(TZ)
                    times.append(dt.strftime("%Y-%m-%d %a %H:%M"))
            if times:
                print(" ", ", ".join(times[:8]), ("..." if len(times) > 8 else ""))


def main():
    print("=== KB ===")
    upload_kb()
    print("=== FAQs ===")
    upsert_faqs()
    print("=== Agent ===")
    put_agent()
    print("=== Booking ===")
    put_booking()
    print("=== Cintilo calendar (15:30) ===")
    put_cintilo()
    print("=== RX calendar (com sabado) ===")
    put_rx_with_saturday()
    print("=== Verify free-slots ===")
    verify_slots()
    print("DONE")


if __name__ == "__main__":
    main()
