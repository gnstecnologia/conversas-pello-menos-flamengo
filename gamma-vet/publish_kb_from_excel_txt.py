# -*- coding: utf-8 -*-
"""Converte Procedimentos_GammaVet.xlsx em TXT organizado e publica na KB."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

import openpyxl

sys.stdout.reconfigure(encoding="utf-8")

OUT = Path(r"c:\Users\GC1\Desktop\Automação GHL\gamma-vet")
XLSX = Path(r"c:\Users\GC1\Downloads\Procedimentos_GammaVet (1) (1).xlsx")
TXT = OUT / "Procedimentos_GammaVet_KB.txt"
ENV = Path(r"c:\Users\GC1\Desktop\Automação GHL\.env")

vals = {}
for line in ENV.read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()

TOKEN = vals["GHL_GAMMA_API_KEY"]
LOC = vals["GHL_GAMMA_LOCATION_ID"]
KB = vals["GHL_GAMMA_KB_ID"]
AGENT = vals["GHL_GAMMA_AGENT_ID"]


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
        tmp = OUT / "audit" / "req-kb-txt.json"
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


def clean(v) -> str:
    if v is None:
        return ""
    return str(v).strip().replace("\r\n", "\n").replace("\r", "\n")


def build_txt() -> str:
    wb = openpyxl.load_workbook(XLSX, data_only=True)
    lines: list[str] = []
    lines.append("=" * 72)
    lines.append("BASE DE CONHECIMENTO — GAMMA VET")
    lines.append("Fonte: Procedimentos_GammaVet.xlsx (texto reorganizado)")
    lines.append("=" * 72)
    lines.append("")

    # --- Procedimentos ---
    ws = wb["Procedimentos"]
    headers = [clean(c.value) for c in next(ws.iter_rows(min_row=1, max_row=1))]
    lines.append("# 1. PROCEDIMENTOS")
    lines.append("")

    for row in ws.iter_rows(min_row=2, values_only=True):
        if not row or not row[0]:
            continue
        nome = clean(row[0]).replace("\n", " ")
        lines.append("-" * 72)
        lines.append(f"## {nome}")
        lines.append("-" * 72)
        for i, h in enumerate(headers):
            if i == 0 or not h:
                continue
            val = clean(row[i]) if i < len(row) else ""
            if not val:
                continue
            # STATUS IA é nota interna — incluir como observação de revisão
            title = h.upper() if h != "STATUS IA" else "NOTA DE REVISÃO (STATUS IA)"
            lines.append("")
            lines.append(f"### {title}")
            lines.append(val)
        lines.append("")

    # --- Regras comunicação ---
    if "regras comunicação" in wb.sheetnames:
        lines.append("")
        lines.append("=" * 72)
        lines.append("# 2. REGRAS DE COMUNICAÇÃO")
        lines.append("=" * 72)
        lines.append("")
        ws2 = wb["regras comunicação"]
        for row in ws2.iter_rows(values_only=True):
            cell = clean(row[0]) if row else ""
            if not cell:
                lines.append("")
                continue
            lines.append(cell)

    # --- Descritivos ---
    if "descritivo sobre os exames" in wb.sheetnames:
        lines.append("")
        lines.append("")
        lines.append("=" * 72)
        lines.append("# 3. DESCRITIVO DOS EXAMES")
        lines.append("=" * 72)
        lines.append("")
        ws3 = wb["descritivo sobre os exames"]
        headers3 = [clean(c.value) for c in next(ws3.iter_rows(min_row=1, max_row=1))]
        for row in ws3.iter_rows(min_row=2, values_only=True):
            if not row or not row[0]:
                continue
            nome = clean(row[0]).replace("\n", " ")
            lines.append("-" * 72)
            lines.append(f"## {nome}")
            lines.append("-" * 72)
            for i, h in enumerate(headers3):
                if i == 0 or not h:
                    continue
                val = clean(row[i]) if i < len(row) else ""
                if not val:
                    continue
                lines.append("")
                lines.append(f"### {h}")
                lines.append(val)
            lines.append("")

    lines.append("")
    lines.append("=" * 72)
    lines.append("Fim da base — Gamma Vet / Shopping Città Vet — Barra da Tijuca")
    lines.append("PIX sinal (quando houver): CNPJ 43608666000130")
    lines.append("=" * 72)
    return "\n".join(lines).strip() + "\n"


def list_kb_files():
    code, body = curl(
        "GET",
        f"https://services.leadconnectorhq.com/knowledge-base/files?locationId={LOC}&knowledgeBaseId={KB}&limit=50",
    )
    print("list files", code)
    if code == "200" and body.strip().startswith("{"):
        data = json.loads(body)
        files = data.get("files") or data.get("data") or data.get("knowledgeBaseFiles") or []
        if isinstance(data.get("data"), dict):
            files = data["data"].get("files") or files
        for f in files:
            print(" ", f.get("id"), f.get("name") or f.get("fileName"))
        return files if isinstance(files, list) else []
    print(body[:400])
    return []


def delete_old_files(files):
    for f in files:
        fid = f.get("id")
        name = (f.get("name") or f.get("fileName") or "").lower()
        if not fid:
            continue
        # remove previous KB docs for procedimentos
        if "procedimento" in name or name.endswith(".md") or name.endswith(".txt"):
            code, body = curl(
                "DELETE",
                f"https://services.leadconnectorhq.com/knowledge-base/files/{fid}?locationId={LOC}&knowledgeBaseId={KB}",
            )
            print("delete", fid, name[:40], code, body[:120].replace("\n", " "))


def upload_txt():
    code, body = curl(
        "POST",
        f"https://services.leadconnectorhq.com/knowledge-base/files?locationId={LOC}&knowledgeBaseId={KB}",
        form=[
            f"file=@{TXT}",
            f"locationId={LOC}",
            f"knowledgeBaseId={KB}",
            "name=Procedimentos_GammaVet_KB",
        ],
    )
    print("upload", code, body[:300].replace("\n", " "))


def ensure_agent_kb():
    """Garante KB no agente sem ligar WhatsApp."""
    code, body = curl(
        "GET",
        f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}?locationId={LOC}",
        version="2021-04-15",
    )
    a = json.loads(body) if body.strip().startswith("{") else {}
    # response is flat agent
    if a.get("id") != AGENT and "agent" in a:
        a = a["agent"]
    payload = {
        "name": a.get("name") or "Assistente Gamma Vet",
        "isPrimary": True,
        "mode": "off",
        "channels": ["WebChat"],
        "instructions": a.get("instructions") or "",
        "goal": a.get("goal") or "",
        "personality": a.get("personality") or "",
        "knowledgeBaseIds": [KB],
        "autoPilotMaxMessages": a.get("autoPilotMaxMessages") or 100,
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
    print("agent PUT", code, "mode off / WebChat")
    code2, body2 = curl(
        "GET",
        f"https://services.leadconnectorhq.com/conversation-ai/agents/{AGENT}?locationId={LOC}",
        version="2021-04-15",
    )
    after = json.loads(body2)
    print("after", after.get("mode"), after.get("channels"), after.get("isPrimary"), "kb", after.get("knowledgeBaseIds"))


def main():
    print("Building TXT from", XLSX.name)
    text = build_txt()
    TXT.write_text(text, encoding="utf-8")
    print("Wrote", TXT, "chars", len(text), "lines", text.count(chr(10)) + 1)
    print("=== KB files before ===")
    files = list_kb_files()
    delete_old_files(files)
    print("=== Upload TXT ===")
    upload_txt()
    print("=== KB files after ===")
    list_kb_files()
    print("=== Agent KB link (mode off) ===")
    ensure_agent_kb()
    print("DONE KB")


if __name__ == "__main__":
    main()
