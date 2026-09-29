# -*- coding: utf-8 -*-
"""Publica KB (do MD já editado), prompt do agente (isPrimary true) e triggers de booking."""
from __future__ import annotations

import json
import re
import subprocess
import time
from datetime import datetime, timedelta, timezone
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


def faqs_from_md(text: str) -> list[dict]:
    faqs = []

    def add(q, a):
        q = re.sub(r"\s+", " ", q).strip()
        a = a.strip()
        if q and a:
            faqs.append({"question": q[:500], "answer": a[:4500]})

    add(
        "Quem é o Gamma Vet? Onde fica?",
        "O Gamma Vet é um centro de diagnóstico por imagem avançado, pioneiro na medicina nuclear "
        "veterinária no Brasil. Localizado na Barra da Tijuca, no Shopping Città Vet "
        "(shopping aberto, estacionamento privado e Pet Friendly), a cerca de 15 minutos da Zona Sul "
        "e do Recreio dos Bandeirantes.",
    )
    add(
        "Qual o horário de funcionamento do Gamma Vet?",
        "Segunda a sexta 8:30–18:00. Sábado 8:00–14:00 (vários exames até 13:00). Domingo fechado. "
        "Preferência do tutor: só manhã ou tarde.",
    )
    add(
        "Na primeira resposta, o que a assistente deve informar sobre o exame?",
        "Pacote obrigatório na primeira mensagem: dias da agenda daquele exame, valor, sinal se houver, "
        "formas de pagamento, preparo, exames prévios e pedido médico. Não esperar o tutor perguntar. "
        "Se pedir dia fora da agenda, recusar e oferecer só os dias certos.",
    )
    add(
        "Dra. Fernanda atende quinta? Quem faz US na quinta?",
        "A Dra. Fernanda NÃO atende quinta (atende segunda, terça, quarta e sexta). "
        "Quinta de ultrassonografia é só a Dra. Luciana. Sábados da Fernanda só quando a equipe informar datas.",
    )
    add(
        "Cintilografia de tireoide: quais dias, valor e sinal?",
        "Somente segunda e quinta. Felino R$ 1.750 + sinal R$ 200. Canino R$ 1.250 (+ sedação R$ 250 se necessária) "
        "e sinal R$ 200. Não oferecer quarta nem outros dias. Sedação felina avaliada no dia.",
    )
    add(
        "Radioiodoterapia pode ser marcada direto?",
        "Não. Primeiro a cintilografia de tireoide (segunda e quinta). Radioiodo R$ 4.000, perfil hormonal do dia "
        "R$ 295. Só marcar radioiodo (terças) se a cintilo já tiver sido feita.",
    )
    add(
        "Ultrassonografia abdominal e cervical: valor e preparo?",
        "Valor R$ 350 cada. Abdominal: jejum 8h (diabético 4h; filhote 1–2h), água liberada. "
        "Cervical: sem preparo, salvo se combinada com abdominal.",
    )
    add(
        "Cintilografia renal: Gabapentina, tempo e valor?",
        "R$ 950 cães e gatos + sinal R$ 200. Tempo 30 min. Gabapentina só para renal FELINA (não citar em caninos).",
    )
    add(
        "Laudo de ultrassonografia com microbolhas demora quanto?",
        "Até 4 dias úteis.",
    )

    parts = re.split(r"\n## ", text)
    for part in parts[1:]:
        lines = part.strip().splitlines()
        if not lines:
            continue
        name = lines[0].strip()
        body = "\n".join(lines[1:]).strip()
        if name in {
            "Quem somos",
            "Horário de funcionamento",
            "Exames que realizamos",
            "Exames que NÃO realizamos",
            "PIX / sinal",
        }:
            continue
        if body:
            add(f"Procedimento {name}: preparo, agenda, plano e valor", body[:4500])

    seen = set()
    uniq = []
    for f in faqs:
        k = f["question"].lower()
        if k in seen:
            continue
        seen.add(k)
        uniq.append(f)
    return uniq


def clear_faqs():
    code, body = curl(
        "GET",
        f"https://services.leadconnectorhq.com/knowledge-base/faqs?locationId={LOC}&knowledgeBaseId={KB}&limit=100",
    )
    print("list faqs", code)
    data = json.loads(body) if body.strip().startswith("{") else {}
    faqs = data.get("faqs") or []
    print("existing faqs", len(faqs))
    for f in faqs:
        fid = f.get("id") or f.get("_id")
        if not fid:
            continue
        for path in [f"/knowledge-base/faqs/{fid}", f"/knowledge-base/faq/{fid}"]:
            c, b = curl(
                "DELETE",
                f"https://services.leadconnectorhq.com{path}?locationId={LOC}&knowledgeBaseId={KB}",
            )
            if c.startswith("2"):
                break
        time.sleep(0.05)


def upload_faqs(faqs):
    ok = fail = 0
    for i, f in enumerate(faqs, 1):
        payload = {
            "locationId": LOC,
            "knowledgeBaseId": KB,
            "question": f["question"],
            "answer": f["answer"],
        }
        code, body = curl("POST", "https://services.leadconnectorhq.com/knowledge-base/faqs", data=payload)
        if code.startswith("2"):
            ok += 1
        else:
            fail += 1
            print("FAIL FAQ", i, code, body[:180].replace("\n", " "))
        if i % 15 == 0:
            print(f"progress {i}/{len(faqs)} ok={ok} fail={fail}")
            time.sleep(0.15)
    print(f"FAQ upload done ok={ok} fail={fail} total={len(faqs)}")


def upload_file():
    doc = OUT / "Procedimentos_GammaVet_KB.txt"
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
        print("file upload", code, body[:250].replace("\n", " "))
        if code.startswith("2"):
            return True
    return False


def put_agent():
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
        "knowledgeBaseTriggers": [
            {
                "mode": "all",
                "knowledgeBaseIds": [KB],
                "triggerCondition": "",
                "priority": 2,
            }
        ],
        "channels": ["WebChat"],
        "autoPilotMaxMessages": 100,
        "sleepEnabled": False,
        "sleepOnManualMessage": True,
        "sleepOnWorkflowMessage": False,
    }
    code, body = curl(
        "PUT",
        f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}",
        data=payload,
    )
    print("agent PUT", code, body[:250].replace("\n", " "))
    code2, body2 = curl("GET", f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}")
    agent = json.loads(body2).get("agent", json.loads(body2))
    print("GET isPrimary", agent.get("isPrimary"), "mode", agent.get("mode"))
    inst = agent.get("instructions") or ""
    print("instructions has pacote?", "Pacote na 1ª resposta" in inst)
    print("instructions has R$350?", "R$350" in inst or "R$ 350" in inst)
    (OUT / "agent-live-now.json").write_text(json.dumps(agent, ensure_ascii=False, indent=2), encoding="utf-8")
    if agent.get("isPrimary") is not True:
        print("ALERTA: isPrimary não está true")
    return agent


def put_booking():
    details = {
        "calendarIds": [
            {
                "id": CAL["fernanda"],
                "triggerCondition": (
                    "Ultrassonografia / US / abdominal / cervical / microbolhas / cistocentese com Dra. Fernanda. "
                    "Fernanda: segunda, terça, quarta e sexta. NÃO usar esta agenda na quinta nem no sábado "
                    "(sábados só quando a equipe informar datas)."
                ),
            },
            {
                "id": CAL["luciana"],
                "triggerCondition": (
                    "Ultrassonografia / US com Dra. Luciana. OBRIGATÓRIO na quinta (única médica de US na quinta). "
                    "Também fallback se Fernanda indisponível ou a pedido do tutor."
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
                "triggerCondition": (
                    "Tomografia / TC / tomografia computadorizada. Slot 60 min. "
                    "TC + citologia = 90 min (dois slots ou transferir)."
                ),
            },
            {"id": CAL["endo"], "triggerCondition": "Endoscopia / colonoscopia / rinoscopia / broncoscopia"},
            {
                "id": CAL["cintilo"],
                "triggerCondition": (
                    "Cintilografia / medicina nuclear diagnóstica (renal, tireoide, óssea, shunt, paratireoide). "
                    "SOMENTE segunda e quinta. NÃO oferecer quarta nem outros dias. "
                    "Se o tutor pediu radioiodo, usar ESTA agenda primeiro (cintilo antes da terapia)."
                ),
            },
            {
                "id": CAL["radio"],
                "triggerCondition": (
                    "Radioiodoterapia / iodo radioativo. SOMENTE se a cintilografia de tireoide já tiver sido realizada. "
                    "NÃO usar esta agenda na primeira resposta de quem pede radioiodo. Preferência terças."
                ),
            },
            {"id": CAL["prereserva"], "triggerCondition": "Pré-reserva / fallback / confirmação humana"},
        ],
        "calendarActionType": "multiple",
        "aiDescription": (
            "Agenda exames do Gamma Vet no calendário correto. "
            "US: Dra. Fernanda seg/ter/qua/sex (NUNCA quinta). Quinta de US = Dra. Luciana. "
            "Cintilografia só segunda e quinta. Radioiodoterapia só depois da cintilo de tireoide (terças). "
            "Na segunda, Fernanda faz US 30 min + RX 30 min + TC 1 h (TC+cito 1h30) — horários não podem coincidir. "
            "Na primeira resposta do exame, já informar dias, valor, sinal, preparo e exames prévios. "
            "Só oferecer horários reais da ferramenta e recusar dia fora da agenda."
        ),
        "fallbackCalendar": True,
        "fallbackCalendarId": CAL["prereserva"],
        "onlySendLink": False,
        "triggerWorkflow": False,
        "sleepAfterBooking": False,
        "transferBot": False,
        "rescheduleEnabled": True,
        "cancelEnabled": True,
    }
    payload = {"type": "appointmentBooking", "name": "Agendamento Gamma Vet", "details": details}
    code, body = curl(
        "PUT",
        f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}/actions/{BOOKING}",
        data=payload,
        version="2021-04-15",
    )
    print("booking PUT", code, body[:400].replace("\n", " "))
    code2, body2 = curl(
        "GET",
        f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}/actions/{BOOKING}",
        version="2021-04-15",
    )
    print("booking GET", code2)
    data = json.loads(body2).get("data", json.loads(body2)) if body2.strip().startswith("{") else {}
    ids = [c.get("id") for c in ((data.get("details") or {}).get("calendarIds") or [])]
    print("booking calendar ids", ids)
    (OUT / "audit" / "booking-action-full.json").write_text(
        json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def validate_slots():
    tz = timezone(timedelta(hours=-3))
    days = ["2026-08-17", "2026-08-18", "2026-08-19", "2026-08-20", "2026-08-21", "2026-08-22"]
    keys = ["fernanda", "luciana", "rx", "tomo", "cintilo", "radio"]
    print("\n=== SLOTS ===")
    print("data       " + " ".join(f"{k:>9}" for k in keys))
    for day_s in days:
        start = datetime.fromisoformat(f"{day_s}T00:00:00").replace(tzinfo=tz)
        s = int(start.timestamp() * 1000)
        e = int((start + timedelta(days=1)).timestamp() * 1000)
        parts = [day_s]
        for key in keys:
            code, body = curl(
                "GET",
                f"https://services.leadconnectorhq.com/calendars/{CAL[key]}/free-slots?startDate={s}&endDate={e}",
                version="2021-07-28",
            )
            sl = json.loads(body) if body.strip().startswith("{") else {}
            n = len((sl.get(day_s) or {}).get("slots") or [])
            parts.append(f"{n:9d}")
        print(" ".join(parts))
    print("Esperado: Fernanda qui=0 sáb=0; Cintilo só seg/qui; Radio só ter; Luciana qui>0.")


def main():
    md = (OUT / "Procedimentos_GammaVet_KB.md").read_text(encoding="utf-8")
    (OUT / "Procedimentos_GammaVet_KB.txt").write_text(md, encoding="utf-8")
    faqs = faqs_from_md(md)
    (OUT / "faqs-plan.json").write_text(json.dumps(faqs, ensure_ascii=False, indent=2), encoding="utf-8")
    print("FAQs", len(faqs), "md chars", len(md))
    clear_faqs()
    upload_faqs(faqs)
    upload_file()
    put_agent()
    put_booking()
    validate_slots()


if __name__ == "__main__":
    main()
