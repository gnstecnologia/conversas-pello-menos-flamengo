# -*- coding: utf-8 -*-
"""Atualiza telefones Campo Grande: só (21) 3161-2205 e (21) 99594-2638. Sem 98493-0549."""
from __future__ import annotations

import json
import subprocess
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ENV = Path(r"c:\Users\GC1\Desktop\Automação GHL\.env")
OUT = Path(r"c:\Users\GC1\Desktop\Automação GHL\multiodonto-audit")
MD = OUT / "BASE.MD"
key = None
for line in ENV.read_text(encoding="utf-8").splitlines():
    if line.startswith("GHL_MULTIODONTO_API_KEY="):
        key = line.split("=", 1)[1].strip()
        break
assert key, "missing PIT"

AGENT = "3Fzfmx7ViwyD9v16h4DR"
LOC = "3R4hY0j3TJyj2SkmSQL3"
KB = "HjJZbTH2w5riiz6GeC5y"
BASE = "https://services.leadconnectorhq.com"
OLD = "98493-0549"

PERSONALITY = (OUT / "personality-new.txt").read_text(encoding="utf-8").strip()
GOAL = (OUT / "goal-new.txt").read_text(encoding="utf-8").strip()
INSTRUCTIONS = (OUT / "instructions-new.txt").read_text(encoding="utf-8").strip()


def req(method, path, body=None, version="2021-07-28"):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    request = urllib.request.Request(
        BASE + path,
        data=data,
        method=method,
        headers={
            "Authorization": f"Bearer {key}",
            "Version": version,
            "Accept": "application/json",
            "Content-Type": "application/json; charset=utf-8",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=90) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode(errors="replace")


def unwrap_agent(payload):
    if isinstance(payload, dict) and "instructions" in payload:
        return payload
    if isinstance(payload, dict):
        return payload.get("data") or payload.get("agent") or payload
    return payload


def curl(method: str, url: str, data=None, form=None):
    cmd = [
        "curl.exe", "-s", "-w", "\nHTTP:%{http_code}",
        "-X", method, url,
        "-H", f"Authorization: Bearer {key}",
        "-H", "Version: 2021-07-28",
        "-H", "Accept: application/json",
        "-H", "User-Agent: Mozilla/5.0",
    ]
    if data is not None:
        tmp = OUT / "req-cg-phones.json"
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
        f"{BASE}/knowledge-base/files?locationId={LOC}&knowledgeBaseId={KB}&limit=50",
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
            print(" ", f.get("id"), f.get("name") or f.get("fileName"))
    else:
        print(body[:400])
    return files if isinstance(files, list) else []


def delete_old_md(files):
    for f in files:
        fid = f.get("id")
        name = (f.get("name") or f.get("fileName") or "").lower()
        if not fid:
            continue
        if "base" in name or name.endswith(".md"):
            code, body = curl(
                "DELETE",
                f"{BASE}/knowledge-base/files/{fid}?locationId={LOC}&knowledgeBaseId={KB}",
            )
            print("delete", fid, name[:50], code, body[:120].replace("\n", " "))


def upload_md():
    variants = [
        (
            f"{BASE}/knowledge-base/files?locationId={LOC}&knowledgeBaseId={KB}",
            [f"file=@{MD}", f"locationId={LOC}", f"knowledgeBaseId={KB}", "name=BASE"],
        ),
        (
            f"{BASE}/knowledge-base/files",
            [f"file=@{MD}", f"locationId={LOC}", f"knowledgeBaseId={KB}"],
        ),
    ]
    for url, form in variants:
        code, body = curl("POST", url, form=form)
        print("upload", code, body[:350].replace("\n", " "))
        if code.startswith("2"):
            return True
    return False


def patch_faqs():
    code, body = curl(
        "GET",
        f"{BASE}/knowledge-base/faqs?locationId={LOC}&knowledgeBaseId={KB}&limit=100",
    )
    print("list faqs", code)
    if code != "200" or not body.strip().startswith("{"):
        print(body[:400])
        return
    faqs = json.loads(body).get("faqs") or []
    n = 0
    for f in faqs:
        q = f.get("question") or ""
        a = f.get("answer") or ""
        fid = f.get("id")
        blob = q + " " + a
        if OLD not in blob and "98493" not in blob:
            continue
        new_q = q.replace("(21) 98493-0549 | ", "").replace(" | (21) 98493-0549", "").replace("(21) 98493-0549", "")
        new_q = new_q.replace("98493-0549 | ", "").replace(" | 98493-0549", "").replace("98493-0549", "")
        new_a = a.replace("(21) 98493-0549 | ", "").replace(" | (21) 98493-0549", "").replace("(21) 98493-0549", "")
        new_a = new_a.replace("98493-0549 | ", "").replace(" | 98493-0549", "").replace("98493-0549", "")
        payload = {
            "locationId": LOC,
            "knowledgeBaseId": KB,
            "question": new_q.strip(),
            "answer": new_a.strip(),
        }
        pcode, pbody = curl("PUT", f"{BASE}/knowledge-base/faqs/{fid}", data=payload)
        print("faq PUT", fid, pcode, q[:70])
        n += 1
    print("faqs patched", n)


def publish_agent():
    st, agent = req("GET", f"/conversation-ai/agents/{AGENT}", version="2021-04-15")
    print("GET agent", st)
    if st != 200:
        print(agent)
        return False
    a = unwrap_agent(agent)
    (OUT / "agent-before-cg-phones.json").write_text(
        json.dumps(a, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("before isPrimary:", a.get("isPrimary"), "mode:", a.get("mode"), "channels:", a.get("channels"))

    channels = a.get("channels") or ["WhatsApp", "SMS", "IG", "FB"]
    put_body = {
        "name": a.get("name") or "Letícia IA Agendamento",
        "personality": PERSONALITY,
        "goal": GOAL,
        "instructions": INSTRUCTIONS,
        "isPrimary": True,
        "mode": a.get("mode") or "auto-pilot",
        "channels": channels,
    }
    for f in ("mode", "knowledgeBaseIds", "autoPilotMaxMessages"):
        if a.get(f) is not None:
            put_body[f] = a[f]
    put_body["isPrimary"] = True

    st, resp = req("PUT", f"/conversation-ai/agents/{AGENT}", put_body, version="2021-04-15")
    print("PUT agent", st)
    if st not in (200, 201):
        print(str(resp)[:2000])
        return False
    (OUT / "agent-after-cg-phones.json").write_text(
        json.dumps(resp, ensure_ascii=False, indent=2) if isinstance(resp, dict) else str(resp),
        encoding="utf-8",
    )
    (OUT / "leticia-prompt.txt").write_text(
        "PERSONALITY\n" + PERSONALITY + "\n\nGOAL\n" + GOAL + "\n\nINSTRUCTIONS\n" + INSTRUCTIONS,
        encoding="utf-8",
    )

    st, agent2 = req("GET", f"/conversation-ai/agents/{AGENT}", version="2021-04-15")
    a2 = unwrap_agent(agent2)
    instr = a2.get("instructions") or ""
    print("VERIFY isPrimary:", a2.get("isPrimary"), "mode:", a2.get("mode"), "channels:", a2.get("channels"))
    print("  3161-2205:", "3161-2205" in instr)
    print("  99594-2638:", "99594-2638" in instr)
    print("  SÓ esses 2:", "SÓ esses 2 números" in instr)
    print("  98493 still in prompt as contact list:", "| (21) 98493-0549" in instr)
    if a2.get("isPrimary") is not True:
        print("ALERTA: isPrimary não veio no GET (padrão da API). PUT foi com isPrimary true.")
    return True


def main():
    assert "3161-2205" in INSTRUCTIONS and "99594-2638" in INSTRUCTIONS
    assert "| (21) 98493-0549" not in INSTRUCTIONS
    assert "3161-2205" in MD.read_text(encoding="utf-8")
    assert "| (21) 98493-0549" not in MD.read_text(encoding="utf-8")
    ok = publish_agent()
    files = list_files()
    delete_old_md(files)
    print("upload_ok", upload_md())
    list_files()
    patch_faqs()
    print("done agent", ok)


if __name__ == "__main__":
    main()
