#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Provisiona Gamma Vet completo: campos, agendas, tools, follow-ups e prompt."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path

TOKEN = "pit-7f81ae98-ee67-4025-a4d6-1c4f8b5bcef7"
LOC = "MhplIQf1baCvRBNGPTOj"
AGENT = "nEndeX5NE4uDJG7414RF"
KB = "yissd6WHhYpyP4yw9TlL"
BOOKING_ACTION = "KM2hdh1Sm6u83AyDGaCy"

OUT = Path(r"c:\Users\GC1\Desktop\Automação GHL\gamma-vet")
AUDIT = OUT / "audit"
AUDIT.mkdir(parents=True, exist_ok=True)

# Calendar IDs
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


def curl(method: str, url: str, data=None, version: str = "2021-07-28"):
    cmd = [
        "curl.exe", "-s", "-w", "\nHTTP:%{http_code}", "-X", method, url,
        "-H", f"Authorization: Bearer {TOKEN}",
        "-H", f"Version: {version}",
        "-H", "Accept: application/json",
        "-H", "User-Agent: Mozilla/5.0",
    ]
    if data is not None:
        tmp = AUDIT / "req.json"
        tmp.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        cmd += ["-H", "Content-Type: application/json", "--data-binary", f"@{tmp}"]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    body = r.stdout
    code = "?"
    if "HTTP:" in body:
        body, code = body.rsplit("HTTP:", 1)
        code = code.strip()
    return code, body


def hours(days, open_h, open_m, close_h, close_m):
    return [
        {
            "daysOfTheWeek": [d],
            "hours": [
                {
                    "openHour": open_h,
                    "openMinute": open_m,
                    "closeHour": close_h,
                    "closeMinute": close_m,
                }
            ],
        }
        for d in days
    ]


def merge_hours(*blocks):
    # blocks are lists of openHours entries; merge by day
    by_day = {}
    for block in blocks:
        for entry in block:
            for d in entry["daysOfTheWeek"]:
                by_day.setdefault(d, [])
                by_day[d].extend(entry["hours"])
    return [{"daysOfTheWeek": [d], "hours": hs} for d, hs in sorted(by_day.items())]


def ensure_custom_fields():
    code, body = curl("GET", f"https://services.leadconnectorhq.com/locations/{LOC}/customFields")
    fields = json.loads(body).get("customFields") or []
    by_name = {f.get("name"): f for f in fields}
    print("existing fields", len(fields))

    needed = [
        ("Pet 1 Sexo", "TEXT", "Sexo do pet 1 (macho/fêmea)"),
        ("Pet 2 Sexo", "TEXT", "Sexo do pet 2 (macho/fêmea)"),
        ("Pet 3 Sexo", "TEXT", "Sexo do pet 3 (macho/fêmea)"),
        ("Pet 2 Castrado", "TEXT", "Pet 2 castrado? sim/não"),
        ("Pet 3 Castrado", "TEXT", "Pet 3 castrado? sim/não"),
        ("Pet 2 Nascimento", "DATE", "Data de nascimento do pet 2"),
        ("Pet 3 Nascimento", "DATE", "Data de nascimento do pet 3"),
        ("Email Tutor", "TEXT", "E-mail do responsável"),
        ("Cidade Tutor", "TEXT", "Cidade do responsável"),
        ("CEP Tutor", "TEXT", "CEP do responsável"),
    ]
    created = {}
    for name, dtype, placeholder in needed:
        if name in by_name:
            created[name] = by_name[name]["id"]
            print("field exists", name, by_name[name]["id"])
            continue
        payload = {
            "name": name,
            "dataType": dtype,
            "placeholder": placeholder,
            "model": "contact",
        }
        code, body = curl(
            "POST",
            f"https://services.leadconnectorhq.com/locations/{LOC}/customFields",
            data=payload,
        )
        print("create field", name, code, body[:180].replace("\n", " "))
        if code.startswith("2"):
            data = json.loads(body)
            fid = (data.get("customField") or data.get("field") or data).get("id")
            created[name] = fid
        time.sleep(0.15)

    # refresh map
    code, body = curl("GET", f"https://services.leadconnectorhq.com/locations/{LOC}/customFields")
    fields = json.loads(body).get("customFields") or []
    fmap = {f["name"]: f["id"] for f in fields}
    (AUDIT / "fields-map.json").write_text(json.dumps(fmap, ensure_ascii=False, indent=2), encoding="utf-8")
    return fmap


def update_calendars():
    specs = {
        CAL["fernanda"]: {
            "name": "US - Dra. Fernanda",
            "description": (
                "Ultrassonografia (abdominal, cervical, microbolhas, cistocentese). "
                "Profissional preferencial: Dra. Fernanda. Seg-sex 8:30-18:00. "
                "Microbolhas: apenas quartas e quintas. Mesma sala do ecocardiograma."
            ),
            "slotDuration": 30,
            "openHours": hours(range(1, 6), 8, 30, 18, 0),
            "autoConfirm": True,
            "eventTitle": "{{contact.pet_1_nome}} | US Fernanda | {{contact.procedimento_interesse}}",
        },
        CAL["luciana"]: {
            "name": "US - Dra. Luciana",
            "description": (
                "Ultrassonografia (abdominal, cervical, microbolhas, cistocentese). "
                "Fallback quando Dra. Fernanda indisponível ou a pedido do cliente. "
                "Seg-sex 8:30-18:00. Microbolhas: quartas e quintas."
            ),
            "slotDuration": 30,
            "openHours": hours(range(1, 6), 8, 30, 18, 0),
            "autoConfirm": True,
            "eventTitle": "{{contact.pet_1_nome}} | US Luciana | {{contact.procedimento_interesse}}",
        },
        CAL["eco"]: {
            "name": "Ecocardiograma",
            "description": (
                "Ecocardiograma. Sem preparo específico. Horário típico 9:00-15:00. "
                "Mesma sala da ultrassonografia — verificar conflito. "
                "Pré-anestésico obrigatório para pacientes >6 anos."
            ),
            "slotDuration": 30,
            "openHours": hours(range(1, 6), 9, 0, 15, 0),
            "autoConfirm": True,
            "eventTitle": "{{contact.pet_1_nome}} | Ecocardiograma | {{contact.procedimento_interesse}}",
        },
        CAL["ecg"]: {
            "name": "Eletrocardiograma",
            "description": "Eletrocardiograma. Sem preparo específico. Seg-sex 9:00-16:00.",
            "slotDuration": 30,
            "openHours": hours(range(1, 6), 9, 0, 16, 0),
            "autoConfirm": True,
            "eventTitle": "{{contact.pet_1_nome}} | Eletrocardiograma",
        },
        CAL["rx"]: {
            "name": "Raio-X",
            "description": (
                "Raio-X / radiografia. Seg-sex 8:30-18:00; sábado 8:00-13:00. "
                "Também usar para uretrografia/uretrocistografia e urografia excretora quando aplicável."
            ),
            "slotDuration": 30,
            "openHours": merge_hours(
                hours(range(1, 6), 8, 30, 18, 0),
                hours([6], 8, 0, 13, 0),
            ),
            "autoConfirm": True,
            "eventTitle": "{{contact.pet_1_nome}} | Raio-X | {{contact.procedimento_interesse}}",
        },
        CAL["tomo"]: {
            "name": "Tomografia",
            "description": (
                "Tomografia computadorizada (com anestesia). Urgência. "
                "Seg-sex 8:30-18:00; sábado 8:00-13:00. Exige exames pré-anestésicos."
            ),
            "slotDuration": 90,
            "openHours": merge_hours(
                hours(range(1, 6), 8, 30, 18, 0),
                hours([6], 8, 0, 13, 0),
            ),
            "autoConfirm": True,
            "eventTitle": "{{contact.pet_1_nome}} | Tomografia | {{contact.procedimento_interesse}}",
        },
        CAL["endo"]: {
            "name": "Endoscopia Rinoscopia Broncoscopia",
            "description": (
                "Endoscopia digestiva alta/baixa, rinoscopia, broncoscopia e combos. "
                "Preferencialmente quartas 10:00-15:00. Com anestesia. Preparo específico por exame."
            ),
            "slotDuration": 120,
            "openHours": hours([3], 10, 0, 15, 0),
            "autoConfirm": False,
            "eventTitle": "{{contact.pet_1_nome}} | Endo/Rino/Bronco | {{contact.procedimento_interesse}}",
        },
        CAL["cintilo"]: {
            "name": "Cintilografia",
            "description": (
                "Cintilografias (renal, tireoide, óssea, shunt, paratireoide). "
                "Preferência segundas e quintas; horários 9:30, 10:00, 13:00, 13:30, 15:30. "
                "Exige sinal. Cancelamento com regras de reembolso."
            ),
            "slotDuration": 90,
            "openHours": hours([1, 4], 9, 30, 16, 0),
            "autoConfirm": False,
            "eventTitle": "{{contact.pet_1_nome}} | Cintilografia | {{contact.procedimento_interesse}}",
        },
        CAL["radio"]: {
            "name": "Radioiodoterapia",
            "description": (
                "Radioiodoterapia felina/canina. Preferência terças. "
                "Horários 9:30-15:30. Isolamento. Exige sinal e preparo específico."
            ),
            "slotDuration": 90,
            "openHours": hours([2], 9, 30, 16, 0),
            "autoConfirm": False,
            "eventTitle": "{{contact.pet_1_nome}} | Radioiodoterapia",
        },
        CAL["prereserva"]: {
            "name": "Pre-reserva Interna",
            "description": (
                "Fallback / pré-reserva interna quando o calendário específico estiver indisponível "
                "ou o exame exigir confirmação humana (contrastes urinários, casos complexos). "
                "Seg-sex 8:30-18:00; sábado 8:00-14:00."
            ),
            "slotDuration": 30,
            "openHours": merge_hours(
                hours(range(1, 6), 8, 30, 18, 0),
                hours([6], 8, 0, 14, 0),
            ),
            "autoConfirm": False,
            "eventTitle": "{{contact.pet_1_nome}} | Pre-reserva | {{contact.procedimento_interesse}}",
        },
    }

    for cid, spec in specs.items():
        payload = {
            "name": spec["name"],
            "description": spec["description"],
            "slotDuration": spec["slotDuration"],
            "slotDurationUnit": "mins",
            "slotInterval": 30 if spec["slotDuration"] <= 30 else 30,
            "slotIntervalUnit": "mins",
            "openHours": spec["openHours"],
            "autoConfirm": spec["autoConfirm"],
            "eventTitle": spec["eventTitle"],
            "allowReschedule": True,
            "allowCancellation": True,
        }
        code, body = curl("PUT", f"https://services.leadconnectorhq.com/calendars/{cid}", data=payload)
        print("calendar", spec["name"], code, body[:160].replace("\n", " "))
        time.sleep(0.2)


def create_field_actions(fmap: dict):
    # Get current actions from agent
    code, body = curl("GET", f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}")
    agent = json.loads(body).get("agent", json.loads(body))
    existing = agent.get("actions") or []
    # Delete existing updateContactField to recreate cleanly? Better: list by GET each and skip duplicates by name.
    # We'll fetch each action detail.
    existing_field_names = set()
    for a in existing:
        if a.get("type") != "updateContactField":
            continue
        aid = a["id"]
        code, body = curl(
            "GET",
            f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}/actions/{aid}",
            version="2021-04-15",
        )
        if code.startswith("2"):
            data = json.loads(body).get("data") or {}
            existing_field_names.add(data.get("name") or "")

    defs = [
        ("Nome Pet Ativo", "Pet Ativo Nome", "Registrar o nome do animalzinho em atendimento nesta conversa. Se houver vários pets, confirmar qual e salvar aqui também.", ["Thor", "Mel", "Luna", "Bob"]),
        ("Pet 1 Nome", "Pet 1 Nome", "Registrar o nome do pet 1 (principal/cadastrado).", ["Thor", "Mel", "Luna", "Bob"]),
        ("Pet 1 Especie", "Pet 1 Especie", "Registrar espécie do pet 1: cão/canino ou gato/felino.", ["cão", "gato", "canino", "felino"]),
        ("Pet 1 Raca", "Pet 1 Raca", "Registrar a raça do pet 1.", ["SRD", "Golden Retriever", "Persa", "Poodle"]),
        ("Pet 1 Sexo", "Pet 1 Sexo", "Registrar sexo do pet 1: macho ou fêmea.", ["macho", "fêmea", "macho castrado"]),
        ("Pet 1 Peso", "Pet 1 Peso", "Registrar peso do pet 1 em kg (número ou com kg).", ["4kg", "12", "25 kg", "8,5"]),
        ("Pet 1 Castrado", "Pet 1 Castrado", "Registrar se o pet 1 é castrado: sim ou não.", ["sim", "não", "castrado", "inteiro"]),
        ("Pet 1 Nascimento", "Pet 1 Nascimento", "Registrar data de nascimento do pet 1 (DD/MM/AAAA) ou idade aproximada convertida quando possível.", []),
        ("Pet 2 Nome", "Pet 2 Nome", "Registrar nome do pet 2 quando multi-pet.", ["Nina", "Toby"]),
        ("Pet 2 Especie", "Pet 2 Especie", "Espécie do pet 2.", ["cão", "gato"]),
        ("Pet 2 Raca", "Pet 2 Raca", "Raça do pet 2.", ["SRD", "Siames"]),
        ("Pet 2 Sexo", "Pet 2 Sexo", "Sexo do pet 2.", ["macho", "fêmea"]),
        ("Pet 2 Peso", "Pet 2 Peso", "Peso do pet 2.", ["3kg", "10"]),
        ("Pet 2 Castrado", "Pet 2 Castrado", "Pet 2 castrado? sim/não.", ["sim", "não"]),
        ("Pet 3 Nome", "Pet 3 Nome", "Registrar nome do pet 3 quando multi-pet.", ["Duque"]),
        ("Pet 3 Especie", "Pet 3 Especie", "Espécie do pet 3.", ["cão", "gato"]),
        ("Pet 3 Raca", "Pet 3 Raca", "Raça do pet 3.", ["SRD"]),
        ("Pet 3 Sexo", "Pet 3 Sexo", "Sexo do pet 3.", ["macho", "fêmea"]),
        ("Pet 3 Peso", "Pet 3 Peso", "Peso do pet 3.", ["5kg"]),
        ("Pet 3 Castrado", "Pet 3 Castrado", "Pet 3 castrado? sim/não.", ["sim", "não"]),
        ("CPF Tutor", "CPF Tutor", "Registrar CPF do responsável pelo paciente.", ["123.456.789-00", "12345678900"]),
        ("Email Tutor", "Email Tutor", "Registrar e-mail do responsável.", ["tutor@email.com"]),
        ("Cidade Tutor", "Cidade Tutor", "Registrar cidade do responsável.", ["Rio de Janeiro", "Barra da Tijuca", "Recreio"]),
        ("CEP Tutor", "CEP Tutor", "Registrar CEP do responsável.", ["22640-102", "22000-000"]),
        ("Ja Paciente", "Ja Paciente", "Registrar se já é paciente da Gamma Vet: sim ou não.", ["sim", "não", "já sou cliente", "primeira vez"]),
        ("Procedimento Interesse", "Procedimento Interesse", "Registrar o exame/procedimento desejado (ultrassom, tomo, cintilo, eco, etc.).", ["ultrassonografia abdominal", "tomografia", "cintilografia renal", "ecocardiograma"]),
        ("Periodo Preferido", "Periodo Preferido", "Registrar preferência de período: apenas manhã ou tarde (sem noite).", ["manhã", "tarde", "de manhã", "à tarde"]),
        ("Datas Preferidas", "Datas Preferidas", "Registrar datas ou dias preferidos mencionados pelo responsável.", ["amanhã de manhã", "quarta-feira", "semana que vem"]),
        ("Profissional Preferido", "Profissional Preferido", "Registrar profissional preferido (ex.: Dra. Fernanda, Dra. Luciana).", ["Fernanda", "Luciana", "Dra. Fernanda"]),
        ("Plano Saude", "Plano Saude", "Registrar plano de saúde pet informado (Pet Love, Au Happy, particular, nenhum).", ["Pet Love", "Au Happy", "particular", "não tenho"]),
        ("Motivo Exame", "Motivo Exame", "Registrar motivo clínico do exame informado pelo responsável/vet.", ["check-up", "vômito", "suspeita de nódulo"]),
        ("Medicacoes em Uso", "Medicacoes em Uso", "Registrar medicações em uso do animalzinho.", ["nenhuma", "metimazol", "gabapentina"]),
        ("Vet Solicitante Nome", "Vet Solicitante Nome", "Registrar nome do médico veterinário solicitante.", ["Dr. João", "Dra. Ana"]),
        ("Vet Solicitante Contato", "Vet Solicitante Contato", "Registrar telefone/WhatsApp/e-mail do veterinário solicitante.", ["21999990000"]),
        ("Status Pedido Medico", "Status Pedido Medico", "Registrar status do pedido médico: pendente, recebido_foto, recebido_pdf, analisado.", ["pendente", "recebido_foto", "recebido_pdf"]),
        ("URL Pedido Medico", "URL Pedido Medico", "Quando houver link/URL do pedido médico anexado, registrar.", ["https://..."]),
        ("Nivel Urgencia", "Nivel Urgencia", "Registrar nível: normal, prioridade ou urgencia (tomo e cintilo renal = urgencia).", ["normal", "prioridade", "urgencia"]),
        ("Setor Destino", "Setor Destino", "Registrar setor: US, Eco, ECG, RX, TC, Endoscopia, Cintilografia, Radioiodo, Contraste.", ["US", "TC", "Cintilografia"]),
        ("Valor Informado", "Valor Informado", "Registrar o valor numérico informado ao cliente (sem R$).", ["400", "1500", "1750"]),
        ("Sinal Valor", "Sinal Valor", "Registrar valor do sinal quando aplicável (cintilos/radioiodo).", ["200", "250"]),
        ("Taxa Execucao", "Taxa Execucao", "Registrar taxa/valor de execução quando separado do sinal.", ["950", "1500"]),
    ]

    created = []
    for action_name, field_name, desc, examples in defs:
        if action_name in existing_field_names:
            print("skip action", action_name)
            continue
        fid = fmap.get(field_name)
        if not fid:
            print("MISSING FIELD", field_name)
            continue
        details = {
            "contactFieldId": fid,
            "description": desc,
            "contactUpdateExamples": examples,
        }
        # DATE/NUM fields may not want examples required - API said examples not required for date/monetary
        payload = {
            "type": "updateContactField",
            "name": action_name,
            "details": details,
        }
        code, body = curl(
            "POST",
            f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}/actions",
            data=payload,
            version="2021-04-15",
        )
        print("field action", action_name, code, body[:140].replace("\n", " "))
        if code.startswith("2"):
            created.append(action_name)
        time.sleep(0.12)
    print("created field actions", len(created))
    return created


def update_booking_action():
    details = {
        "calendarIds": [
            {
                "id": CAL["fernanda"],
                "triggerCondition": "Ultrassonografia / US / abdominal / cervical / microbolhas / cistocentese quando profissional for Dra. Fernanda ou preferência padrão de US",
            },
            {
                "id": CAL["luciana"],
                "triggerCondition": "Ultrassonografia / US quando Dra. Fernanda indisponível ou cliente pedir Dra. Luciana",
            },
            {
                "id": CAL["eco"],
                "triggerCondition": "Ecocardiograma / eco / pré-anestésico cardíaco",
            },
            {
                "id": CAL["ecg"],
                "triggerCondition": "Eletrocardiograma / eletro / ECG",
            },
            {
                "id": CAL["rx"],
                "triggerCondition": "Raio-X / radiografia / RX / uretrografia / uretrocistografia / urografia excretora",
            },
            {
                "id": CAL["tomo"],
                "triggerCondition": "Tomografia / TC / tomografia computadorizada",
            },
            {
                "id": CAL["endo"],
                "triggerCondition": "Endoscopia / colonoscopia / rinoscopia / broncoscopia / endoscopia digestiva",
            },
            {
                "id": CAL["cintilo"],
                "triggerCondition": "Cintilografia / medicina nuclear diagnóstica (renal, tireoide, óssea, shunt, paratireoide)",
            },
            {
                "id": CAL["radio"],
                "triggerCondition": "Radioiodoterapia / iodo radioativo / tratamento tireoide",
            },
            {
                "id": CAL["prereserva"],
                "triggerCondition": "Pré-reserva / fallback / exame sem calendário específico / confirmação humana necessária",
            },
        ],
        "calendarActionType": "multiple",
        "aiDescription": (
            "Agenda exames da Gamma Vet no calendário correto conforme o procedimento. "
            "US: Fernanda (preferencial) ou Luciana. Eco, ECG, RX, Tomografia, Endoscopia/Rino/Bronco, "
            "Cintilografia e Radioiodoterapia têm calendários próprios. Use Pré-reserva Interna como fallback. "
            "Microbolhas só qua/qui. Antes de oferecer horários, coletar dados mínimos e consultar disponibilidade real."
        ),
        "fallbackCalendar": True,
        "fallbackCalendarId": CAL["prereserva"],
        "onlySendLink": False,
        "triggerWorkflow": False,
        "workflowIds": None,
        "sleepAfterBooking": False,
        "sleepTimeUnit": None,
        "sleepTime": None,
        "transferBot": False,
        "transferEmployee": None,
        "rescheduleEnabled": True,
        "cancelEnabled": True,
    }
    payload = {
        "type": "appointmentBooking",
        "name": "Agendamento Gamma Vet",
        "details": details,
    }
    code, body = curl(
        "PUT",
        f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}/actions/{BOOKING_ACTION}",
        data=payload,
        version="2021-04-15",
    )
    print("booking update", code, body[:400].replace("\n", " "))
    return code


def create_followup():
    # Check if already exists
    code, body = curl("GET", f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}")
    agent = json.loads(body).get("agent", json.loads(body))
    for a in agent.get("actions") or []:
        if a.get("type") == "advancedFollowup":
            print("followup already exists", a.get("id"))
            return a.get("id")

    working = []
    for d in range(1, 7):  # Mon-Sat
        working.append(
            {
                "dayOfTheWeek": d,
                "intervals": [{"startHour": 7, "startMinute": 0, "endHour": 20, "endMinute": 0}],
            }
        )
    working.append(
        {
            "dayOfTheWeek": 0,
            "intervals": [{"startHour": 10, "startMinute": 0, "endHour": 20, "endMinute": 0}],
        }
    )

    msgs = [
        (1, 15, "minutes", "Olá! Vi sua mensagem sobre o exame do seu pet. Posso seguir te ajudando a reunir as informações para agendarmos?"),
        (2, 1, "hours", "Oi! Só para não perder o fio — você gostaria de agendar algum exame na Gamma Vet? Estou à disposição."),
        (3, 2, "hours", "Quando puder me diga qual exame deseja e o nome do animalzinho. Assim avanço com o agendamento."),
        (4, 7, "hours", "Passando para saber se ainda posso ajudar com o agendamento. Se preferir, nossa equipe humana também pode te atender."),
        (5, 12, "hours", "Último retorno por aqui: se quiser retomar o agendamento na Gamma Vet, é só responder esta conversa."),
    ]
    seq = []
    for i, t, unit, msg in msgs:
        seq.append(
            {
                "id": i,
                "followupTime": t,
                "followupTimeUnit": unit,
                "aiEnabledMessage": False,
                "customMessage": msg,
                "triggerWorkflow": False,
                "workflowId": None,
            }
        )

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
        version="2021-04-15",
    )
    print("followup", code, body[:500].replace("\n", " "))
    return code


def create_handover_and_stop():
    code, body = curl("GET", f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}")
    agent = json.loads(body).get("agent", json.loads(body))
    types = {a.get("type") for a in (agent.get("actions") or [])}

    if "humanHandOver" not in types:
        payload = {
            "type": "humanHandOver",
            "name": "Transferir para humano",
            "details": {
                "enabled": True,
                "handoverType": "contactRequest",
                "triggerCondition": (
                    "Quando o responsável pedir atendimento humano, ou houver PDF de pedido médico, "
                    "dúvida sem resposta clara na base, urgência que precise da equipe, "
                    "ou cancelamento de cintilografia/radioiodo com regra de sinal."
                ),
                "examples": [
                    "quero falar com uma pessoa",
                    "pode me transferir",
                    "atendimento humano",
                    "falar com a recepção",
                    "falar com agendamento",
                ],
                "skipAssignToUser": True,
                "createTask": True,
                "reactivateEnabled": True,
                "sleepTimeUnit": "hours",
                "sleepTime": 24,
                "finalMessage": (
                    "Vou te transferir para nossa equipe humana da Gamma Vet. Em instantes alguém dá continuidade, ok?"
                ),
                "tags": ["aguardando"],
            },
        }
        code, body = curl(
            "POST",
            f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}/actions",
            data=payload,
            version="2021-04-15",
        )
        print("handover", code, body[:400].replace("\n", " "))
    else:
        print("handover exists")

    if "stopBot" not in types:
        payload = {
            "type": "stopBot",
            "name": "Encerrar conversa",
            "details": {
                "enabled": True,
                "stopBotDetectionType": "Custom",
                "stopBotTriggerCondition": "Quando o responsável disser que não precisa mais de ajuda ou encerrar a conversa.",
                "stopBotExamples": ["obrigado era só isso", "não preciso mais", "pode encerrar", "tchau", "até mais"],
                "reactivateEnabled": True,
                "sleepTimeUnit": "hours",
                "sleepTime": 12,
                "finalMessage": "Perfeito! Qualquer coisa, a Gamma Vet está à disposição. Obrigada pela preferência.",
                "tags": [],
            },
        }
        code, body = curl(
            "POST",
            f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}/actions",
            data=payload,
            version="2021-04-15",
        )
        print("stopBot", code, body[:400].replace("\n", " "))
    else:
        print("stopBot exists")


def update_agent_prompt():
    prompt = (OUT / "system-prompt-completo.md").read_text(encoding="utf-8")
    payload = {
        "name": "Assistente Gamma Vet",
        "isPrimary": True,
        "mode": "off",
        "instructions": prompt,
        "goal": (
            "Conduzir o responsável até o agendamento do exame: coletar dados do tutor e do pet, "
            "validar escopo/preparo/plano/valor pela base, consultar agenda real no calendário correto, "
            "oferecer horários e confirmar no sistema. Em dúvida ou exceção, transferir para humano."
        ),
        "personality": (
            "Formal porém acolhedor. Use animalzinho, seu pet e responsável pelo paciente. "
            "Sempre se apresente como assistente virtual da Gamma Vet. Agradeça a preferência. "
            "Respostas curtas, claras, estilo WhatsApp, em português do Brasil."
        ),
        "knowledgeBaseIds": [KB],
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
    print("agent prompt", code, body[:350].replace("\n", " "))
    return code


def final_snapshot():
    code, body = curl("GET", f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}")
    agent = json.loads(body).get("agent", json.loads(body))
    (OUT / "agent-completo.json").write_text(json.dumps(agent, ensure_ascii=False, indent=2), encoding="utf-8")
    actions = []
    for a in agent.get("actions") or []:
        aid = a["id"]
        c2, b2 = curl(
            "GET",
            f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}/actions/{aid}",
            version="2021-04-15",
        )
        if c2.startswith("2"):
            actions.append(json.loads(b2).get("data"))
        else:
            actions.append(a)
    (OUT / "actions-completo.json").write_text(json.dumps(actions, ensure_ascii=False, indent=2), encoding="utf-8")
    print("FINAL actions:")
    for a in actions:
        print("-", a.get("type"), "|", a.get("name"), "|", a.get("id"))
    print("KB", agent.get("knowledgeBaseIds"))
    print("prompt_len", len(agent.get("instructions") or ""))
    print("goal", (agent.get("goal") or "")[:140])


def main():
    fmap = ensure_custom_fields()
    update_calendars()
    create_field_actions(fmap)
    update_booking_action()
    create_followup()
    create_handover_and_stop()
    update_agent_prompt()
    final_snapshot()


if __name__ == "__main__":
    main()
