# -*- coding: utf-8 -*-
"""Sobe Procedimentos_GammaVet_KB.md (ECG R$120). Não altera o agente."""
from __future__ import annotations

import json
import subprocess
from pathlib import Path

OUT = Path(r"c:\Users\GC1\Desktop\Automação GHL\gamma-vet")
ENV = Path(r"c:\Users\GC1\Desktop\Automação GHL\.env")
MD = OUT / "Procedimentos_GammaVet_KB.md"

vals = {}
for line in ENV.read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()

TOKEN = vals["GHL_GAMMA_API_KEY"]
LOC = vals["GHL_GAMMA_LOCATION_ID"]
KB = vals["GHL_GAMMA_KB_ID"]


def curl(method: str, url: str, data=None, form=None):
    cmd = [
        "curl.exe", "-s", "-w", "\nHTTP:%{http_code}",
        "-X", method, url,
        "-H", f"Authorization: Bearer {TOKEN}",
        "-H", "Version: 2021-07-28",
        "-H", "Accept: application/json",
        "-H", "User-Agent: Mozilla/5.0",
    ]
    if data is not None:
        tmp = OUT / "audit" / "req-ecg120.json"
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


def list_files():
    code, body = curl(
        "GET",
        f"https://services.leadconnectorhq.com/knowledge-base/files?locationId={LOC}&knowledgeBaseId={KB}&limit=50",
    )
    print("list files", code)
    files = []
    if code == "200" and body.strip().startswith("{"):
        data = json.loads(body)
        files = data.get("files") or data.get("data") or data.get("knowledgeBaseFiles") or []
        if isinstance(data.get("data"), dict):
            files = data["data"].get("files") or files
        if not isinstance(files, list):
            files = []
        for f in files:
            print(" ", f.get("id"), f.get("name") or f.get("fileName"), f.get("type") or "")
    else:
        print(body[:500])
    return files


def delete_old(files):
    for f in files:
        fid = f.get("id")
        name = (f.get("name") or f.get("fileName") or "").lower()
        if not fid:
            continue
        if "procedimento" in name or name.endswith(".md"):
            code, body = curl(
                "DELETE",
                f"https://services.leadconnectorhq.com/knowledge-base/files/{fid}?locationId={LOC}&knowledgeBaseId={KB}",
            )
            print("delete", fid, name[:50], code, body[:120].replace("\n", " "))


def upload_md():
    variants = [
        (
            f"https://services.leadconnectorhq.com/knowledge-base/files?locationId={LOC}&knowledgeBaseId={KB}",
            [f"file=@{MD}", f"locationId={LOC}", f"knowledgeBaseId={KB}", "name=Procedimentos_GammaVet_KB"],
        ),
        (
            "https://services.leadconnectorhq.com/knowledge-base/files",
            [f"file=@{MD}", f"locationId={LOC}", f"knowledgeBaseId={KB}"],
        ),
    ]
    for url, form in variants:
        code, body = curl("POST", url, form=form)
        print("upload", code, body[:400].replace("\n", " "))
        if code.startswith("2"):
            return True
    return False


def list_ecg_faqs():
    code, body = curl(
        "GET",
        f"https://services.leadconnectorhq.com/knowledge-base/faqs?locationId={LOC}&knowledgeBaseId={KB}&limit=100",
    )
    print("list faqs", code)
    if code != "200" or not body.strip().startswith("{"):
        print(body[:400])
        return
    faqs = json.loads(body).get("faqs") or []
    for f in faqs:
        blob = ((f.get("question") or "") + " " + (f.get("answer") or "")).lower()
        if "eletro" in blob or "ecg" in blob:
            q = (f.get("question") or "")[:80]
            a = (f.get("answer") or "")
            hit110 = "110" in a or "110" in q
            hit120 = "120" in a or "120" in q
            print(f"  FAQ {f.get('id')} 110={hit110} 120={hit120} | {q}")


def main():
    text = MD.read_text(encoding="utf-8")
    idx = text.find("## Eletrocardiograma")
    chunk = text[idx : idx + 600] if idx >= 0 else ""
    print("md has VALOR 120 after ECG:", "### VALOR\n120" in chunk)
    print("md still has VALOR 110 after ECG:", "### VALOR\n110" in chunk)
    files = list_files()
    delete_old(files)
    ok = upload_md()
    print("upload_ok", ok)
    list_files()
    list_ecg_faqs()


if __name__ == "__main__":
    main()
