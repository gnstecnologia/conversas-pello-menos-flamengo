#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Corrige tools Gamma Vet: prioriza campos essenciais, booking, follow-up, handoff."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

TOKEN = "pit-7f81ae98-ee67-4025-a4d6-1c4f8b5bcef7"
LOC = "MhplIQf1baCvRBNGPTOj"
AGENT = "nEndeX5NE4uDJG7414RF"
BOOKING = "KM2hdh1Sm6u83AyDGaCy"
OUT = Path(r"c:\Users\GC1\Desktop\Automação GHL\gamma-vet\audit")
OUT.mkdir(parents=True, exist_ok=True)

CAL = {
    "fernanda": "LuylqTlDWQcpnmeslByJ",
    "luciana": "djzQjTsrDhXWaj3LzjU6",
    "eco": "T5uEa6vjDhpZUI1lZO1z",
    "ecg": "AxyMBOCfMaeb0yjEGtJ6",
    "rx": "vg2u63L3YGB06FIYxir7",
    "tomo": "mEEG83mugYscOdjGRlsb",
    "endo": "D1e35F8TiJCsBqsqAJPz",
    "cintilo": "HeFRPrO55KkQjhfJIaNc",
    "radio": "DFrcSX7SDJ5uJbz3qZ3C",
    "prereserva": "XmdN5Odpbe063UXOo8YV",
}

# Keep these updateContactField action names; delete the rest of that type
KEEP = {
    "Nome Pet Ativo",
    "Pet 1 Nome",
    "Pet 1 Especie",
    "Pet 1 Raca",
    "Pet 1 Sexo",
    "Pet 1 Peso",
    "Pet 1 Castrado",
    "Pet 1 Nascimento",
    "CPF Tutor",
    "Procedimento Interesse",
    "Periodo Preferido",
    "Datas Preferidas",
    "Profissional Preferido",
    "Plano Saude",
    "Motivo Exame",
    "Medicacoes em Uso",
    "Vet Solicitante Nome",
    "Status Pedido Medico",
    "Nivel Urgencia",
    "Valor Informado",
}


def curl(method, url, data=None, version="2021-04-15"):
    cmd = [
        "curl.exe", "-s", "-w", "\nHTTP:%{http_code}", "-X", method, url,
        "-H", f"Authorization: Bearer {TOKEN}",
        "-H", f"Version: {version}",
        "-H", "Accept: application/json",
        "-H", "User-Agent: Mozilla/5.0",
    ]
    if data is not None:
        tmp = OUT / "req.json"
        tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        cmd += ["-H", "Content-Type: application/json", "--data-binary", f"@{tmp}"]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    body = r.stdout
    code = "?"
    if "HTTP:" in body:
        body, code = body.rsplit("HTTP:", 1)
        code = code.strip()
    return code, body


def list_actions_detailed():
    code, body = curl("GET", f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}", version="2021-07-28")
    agent = json.loads(body).get("agent", json.loads(body))
    detailed = []
    for a in agent.get("actions") or []:
        c2, b2 = curl("GET", f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}/actions/{a['id']}")
        if c2.startswith("2"):
            detailed.append(json.loads(b2).get("data"))
        else:
            detailed.append(a)
    return agent, detailed


def prune_and_create_fields(fmap):
    agent, actions = list_actions_detailed()
    field_actions = [a for a in actions if a.get("type") == "updateContactField"]
    print("field actions now", len(field_actions))

    # Delete Pet 2 / Pet 3 extras to free slots
    for a in field_actions:
        name = a.get("name") or ""
        if name.startswith("Pet 2") or name.startswith("Pet 3"):
            code, body = curl(
                "DELETE",
                f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}/actions/{a['id']}",
            )
            print("DEL", name, code)
            time.sleep(0.1)

    agent, actions = list_actions_detailed()
    existing_names = {a.get("name") for a in actions if a.get("type") == "updateContactField"}
    print("remaining field actions", len(existing_names), sorted(existing_names))

    needed = [
        ("CPF Tutor", "CPF Tutor", "Registrar CPF do responsável pelo paciente.", ["123.456.789-00", "12345678900"]),
        ("Procedimento Interesse", "Procedimento Interesse", "Registrar o exame/procedimento desejado.", ["ultrassonografia abdominal", "tomografia", "cintilografia renal", "ecocardiograma"]),
        ("Periodo Preferido", "Periodo Preferido", "Registrar preferência: manhã ou tarde (sem noite).", ["manhã", "tarde"]),
        ("Datas Preferidas", "Datas Preferidas", "Registrar datas/dias preferidos.", ["amanhã", "quarta-feira", "semana que vem"]),
        ("Profissional Preferido", "Profissional Preferido", "Registrar profissional preferido (Fernanda/Luciana).", ["Fernanda", "Luciana", "Dra. Fernanda"]),
        ("Plano Saude", "Plano Saude", "Registrar plano: Pet Love, Au Happy, particular ou nenhum.", ["Pet Love", "Au Happy", "particular"]),
        ("Motivo Exame", "Motivo Exame", "Registrar motivo clínico do exame.", ["check-up", "vômito", "nódulo"]),
        ("Medicacoes em Uso", "Medicacoes em Uso", "Registrar medicações em uso.", ["nenhuma", "metimazol"]),
        ("Vet Solicitante Nome", "Vet Solicitante Nome", "Registrar nome do veterinário solicitante.", ["Dr. João", "Dra. Ana"]),
        ("Status Pedido Medico", "Status Pedido Medico", "Status do pedido: pendente, recebido_foto, recebido_pdf.", ["pendente", "recebido_foto", "recebido_pdf"]),
        ("Nivel Urgencia", "Nivel Urgencia", "normal, prioridade ou urgencia.", ["normal", "prioridade", "urgencia"]),
        ("Valor Informado", "Valor Informado", "Valor numérico informado ao cliente (sem R$).", ["400", "1500", "1750"]),
    ]

    for action_name, field_name, desc, examples in needed:
        if action_name in existing_names:
            print("skip", action_name)
            continue
        fid = fmap.get(field_name)
        if not fid:
            print("missing field", field_name)
            continue
        payload = {
            "type": "updateContactField",
            "name": action_name,
            "details": {
                "contactFieldId": fid,
                "description": desc,
                "contactUpdateExamples": examples,
            },
        }
        code, body = curl(
            "POST",
            f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}/actions",
            data=payload,
        )
        print("ADD", action_name, code, body[:120].replace("\n", " "))
        time.sleep(0.15)
        if not code.startswith("2"):
            # maybe still at limit
            print("stop creating due to", code)
            break


def fix_booking():
    details = {
        "calendarIds": [
            {"id": CAL["fernanda"], "triggerCondition": "Ultrassonografia / US / abdominal / cervical / microbolhas / cistocentese com Dra. Fernanda (preferencial)"},
            {"id": CAL["luciana"], "triggerCondition": "Ultrassonografia / US com Dra. Luciana (fallback ou pedido do cliente)"},
            {"id": CAL["eco"], "triggerCondition": "Ecocardiograma / eco / pré-anestésico cardíaco"},
            {"id": CAL["ecg"], "triggerCondition": "Eletrocardiograma / eletro / ECG"},
            {"id": CAL["rx"], "triggerCondition": "Raio-X / radiografia / RX / uretrografia / uretrocistografia / urografia"},
            {"id": CAL["tomo"], "triggerCondition": "Tomografia / TC / tomografia computadorizada"},
            {"id": CAL["endo"], "triggerCondition": "Endoscopia / colonoscopia / rinoscopia / broncoscopia"},
            {"id": CAL["cintilo"], "triggerCondition": "Cintilografia / medicina nuclear diagnóstica"},
            {"id": CAL["radio"], "triggerCondition": "Radioiodoterapia / iodo radioativo"},
            {"id": CAL["prereserva"], "triggerCondition": "Pré-reserva / fallback / confirmação humana"},
        ],
        "calendarActionType": "multiple",
        "aiDescription": (
            "Agenda exames da Gamma Vet no calendário correto. "
            "US: Fernanda preferencial, Luciana fallback. "
            "Eco, ECG, RX, Tomografia, Endoscopia/Rino/Bronco, Cintilografia e Radioiodoterapia têm calendários próprios. "
            "Use Pré-reserva Interna como fallback. Microbolhas só qua/qui. "
            "Só oferecer horários reais da ferramenta."
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
    )
    print("booking", code, body[:350].replace("\n", " "))


def fix_followup():
    agent, actions = list_actions_detailed()
    for a in actions:
        if a.get("type") == "advancedFollowup":
            print("followup exists", a.get("id"))
            return

    # dayOfTheWeek: 1=Mon ... 7=Sun (API rejected 0)
    working = []
    for d in range(1, 7):
        working.append({"dayOfTheWeek": d, "intervals": [{"startHour": 7, "startMinute": 0, "endHour": 20, "endMinute": 0}]})
    working.append({"dayOfTheWeek": 7, "intervals": [{"startHour": 10, "startMinute": 0, "endHour": 20, "endMinute": 0}]})

    msgs = [
        (1, 15, "minutes", "Olá! Vi sua mensagem sobre o exame do seu pet. Posso seguir te ajudando a reunir as informações para agendarmos?"),
        (2, 1, "hours", "Oi! Só para não perder o fio — você gostaria de agendar algum exame na Gamma Vet? Estou à disposição."),
        (3, 2, "hours", "Quando puder me diga qual exame deseja e o nome do animalzinho. Assim avanço com o agendamento."),
        (4, 7, "hours", "Passando para saber se ainda posso ajudar com o agendamento. Se preferir, nossa equipe humana também pode te atender."),
        (5, 12, "hours", "Último retorno por aqui: se quiser retomar o agendamento na Gamma Vet, é só responder esta conversa."),
    ]
    seq = [
        {
            "id": i,
            "followupTime": t,
            "followupTimeUnit": unit,
            "aiEnabledMessage": False,
            "customMessage": msg,
            "triggerWorkflow": False,
        }
        for i, t, unit, msg in msgs
    ]
    payload = {
        "type": "advancedFollowup",
        "name": "Follow-up parado de responder",
        "details": {
            "enabled": True,
            "scenarioId": "contactStoppedReplying",
            "followupSequence": seq,
            "followupSettings": {
                "dynamicChannelSwitching": False,
                "followUpHours": True,
                "workingHours": working,
            },
        },
    }
    code, body = curl(
        "POST",
        f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}/actions",
        data=payload,
    )
    print("followup", code, body[:500].replace("\n", " "))


def fix_handover():
    agent, actions = list_actions_detailed()
    if any(a.get("type") == "humanHandOver" for a in actions):
        print("handover exists")
        return

    # Try simpler payload matching Multiodonto/docs
    attempts = [
        {
            "type": "humanHandOver",
            "name": "Transferir para humano",
            "details": {
                "enabled": True,
                "handoverType": "contactRequest",
                "triggerCondition": "Quando o responsável pedir atendimento humano ou precisar da equipe de agendamento.",
                "examples": ["quero falar com uma pessoa", "pode me transferir", "atendimento humano", "falar com a recepção"],
                "skipAssignToUser": True,
                "createTask": False,
                "reactivateEnabled": True,
                "sleepTimeUnit": "hours",
                "sleepTime": 24,
                "finalMessage": "Vou te transferir para nossa equipe humana da Gamma Vet. Em instantes alguém dá continuidade, ok?",
            },
        },
        {
            "type": "humanHandOver",
            "name": "Transferir para humano",
            "details": {
                "enabled": True,
                "handoverType": "custom",
                "triggerCondition": "Quando o responsável pedir atendimento humano.",
                "examples": ["quero falar com uma pessoa", "pode me transferir", "atendimento humano"],
                "reactivateEnabled": False,
                "finalMessage": "Vou te transferir para nossa equipe humana da Gamma Vet.",
            },
        },
    ]
    for i, payload in enumerate(attempts, 1):
        code, body = curl(
            "POST",
            f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}/actions",
            data=payload,
        )
        print(f"handover try{i}", code, body[:400].replace("\n", " "))
        if code.startswith("2"):
            break


def main():
    fmap = json.loads((OUT / "fields-map.json").read_text(encoding="utf-8"))
    # refresh fields map
    code, body = curl("GET", f"https://services.leadconnectorhq.com/locations/{LOC}/customFields", version="2021-07-28")
    fields = json.loads(body).get("customFields") or []
    fmap = {f["name"]: f["id"] for f in fields}
    (OUT / "fields-map.json").write_text(json.dumps(fmap, ensure_ascii=False, indent=2), encoding="utf-8")

    prune_and_create_fields(fmap)
    fix_booking()
    fix_followup()
    fix_handover()

    agent, actions = list_actions_detailed()
    print("\n=== FINAL ===")
    for a in actions:
        print("-", a.get("type"), "|", a.get("name"))
    Path(r"c:\Users\GC1\Desktop\Automação GHL\gamma-vet\actions-completo.json").write_text(
        json.dumps(actions, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    Path(r"c:\Users\GC1\Desktop\Automação GHL\gamma-vet\agent-completo.json").write_text(
        json.dumps(agent, ensure_ascii=False, indent=2), encoding="utf-8"
    )


if __name__ == "__main__":
    main()
