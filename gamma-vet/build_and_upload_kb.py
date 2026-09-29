#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Gera documento KB a partir do Excel e sobe FAQs + liga no agente Gamma Vet."""

from __future__ import annotations

import json
import re
import subprocess
import time
from pathlib import Path

TOKEN = "pit-7f81ae98-ee67-4025-a4d6-1c4f8b5bcef7"
LOC = "MhplIQf1baCvRBNGPTOj"
KB = "yissd6WHhYpyP4yw9TlL"
AGENT = "nEndeX5NE4uDJG7414RF"

OUT = Path(r"c:\Users\GC1\Desktop\Automação GHL\gamma-vet")
RAW_PATH = Path(r"c:\Users\GC1\Desktop\Automação GHL\gamma-vet-xlsx-raw.json")
OUT.mkdir(parents=True, exist_ok=True)


def curl(method: str, url: str, data=None, form=None):
    cmd = [
        "curl.exe",
        "-s",
        "-w",
        "\nHTTP:%{http_code}",
        "-X",
        method,
        url,
        "-H",
        f"Authorization: Bearer {TOKEN}",
        "-H",
        "Version: 2021-07-28",
        "-H",
        "Accept: application/json",
        "-H",
        "User-Agent: Mozilla/5.0",
    ]
    if data is not None:
        tmp = OUT / "req.json"
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


def build_docs(raw: dict):
    headers = raw["Procedimentos"][0]
    procs = []
    md: list[str] = []
    md.append("# Base de Conhecimento — Gamma Vet (Procedimentos Completos)")
    md.append("")
    md.append("Fonte: Procedimentos_GammaVet.xlsx — textos preservados.")
    md.append("")
    md.append("## Quem somos")
    md.append(
        "O Gamma Vet é um centro de diagnóstico por imagem avançado. "
        "Pioneiro na medicina nuclear veterinária no Brasil. Localizado na Barra da Tijuca, "
        "no Shopping Città Vet (shopping aberto, estacionamento privado, Pet Friendly), "
        "a cerca de 15 minutos da Zona Sul e do Recreio dos Bandeirantes."
    )
    md.append("")
    md.append("## Horário de funcionamento")
    md.append("- Segunda a sexta: 8:30 às 18:00")
    md.append("- Sábado: 8:00 às 14:00 (alguns exames até 13:00)")
    md.append("- Domingo: fechado")
    md.append("- Preferência de período do tutor: apenas manhã ou tarde (sem noite)")
    md.append("")
    md.append("## Exames que realizamos")
    md.append(
        "Tomografia computadorizada, cintilografia, ultrassonografia, "
        "ultrassonografia com contraste por microbolhas, ecocardiografia, "
        "eletrocardiografia, endoscopia, broncoscopia, rinoscopia, raio-X, "
        "radioiodoterapia, cistocentese, uretrografia/uretrocistografia, urografia excretora."
    )
    md.append("")
    md.append("## Exames que NÃO realizamos")
    md.append(
        "Ressonância magnética e quaisquer exames fora da lista acima. "
        "Nestes casos: agradecer, informar que não realizamos, listar o que fazemos "
        "e transferir/encerrar com educação."
    )
    md.append("")
    md.append("## PIX / sinal")
    md.append("- Chave PIX: CNPJ 43608666000130")
    md.append("- 5% desconto à vista (pix ou dinheiro) quando constar no procedimento")
    md.append("- Exames com sinal: agendamento confirmado somente após pagamento do sinal")
    md.append("")
    md.append("---")
    md.append("")
    md.append("# Procedimentos operacionais")
    md.append("")

    for row in raw["Procedimentos"][1:]:
        if not row or not str(row[0]).strip():
            continue
        row = list(row)
        while len(row) < len(headers):
            row.append("")
        data = {headers[i]: (row[i] or "").strip() for i in range(len(headers))}
        procs.append(data)
        name = data["Procedimento"].replace("\n", " ").strip()
        md.append(f"## {name}")
        md.append("")
        for h in headers[1:]:
            val = data.get(h, "").strip()
            if not val:
                continue
            md.append(f"**{h}:**")
            md.append(val)
            md.append("")
        md.append("---")
        md.append("")

    md.append("# Regras de comunicação")
    md.append("")
    for row in raw["regras comunicação"]:
        t = (row[0] or "").strip() if row else ""
        if t:
            md.append(t)
            md.append("")

    md.append("---")
    md.append("")
    md.append("# Descritivo sobre os exames")
    md.append("")
    for row in raw["descritivo sobre os exames"][1:]:
        if not row or not str(row[0]).strip():
            continue
        row = list(row)
        while len(row) < 4:
            row.append("")
        nome, oque, serve, indicado = [(c or "").strip() for c in row[:4]]
        md.append(f"## {nome.replace(chr(10), ' ')}")
        md.append("")
        md.append(f"**O que é:** {oque}")
        md.append("")
        md.append(f"**Para que serve:** {serve}")
        md.append("")
        md.append(f"**Para quem é indicado:** {indicado}")
        md.append("")
        md.append("---")
        md.append("")

    text = "\n".join(md)
    (OUT / "Procedimentos_GammaVet_KB.md").write_text(text, encoding="utf-8")
    (OUT / "Procedimentos_GammaVet_KB.txt").write_text(text, encoding="utf-8")
    return text, procs, headers


def build_faqs(raw: dict, procs: list[dict], headers: list[str]):
    faqs = []

    def add_faq(q: str, a: str):
        q = re.sub(r"\s+", " ", q).strip()
        a = a.strip()
        if q and a:
            faqs.append({"question": q[:500], "answer": a[:4500]})

    add_faq(
        "Quem é o Gamma Vet? Onde fica?",
        "O Gamma Vet é um centro de diagnóstico por imagem avançado, pioneiro na medicina nuclear "
        "veterinária no Brasil. Localizado na Barra da Tijuca, no Shopping Città Vet "
        "(shopping aberto, estacionamento privado e Pet Friendly), a cerca de 15 minutos da Zona Sul "
        "e do Recreio dos Bandeirantes. Objetivo: oferecer o que há de melhor e mais inovador no "
        "diagnóstico de imagem veterinário para qualidade de vida e longevidade dos pacientes.",
    )
    add_faq(
        "Qual o horário de funcionamento do Gamma Vet?",
        "Horário da clínica:\n"
        "- Segunda a sexta: 8:30 às 18:00\n"
        "- Sábado: 8:00 às 14:00 (alguns exames têm horário próprio; vários até 13:00)\n"
        "- Domingo: fechado\n"
        "Cada exame tem particularidade de agenda — a confirmação definitiva de horário é feita "
        "pela equipe humana de agendamento.\n"
        "Preferência do tutor: apenas manhã ou tarde (sem noite).",
    )
    add_faq(
        "Quais exames o Gamma Vet realiza?",
        "Realizamos: tomografia computadorizada, cintilografia, ultrassonografia, ultrassonografia "
        "com contraste por microbolhas, ecocardiografia, eletrocardiografia, endoscopia, broncoscopia, "
        "rinoscopia, raio-X, radioiodoterapia, cistocentese, uretrografia/uretrocistografia e urografia excretora.\n"
        "Diferenciais: únicos no Brasil com cintilografia para cães e gatos; únicos no Rio de Janeiro "
        "com ultrassonografia com contraste por microbolhas.",
    )
    add_faq(
        "O Gamma Vet faz ressonância magnética?",
        "Não. Não realizamos ressonância. Agradecemos o contato e informamos os exames que realizamos "
        "(tomografia, cintilografia, ultrassonografia e microbolhas, eco, eletro, endoscopia, "
        "broncoscopia, rinoscopia, raio-X, radioiodoterapia etc.). Esperamos poder atendê-los em outra oportunidade.",
    )
    add_faq(
        "Qual o tom de voz e regras de atendimento da Gamma Vet?",
        "Padrão formal porém acolhedor. Usar: animalzinho, seu pet, responsável pelo paciente. "
        "Sempre agradecer a preferência.\n"
        "Receber de forma receptiva. Perguntar como podemos ajudar. Se o exame estiver no escopo: "
        "solicitar pedido médico e preferência de data/horário; se já for paciente, chamar pelo nome "
        "do responsável; se novo, pedir ficha cadastral e transferir para agendamento humano.\n"
        "Após agendamento humano: enviar confirmação e preparo (se houver). No primeiro contato NÃO "
        "enviar orçamento completo sem necessidade.\n"
        "Confirmação D-1: lembrete do agendamento + preparo (não pedir confirmação como dúvida).\n"
        "Reagendar/cancelar: transferir para agendamento humano.\n"
        "Se a resposta não estiver clara na base: transferir para atendimento humano.",
    )
    add_faq(
        "Qual a política de cancelamento e sinal?",
        "Cintilografias exigem sinal para confirmação (reforçado pelo agendamento humano).\n"
        "Regra geral: cancelar com antecedência adequada (24h ou 48h conforme o exame) para retorno "
        "da taxa; caso contrário o sinal não é reembolsado.\n"
        "Demais exames: cancelamento pode acontecer sem custo.\n"
        "Chave PIX (quando sinal aplicável): CNPJ 43608666000130. 5% desconto à vista (pix ou dinheiro) "
        "quando constar no procedimento.",
    )
    add_faq(
        "Quais dados são necessários para agendamento?",
        "Dados típicos: nome do animal, peso, data de nascimento, sexo/espécie/raça, castrado?, "
        "plano de saúde?, nome do responsável, celular/CPF/e-mail, cidade/CEP, contato do médico "
        "veterinário solicitante, motivo do exame, medicações em uso, requisição do médico veterinário. "
        "Exames com anestesia também pedem exames pré-anestésicos.",
    )

    for d in procs:
        name = d["Procedimento"].replace("\n", " ").strip()
        parts = []
        for h in headers[1:]:
            v = d.get(h, "").strip()
            if v:
                parts.append(f"{h}:\n{v}")
        add_faq(f"Procedimento {name}: preparo, agenda, plano e valor", "\n\n".join(parts))
        if d.get("Preparo do Paciente", "").strip():
            add_faq(f"Qual o preparo para {name}?", d["Preparo do Paciente"].strip())
        val = d.get("Valor", "").strip()
        if val:
            obs = d.get("Observações Importantes", "").strip()
            add_faq(
                f"Qual o valor de {name}?",
                f"Valor de {name}: {val}" + (f"\nObservações: {obs}" if obs else ""),
            )
        agenda_bits = []
        for h in ["Agenda", "Dias", "Horários"]:
            if d.get(h, "").strip():
                agenda_bits.append(f"{h}: {d[h].strip()}")
        if agenda_bits:
            obs = d.get("Observações Importantes", "").strip()
            add_faq(
                f"Quando e onde é feito o exame {name}?",
                "\n".join(agenda_bits) + (f"\nObservações: {obs}" if obs else ""),
            )
        plano = d.get("Aceita plano de saúde", "").strip()
        if plano:
            add_faq(
                f"{name} aceita plano de saúde?",
                f"Aceita plano: {plano}. Qual: {d.get('Qual', '').strip() or 'n/a'}",
            )

    for row in raw["descritivo sobre os exames"][1:]:
        if not row or not str(row[0]).strip():
            continue
        row = list(row)
        while len(row) < 4:
            row.append("")
        nome, oque, serve, indicado = [(c or "").strip() for c in row[:4]]
        nome = nome.replace("\n", " ")
        add_faq(
            f"O que é {nome}? Para que serve?",
            f"O que é: {oque}\n\nPara que serve: {serve}\n\nPara quem é indicado: {indicado}",
        )

    seen = set()
    uniq = []
    for f in faqs:
        k = f["question"].lower()
        if k in seen:
            continue
        seen.add(k)
        uniq.append(f)
    return uniq


def clear_existing_faqs():
    code, body = curl(
        "GET",
        f"https://services.leadconnectorhq.com/knowledge-base/faqs?locationId={LOC}&knowledgeBaseId={KB}&limit=100",
    )
    print("list faqs", code)
    data = json.loads(body) if body.strip().startswith("{") else {}
    faqs = data.get("faqs") or []
    print("existing", len(faqs))
    for f in faqs:
        fid = f.get("id") or f.get("_id")
        if not fid:
            continue
        # try delete endpoints
        for path in [
            f"/knowledge-base/faqs/{fid}",
            f"/knowledge-base/faq/{fid}",
        ]:
            c, b = curl(
                "DELETE",
                f"https://services.leadconnectorhq.com{path}?locationId={LOC}&knowledgeBaseId={KB}",
            )
            print("delete", fid, path, c, b[:120].replace("\n", " "))
            if c.startswith("2"):
                break


def upload_faqs(faqs: list[dict]):
    ok = 0
    fail = 0
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
            print("FAIL FAQ", i, code, body[:200].replace("\n", " "))
        if i % 10 == 0:
            print(f"progress {i}/{len(faqs)} ok={ok} fail={fail}")
            time.sleep(0.2)
    print(f"FAQ upload done ok={ok} fail={fail}")
    return ok, fail


def try_upload_file(doc_path: Path):
    # Probe file upload variants
    variants = [
        (
            "POST",
            f"https://services.leadconnectorhq.com/knowledge-base/files?locationId={LOC}&knowledgeBaseId={KB}",
            [f"file=@{doc_path}", f"locationId={LOC}", f"knowledgeBaseId={KB}", "name=Procedimentos_GammaVet_KB"],
        ),
        (
            "POST",
            "https://services.leadconnectorhq.com/knowledge-base/files",
            [f"file=@{doc_path}", f"locationId={LOC}", f"knowledgeBaseId={KB}"],
        ),
    ]
    for method, url, form in variants:
        code, body = curl(method, url, form=form)
        print("file upload", code, body[:300].replace("\n", " "))
        if code.startswith("2"):
            return True
    return False


def rename_kb():
    for method, payload in [
        (
            "PUT",
            {"name": "Base Gamma Vet — Procedimentos V1", "locationId": LOC},
        ),
        (
            "PUT",
            {"name": "Base Gamma Vet — Procedimentos V1"},
        ),
        (
            "PATCH",
            {"name": "Base Gamma Vet — Procedimentos V1", "locationId": LOC},
        ),
    ]:
        code, body = curl(
            method,
            f"https://services.leadconnectorhq.com/knowledge-base/{KB}",
            data=payload,
        )
        print("rename", method, code, body[:200].replace("\n", " "))
        if code.startswith("2"):
            return True
    return False


def link_kb_and_update_prompt(prompt_path: Path):
    instructions = prompt_path.read_text(encoding="utf-8")
    # GET current agent
    code, body = curl("GET", f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}")
    print("get agent", code)
    agent = json.loads(body)
    if "agent" in agent:
        agent = agent["agent"]

    payload = {
        "locationId": LOC,
        "isPrimary": True,
        "mode": "off",
        "channels": ["WebChat"],
        "instructions": instructions,
        "goal": (
            "Coletar dados do responsável e do pet, preferência manhã/tarde, procedimento e pedido médico; "
            "informar preparo, pré-requisitos, planos e valores quando constarem na base de conhecimento; "
            "transferir para a equipe humana agendar. NÃO confirmar horário definitivo nem marcar sozinha."
        ),
        "personality": (
            "Formal porém acolhedor. Use animalzinho, seu pet e responsável pelo paciente. "
            "Sempre se apresente como assistente virtual da Gamma Vet. Agradeça a preferência. "
            "Respostas curtas, claras, em português do Brasil."
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
    }
    code, body = curl(
        "PUT",
        f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}",
        data=payload,
    )
    print("update agent", code, body[:400].replace("\n", " "))
    if not code.startswith("2"):
        # try alternate shapes
        for alt in [
            {**payload, "id": AGENT},
            {"agent": payload},
            {"instructions": instructions, "knowledgeBaseIds": [KB], "locationId": LOC},
        ]:
            code, body = curl(
                "PUT",
                f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}",
                data=alt,
            )
            print("update alt", code, body[:300].replace("\n", " "))
            if code.startswith("2"):
                break
    return code


def main():
    raw = json.loads(RAW_PATH.read_text(encoding="utf-8"))
    text, procs, headers = build_docs(raw)
    print("DOC chars", len(text), "procs", len(procs))
    faqs = build_faqs(raw, procs, headers)
    (OUT / "faqs-plan.json").write_text(json.dumps(faqs, ensure_ascii=False, indent=2), encoding="utf-8")
    print("FAQs planned", len(faqs))

    rename_kb()
    clear_existing_faqs()
    upload_faqs(faqs)
    try_upload_file(OUT / "Procedimentos_GammaVet_KB.txt")

    # verify
    code, body = curl(
        "GET",
        f"https://services.leadconnectorhq.com/knowledge-base/faqs?locationId={LOC}&knowledgeBaseId={KB}&limit=100",
    )
    data = json.loads(body) if body.strip().startswith("{") else {}
    print("final faq count", data.get("count"), "listed", len(data.get("faqs") or []))


if __name__ == "__main__":
    main()
