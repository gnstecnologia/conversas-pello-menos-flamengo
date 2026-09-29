# -*- coding: utf-8 -*-
"""Atualiza ECG R$120 + RX região R$80; desliga agente (mode off); silencia bot na equipe."""
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
PROMPT = (OUT / "system-prompt-completo.md").read_text(encoding="utf-8")

# Contatos da equipe (conversa com o WhatsApp de agendamento)
STAFF = [
    {"name": "Marcello Comodo", "id": "4cReWV57zGHdRk2jHVCI", "phone": "+5521964430925"},
    {"name": "Gustavo Cobucci", "id": "JG54i4qh14CCpm6QmM6S", "phone": "+553196579532"},
    {"name": "Fernanda Meirelles", "id": "N2PEcvlRNaHyRBh4Qn3y", "phone": "+5524988238762"},
    {"name": "Mariana Gantois", "id": "scU5xY2AVThJ70eiltmJ", "phone": "+5521997805456"},
    # Marcella Rosa: procurar abaixo se houver id
]


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


def find_marcella():
    code, body = curl(
        "POST",
        "https://services.leadconnectorhq.com/contacts/search",
        data={"locationId": LOC, "query": "Marcella Rosa", "pageLimit": 10},
    )
    if code == "200" and body.strip().startswith("{"):
        for z in json.loads(body).get("contacts") or []:
            name = f"{z.get('firstName') or ''} {z.get('lastName') or ''}".lower()
            email = (z.get("email") or "").lower()
            if "rosa" in name or "marcella_rosa" in email or "rosa" in email:
                return {
                    "name": f"{z.get('firstName')} {z.get('lastName')}".strip(),
                    "id": z["id"],
                    "phone": z.get("phone"),
                }
    return None


def put_agent():
    code, body = curl(
        "GET",
        f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}?locationId={LOC}",
        version="2021-04-15",
    )
    before = json.loads(body).get("agent") or json.loads(body)
    print("before mode", before.get("mode"), "channels", before.get("channels"), "primary", before.get("isPrimary"))

    payload = {
        "name": "Assistente Gamma Vet",
        "isPrimary": True,
        "mode": "off",
        "channels": ["WebChat"],
        "instructions": PROMPT,
        "goal": (
            "Conduzir o responsável até o agendamento: pacote na 1ª resposta; "
            "valores corretos (ECG R$120; RX R$200 + R$80 região adicional; Eco R$400); "
            "tireoide nos horários fixos; não agendar renal/encaixes; "
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
    print("agent PUT", code, body[:200].replace("\n", " "))
    code, body = curl(
        "GET",
        f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}?locationId={LOC}",
        version="2021-04-15",
    )
    after = json.loads(body).get("agent") or json.loads(body)
    (OUT / "agent-live-now.json").write_text(json.dumps(after, ensure_ascii=False, indent=2), encoding="utf-8")
    inst = after.get("instructions") or ""
    print(
        "after mode", after.get("mode"),
        "channels", after.get("channels"),
        "primary", after.get("isPrimary"),
        "ECG120", "R$120" in inst,
        "RX80", "R$80" in inst,
    )
    if after.get("isPrimary") is not True:
        print("ALERTA: isPrimary caiu")
    if after.get("mode") != "off" or after.get("channels") != ["WebChat"]:
        print("ALERTA mode/channels", after.get("mode"), after.get("channels"))


def upload_kb_and_faqs():
    doc = OUT / "Procedimentos_GammaVet_KB.md"
    code, body = curl(
        "POST",
        f"https://services.leadconnectorhq.com/knowledge-base/files?locationId={LOC}&knowledgeBaseId={KB}",
        form=[f"file=@{doc}", f"locationId={LOC}", f"knowledgeBaseId={KB}", "name=Procedimentos_GammaVet_KB"],
    )
    print("kb file", code, body[:180].replace("\n", " "))

    faqs = [
        {
            "question": "Quanto custa eletrocardiograma e Raio-X?",
            "answer": (
                "Eletrocardiograma: R$ 120,00. "
                "Raio-X: R$ 200,00 (1 região); cada região adicional R$ 80,00. "
                "Ecocardiograma: R$ 400,00."
            ),
        },
        {
            "question": "Eletrocardiograma: valor?",
            "answer": "R$ 120,00.",
        },
        {
            "question": "Raio-X: valor por região?",
            "answer": "R$ 200,00 para 1 região. Cada região adicional R$ 80,00.",
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
    for item in faqs:
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
            print("faq PUT", code, q)
        else:
            code, body = curl(
                "POST",
                "https://services.leadconnectorhq.com/knowledge-base/faqs",
                data=payload,
            )
            print("faq POST", code, q)


def tag_and_try_silence(staff_list):
    """Marca tag equipe_interna e tenta endpoints de bot inactive."""
    results = []
    for s in staff_list:
        cid = s["id"]
        # add tag
        code, body = curl(
            "POST",
            f"https://services.leadconnectorhq.com/contacts/{cid}/tags",
            data={"tags": ["equipe_interna"]},
        )
        print("tag", s["name"], code, body[:120].replace("\n", " "))

        # try common bot-status payloads
        tried = []
        for method, url, data, ver in [
            (
                "POST",
                "https://services.leadconnectorhq.com/conversation-ai/bot",
                {"contactId": cid, "locationId": LOC, "agentId": AGENT, "status": "inactive"},
                "2021-04-15",
            ),
            (
                "PUT",
                f"https://services.leadconnectorhq.com/contacts/{cid}",
                {
                    "tags": ["equipe_interna"],
                },
                "2021-07-28",
            ),
        ]:
            code, body = curl(method, url, data=data, version=ver)
            tried.append((method, url.split(".com")[-1][:50], code, body[:80]))
        results.append({"staff": s, "tried": tried})
    (OUT / "audit" / "staff-silence-attempt.json").write_text(
        json.dumps(results, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def main():
    m = find_marcella()
    staff = list(STAFF)
    if m:
        staff.append(m)
        print("Marcella encontrada", m)
    else:
        print("Marcella Rosa: contato WhatsApp não encontrado pelo nome — avisar usuário")

    print("=== KB/FAQs ===")
    upload_kb_and_faqs()
    print("=== Agent (mode off) ===")
    put_agent()
    print("=== Staff silence ===")
    tag_and_try_silence(staff)
    print("DONE")


if __name__ == "__main__":
    main()
