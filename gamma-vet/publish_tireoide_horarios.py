# -*- coding: utf-8 -*-
"""Publica horários tireoide + regra encaixe renal/protocolos. Agente permanece mode=off."""
from __future__ import annotations

import json
import shutil
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
MD = OUT / "Procedimentos_GammaVet_KB.md"
TXT = OUT / "Procedimentos_GammaVet_KB.txt"
# usuário para teamMembers da agenda Cintilografia (API exige >=1)
CINTILO_USER = "v6rvJVeXBnBObCiYnxMJ"  # Fernanda — fallback se não achar Gustavo


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
        tmp = OUT / "audit" / "req.json"
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


def get_agent():
    code, body = curl(
        "GET",
        f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}?locationId={LOC}",
        version="2021-04-15",
    )
    if code != "200":
        raise SystemExit(f"GET agent fail {code} {body[:300]}")
    data = json.loads(body)
    return data.get("agent") or data.get("data") or data


def resolve_cintilo_user() -> str:
    code, body = curl("GET", f"https://services.leadconnectorhq.com/users/?locationId={LOC}")
    if code == "200" and body.strip().startswith("{"):
        for u in json.loads(body).get("users") or []:
            name = (u.get("name") or "").lower()
            email = (u.get("email") or "").lower()
            if "gustavo" in name or "gustavo" in email:
                return u["id"]
            if "cobucci" in name or "cobucci" in email:
                return u["id"]
    return CINTILO_USER


def upload_md():
    # API aceita .md (txt é rejeitado)
    doc = OUT / "Procedimentos_GammaVet_KB.md"
    variants = [
        (
            f"https://services.leadconnectorhq.com/knowledge-base/files?locationId={LOC}&knowledgeBaseId={KB}",
            [f"file=@{doc}", f"locationId={LOC}", f"knowledgeBaseId={KB}", "name=Procedimentos_GammaVet_KB"],
        ),
        (
            "https://services.leadconnectorhq.com/knowledge-base/files",
            [f"file=@{doc}", f"locationId={LOC}", f"knowledgeBaseId={KB}"],
        ),
    ]
    for url, form in variants:
        code, body = curl("POST", url, form=form)
        print("file upload", code, body[:220].replace("\n", " "))
        if code.startswith("2"):
            return True
    return False


def upsert_faqs():
    items = [
        {
            "question": "Cintilografia de tireoide: quais dias e horários?",
            "answer": (
                "Segunda e quinta: 9:30, 10:00, 13:00, 13:30 e 16:00. "
                "Terça: 13:00, 13:30 e 16:00 (sem manhã). "
                "Nunca oferecer quarta, sexta, sábado nem 15:30 (usar 16:00). "
                "Felino R$ 1.750 + sinal R$ 200. Canino R$ 1.250 (+ sedação R$ 250 se necessária) + sinal R$ 200."
            ),
        },
        {
            "question": "Cintilografia renal: a IA agenda?",
            "answer": (
                "Não. Renal e demais protocolos (óssea, shunt, paratireoide) são ENCAIXES — "
                "a IA não oferece horário; informa valor/sinal se souber e transfere para a equipe humana. "
                "A IA agenda só tireoide (~90% da casuística)."
            ),
        },
        {
            "question": "Radioiodoterapia pode ser marcada direto?",
            "answer": (
                "Não. Primeiro cintilografia de tireoide nos horários fixos "
                "(seg/qui manhã+tarde; terça só tarde). "
                "Radioiodo R$ 4.000 + perfil hormonal do dia R$ 295. "
                "Só marcar radioiodo (terças) se a cintilo já tiver sido feita."
            ),
        },
        {
            "question": "Cintilografia de tireoide: quais dias, valor e sinal?",
            "answer": (
                "Segunda e quinta: 9:30/10:00/13:00/13:30/16:00. Terça: 13:00/13:30/16:00. "
                "Felino R$ 1.750 + sinal R$ 200. Canino R$ 1.250 (+ sedação R$ 250 se necessária) e sinal R$ 200. "
                "Não oferecer 15:30 nem quarta/sexta/sábado."
            ),
        },
    ]
    code, body = curl(
        "GET",
        f"https://services.leadconnectorhq.com/knowledge-base/faqs?locationId={LOC}&knowledgeBaseId={KB}&limit=100",
    )
    existing = []
    if code == "200" and body.strip().startswith("{"):
        existing = json.loads(body).get("faqs") or []
    by_q = {(f.get("question") or "").strip().lower(): f for f in existing}
    for item in items:
        q = item["question"]
        hit = by_q.get(q.lower())
        payload = {
            "locationId": LOC,
            "knowledgeBaseId": KB,
            "question": item["question"],
            "answer": item["answer"],
        }
        if hit and (hit.get("id") or hit.get("_id")):
            fid = hit.get("id") or hit.get("_id")
            code, body = curl(
                "PUT",
                f"https://services.leadconnectorhq.com/knowledge-base/faqs/{fid}",
                data=payload,
            )
            print("faq PUT", code, q[:60])
        else:
            code, body = curl(
                "POST",
                "https://services.leadconnectorhq.com/knowledge-base/faqs",
                data=payload,
            )
            print("faq POST", code, q[:60])


def put_agent():
    payload = {
        "name": "Assistente Gamma Vet",
        "isPrimary": True,
        "mode": "off",
        "channels": ["WebChat"],
        "instructions": PROMPT,
        "goal": (
            "Conduzir o responsável até o agendamento: pacote na 1ª resposta; "
            "tireoide nos horários fixos (seg/qui 9:30/10/13/13:30/16; terça 13/13:30/16); "
            "NÃO agendar renal nem outros protocolos de cintilo (encaixe → humano); "
            "radioiodo só depois da cintilo de tireoide. Em dúvida, transferir."
        ),
        "personality": (
            "Formal porém acolhedor. Use animalzinho, seu pet e responsável pelo paciente. "
            "Fale do Gamma Vet no masculino (o centro). Sempre se apresente como assistente virtual do Gamma Vet. "
            "Agradeça a preferência. Respostas curtas, claras, estilo WhatsApp, em português do Brasil. "
            "Áudio: peça texto; você não transcreve áudio de WhatsApp."
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
    print("agent PUT", code, body[:250].replace("\n", " "))
    after = get_agent()
    (OUT / "agent-live-now.json").write_text(json.dumps(after, ensure_ascii=False, indent=2), encoding="utf-8")
    inst = after.get("instructions") or ""
    print(
        "after primary", after.get("isPrimary"),
        "mode", after.get("mode"),
        "channels", after.get("channels"),
        "16:00", "16:00" in inst,
        "encaixe", "encaixe" in inst.lower(),
        "Terça:", "Terça:" in inst,
    )
    if after.get("isPrimary") is not True:
        print("ALERTA: isPrimary caiu")
    if after.get("mode") != "off":
        print("ALERTA: mode não está off")
    if after.get("channels") != ["WebChat"]:
        print("ALERTA channels:", after.get("channels"))
    return after


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
            "triggerCondition": "Raio-X / radiografia / RX / uretrografia / uretrocistografia / urografia",
        },
        {
            "id": CAL["tomo"],
            "triggerCondition": "Tomografia / TC. Slot 60 min. TC+citologia 90 min (dois slots ou transferir).",
        },
        {"id": CAL["endo"], "triggerCondition": "Endoscopia / colonoscopia / rinoscopia / broncoscopia"},
        {
            "id": CAL["cintilo"],
            "triggerCondition": (
                "SOMENTE cintilografia de TIREOIDE (cão/gato). "
                "Segunda e quinta: 9:30/10:00/13:00/13:30/16:00. Terça: 13:00/13:30/16:00. "
                "NÃO usar para renal, óssea, shunt, paratireoide (encaixes — handoff humano). "
                "Nunca oferecer 15:30; tarde = 16:00. "
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
        "Agenda exames do Gamma Vet. "
        "Cintilo: a IA só agenda TIREOIDE nos horários fixos "
        "(seg/qui 9:30/10/13/13:30/16; terça 13/13:30/16). "
        "Renal e demais protocolos = encaixe, transferir humano sem slot. "
        "Radioiodo só depois da cintilo de tireoide. "
        "Só oferecer horários reais da ferramenta filtrados pela lista fechada."
    )
    payload = {"type": "appointmentBooking", "name": "Agendamento Gamma Vet", "details": details}
    code, body = curl(
        "PUT",
        f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}/actions/{BOOKING}",
        data=payload,
        version="2021-04-15",
    )
    print("booking PUT", code, body[:280].replace("\n", " "))


def put_cintilo_hours(user_id: str):
    """Janelas estreitas para só gerar starts permitidos (slot 90 min)."""
    windows_seg_qui = [
        {"openHour": 9, "openMinute": 30, "closeHour": 11, "closeMinute": 0},   # 9:30
        {"openHour": 10, "openMinute": 0, "closeHour": 11, "closeMinute": 30},  # 10:00
        {"openHour": 13, "openMinute": 0, "closeHour": 14, "closeMinute": 30},  # 13:00
        {"openHour": 13, "openMinute": 30, "closeHour": 15, "closeMinute": 0},  # 13:30
        {"openHour": 16, "openMinute": 0, "closeHour": 17, "closeMinute": 30},  # 16:00
    ]
    windows_ter = [
        {"openHour": 13, "openMinute": 0, "closeHour": 14, "closeMinute": 30},
        {"openHour": 13, "openMinute": 30, "closeHour": 15, "closeMinute": 0},
        {"openHour": 16, "openMinute": 0, "closeHour": 17, "closeMinute": 30},
    ]
    open_hours = [
        {"daysOfTheWeek": [1], "hours": windows_seg_qui},  # segunda
        {"daysOfTheWeek": [2], "hours": windows_ter},      # terça
        {"daysOfTheWeek": [4], "hours": windows_seg_qui},  # quinta
    ]
    tm = [{
        "userId": user_id,
        "priority": 0.5,
        "selected": True,
        "isPrimary": True,
    }]
    payload = {
        "openHours": open_hours,
        "slotDuration": 90,
        "slotDurationUnit": "mins",
        "slotInterval": 30,
        "slotIntervalUnit": "mins",
        "description": (
            "Cintilografia de TIREOIDE. "
            "Seg/qui: 9:30, 10:00, 13:00, 13:30, 16:00. "
            "Terça: 13:00, 13:30, 16:00. "
            "Renal e outros protocolos = encaixe humano (IA não agenda)."
        ),
        "teamMembers": tm,
    }
    cid = CAL["cintilo"]
    code, body = curl("PUT", f"https://services.leadconnectorhq.com/calendars/{cid}", data=payload)
    print("cintilo hours PUT", code, body[:300].replace("\n", " "))
    code2, body2 = curl("GET", f"https://services.leadconnectorhq.com/calendars/{cid}")
    if code2 == "200":
        cal = json.loads(body2).get("calendar") or {}
        print("cintilo openHours", json.dumps(cal.get("openHours"), ensure_ascii=False)[:600])
        (OUT / "audit" / "cal-cintilo-after-tireoide.json").write_text(
            json.dumps(cal, ensure_ascii=False, indent=2), encoding="utf-8"
        )


def main():
    print("=== KB md ===")
    upload_md()
    print("=== FAQs ===")
    upsert_faqs()
    print("=== Agent ===")
    before = get_agent()
    print("before", before.get("isPrimary"), before.get("mode"), before.get("channels"))
    put_agent()
    print("=== Booking ===")
    put_booking()
    print("=== Cintilo calendar ===")
    uid = resolve_cintilo_user()
    print("cintilo user", uid)
    put_cintilo_hours(uid)
    print("DONE")


if __name__ == "__main__":
    main()
