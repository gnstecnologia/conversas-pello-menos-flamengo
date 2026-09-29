# -*- coding: utf-8 -*-
"""Sobe BASE.MD e atualiza FAQ de extração (só siso incluso/semi-incluso)."""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

OUT = Path(r"c:\Users\GC1\Desktop\Automação GHL\multiodonto-audit")
ENV = Path(r"c:\Users\GC1\Desktop\Automação GHL\.env")
MD = OUT / "BASE.MD"
key = None
for line in ENV.read_text(encoding="utf-8").splitlines():
    if line.startswith("GHL_MULTIODONTO_API_KEY="):
        key = line.split("=", 1)[1].strip()
        break
assert key, "missing PIT"

LOC = "3R4hY0j3TJyj2SkmSQL3"
KB = "HjJZbTH2w5riiz6GeC5y"
BASE = "https://services.leadconnectorhq.com"

FAQ_Q = "Fazem extração de dente?"
FAQ_A = (
    "Não, salvo siso. A clínica só realiza extração de siso (terceiro molar) "
    "nas posições incluso ou semi-incluso. Extração de outros dentes, inclusive "
    "após canal, não é feita. Não oferecer clínico geral. Siso: somente Campo Grande "
    "e somente por telefone (21) 3161-2205 ou (21) 99594-2638. RX panorâmico obrigatório."
)


def curl(method, url, data=None, form=None):
    cmd = [
        "curl.exe", "-s", "-w", "\nHTTP:%{http_code}",
        "-X", method, url,
        "-H", f"Authorization: Bearer {key}",
        "-H", "Version: 2021-07-28",
        "-H", "Accept: application/json",
        "-H", "User-Agent: Mozilla/5.0",
    ]
    if data is not None:
        tmp = OUT / "req-kb-extracao.json"
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


def main():
    code, body = curl(
        "GET",
        f"{BASE}/knowledge-base/files?locationId={LOC}&knowledgeBaseId={KB}&limit=50",
    )
    print("list files", code)
    files = []
    if code == "200" and body.strip().startswith("{"):
        data = json.loads(body)
        files = data.get("files") or data.get("data") or []
        if isinstance(data.get("data"), dict):
            files = data["data"].get("files") or files
        if not isinstance(files, list):
            files = []
        for f in files:
            print(" ", f.get("id"), f.get("name") or f.get("fileName"))

    for f in files:
        name = (f.get("name") or f.get("fileName") or "").lower()
        fid = f.get("id")
        if fid and ("base" in name or name.endswith(".md")):
            c2, b2 = curl(
                "DELETE",
                f"{BASE}/knowledge-base/files/{fid}?locationId={LOC}&knowledgeBaseId={KB}",
            )
            print("delete", name[:50], c2, b2[:120].replace("\n", " "))

    code, body = curl(
        "POST",
        f"{BASE}/knowledge-base/files?locationId={LOC}&knowledgeBaseId={KB}",
        form=[
            f"file=@{MD}",
            f"locationId={LOC}",
            f"knowledgeBaseId={KB}",
            "name=BASE",
        ],
    )
    print("upload", code, body[:300].replace("\n", " "))

    code, body = curl(
        "GET",
        f"{BASE}/knowledge-base/faqs?locationId={LOC}&knowledgeBaseId={KB}&limit=100",
    )
    print("list faqs", code)
    hit = None
    if code == "200" and body.strip().startswith("{"):
        for f in json.loads(body).get("faqs") or []:
            q = (f.get("question") or "").lower()
            a = (f.get("answer") or "").lower()
            if "extra" in q or "extra" in a or "siso" in q:
                print(" faq", f.get("id"), (f.get("question") or "")[:80])
                if "extra" in q and "siso" not in q:
                    hit = f

    payload = {"locationId": LOC, "knowledgeBaseId": KB, "question": FAQ_Q, "answer": FAQ_A}
    if hit:
        code, body = curl("PUT", f"{BASE}/knowledge-base/faqs/{hit['id']}", data=payload)
        print("faq PUT", hit["id"], code, body[:200].replace("\n", " "))
    else:
        code, body = curl("POST", f"{BASE}/knowledge-base/faqs", data=payload)
        print("faq POST", code, body[:200].replace("\n", " "))


if __name__ == "__main__":
    main()
