# -*- coding: utf-8 -*-
"""Microbolhas + tireoide reforçada + equipe interna ampliada. Agente mode=off, WebChat."""
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

STAFF = [
    {"name": "Marcello Comodo", "id": "4cReWV57zGHdRk2jHVCI"},
    {"name": "Gustavo Cobucci", "id": "JG54i4qh14CCpm6QmM6S"},
    {"name": "Fernanda Meirelles", "id": "N2PEcvlRNaHyRBh4Qn3y"},
    {"name": "Mariana Gantois", "id": "scU5xY2AVThJ70eiltmJ"},
    {"name": "Aline Machado", "id": "W0IebXmLTXe0DELW470d"},
    {"name": "Cristiane Botelho", "id": "sUsZDc3JKUPoyFGDj3vL"},
    {"name": "Eduardo Cotias", "id": "kO7yGWYnyZgeMAfmfD9T"},
    {"name": "Gracy Marcello", "id": "a9JUcpyE3I6dQgS4I3dO"},
    {"name": "Rafael Seiti", "id": "7FMmIcICWNVn9clIAfEg"},
    {"name": "Daniel Brandello", "id": "cZdHBQXcYsSfCbMnm6ah"},
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


def search_contact(query: str):
    code, body = curl(
        "POST",
        "https://services.leadconnectorhq.com/contacts/search",
        data={"locationId": LOC, "query": query, "pageLimit": 15},
    )
    if code == "200" and body.strip().startswith("{"):
        return json.loads(body).get("contacts") or []
    return []


def find_extra_staff():
    found = []
    for q in ["Arrochella", "Luiza d Arrochella", "Debora Cruz anest", "Deborah Cruz"]:
        for z in search_contact(q):
            name = f"{z.get('firstName') or ''} {z.get('lastName') or ''}".strip()
            low = name.lower()
            if "arrochella" in low or ("debor" in low and "cruz" in low):
                found.append({"name": name, "id": z["id"]})
    # dedupe
    seen = set()
    out = []
    for s in found:
        if s["id"] not in seen:
            seen.add(s["id"])
            out.append(s)
    return out


def tag_staff(staff_list):
    for s in staff_list:
        code, body = curl(
            "POST",
            f"https://services.leadconnectorhq.com/contacts/{s['id']}/tags",
            data={"tags": ["equipe_interna"]},
        )
        print("tag", s["name"], code, body[:100].replace("\n", " "))


def upload_kb():
    doc = OUT / "Procedimentos_GammaVet_KB.md"
    code, body = curl(
        "POST",
        f"https://services.leadconnectorhq.com/knowledge-base/files?locationId={LOC}&knowledgeBaseId={KB}",
        form=[f"file=@{doc}", f"locationId={LOC}", f"knowledgeBaseId={KB}", "name=Procedimentos_GammaVet_KB"],
    )
    print("kb", code, body[:160].replace("\n", " "))


def upsert_faqs():
    faqs = [
        {
            "question": "Ultrassonografia com microbolhas: valor por peso?",
            "answer": (
                "Até 10 kg: R$ 750,00. 11 a 20 kg: R$ 850,00. 21 kg em diante: R$ 950,00. "
                "Região ou nódulo adicional: + R$ 200,00 cada. "
                "Agenda: quartas e quintas. Laudo: até 4 dias úteis."
            ),
        },
        {
            "question": "Cintilografia de tireoide: quais horários exatos?",
            "answer": (
                "Lista fechada: 9:30, 10:00, 13:00, 13:30 e 16:00. "
                "Segunda e quinta: todos os 5. Terça: só 13:00, 13:30 e 16:00. "
                "Nunca oferecer 15:30 nem outro horário fora dessa lista."
            ),
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
            print("faq PUT", code, item["question"][:50])
        else:
            code, body = curl("POST", "https://services.leadconnectorhq.com/knowledge-base/faqs", data=payload)
            print("faq POST", code, item["question"][:50])


def put_agent():
    payload = {
        "name": "Assistente Gamma Vet",
        "isPrimary": True,
        "mode": "off",
        "channels": ["WebChat"],
        "instructions": PROMPT,
        "goal": (
            "Agendar com pacote na 1ª resposta. Tireoide: SOMENTE 9:30/10/13/13:30/16h (terça sem manhã). "
            "Microbolhas: até 10kg R$750, 11-20 R$850, 21+ R$950, +R$200 região. "
            "Tag equipe_interna = silêncio total. Renal/encaixes = humano."
        ),
        "personality": (
            "Formal porém acolhedor. Gamma Vet no masculino. Assistente virtual. "
            "Áudio: pedir texto. Horários de tireoide: lista fechada, nunca inventar."
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
    print("agent PUT", code, body[:180].replace("\n", " "))
    code, body = curl(
        "GET",
        f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}?locationId={LOC}",
        version="2021-04-15",
    )
    a = json.loads(body).get("agent") or json.loads(body)
    inst = a.get("instructions") or ""
    (OUT / "agent-live-now.json").write_text(json.dumps(a, ensure_ascii=False, indent=2), encoding="utf-8")
    print(
        "after mode", a.get("mode"),
        "channels", a.get("channels"),
        "primary", a.get("isPrimary"),
        "lista fechada", "Lista fechada" in inst,
        "micro850", "850" in inst,
    )
    if a.get("mode") != "off" or a.get("channels") != ["WebChat"]:
        print("ALERTA mode/channels", a.get("mode"), a.get("channels"))


def main():
    extra = find_extra_staff()
    if extra:
        print("extra staff", extra)
    else:
        print("Luiza d'Arrochella / Debora Cruz: não encontrados — pedir celular se necessário")
    staff = STAFF + extra
    (OUT / "audit" / "staff-equipe-interna.json").write_text(
        json.dumps(staff, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    upload_kb()
    upsert_faqs()
    put_agent()
    tag_staff(staff)
    print("DONE staff tagged", len(staff))


if __name__ == "__main__":
    main()
