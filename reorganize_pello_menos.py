# -*- coding: utf-8 -*-
"""Move artefatos Pello Menos de gamma-vet/ para pello-menos/."""
from __future__ import annotations

import re
import shutil
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

WS = Path(r"c:\Users\GC1\Desktop\Automação GHL")
SRC = WS / "gamma-vet"
DST = WS / "pello-menos"

SKIP_NAMES = {
    "reorganize_pello_menos.py",
}

# scripts claramente de outros clientes (ficam em gamma-vet)
GAMMA_ONLY_STEMS = {
    "cartao",
    "gamma",
    "ehmedical",
    "eh_",
    "deactivate_agent",
    "cleanup_gamma",
    "fix_gamma",
    "tighten_gamma",
    "list_gamma",
    "dump_gamma",
    "check_gamma",
    "import_oticas_carol",
    "clubliss",
    "export_ehmedical",
    "fetch_ehmedical",
    "publish_ehmedical",
    "probe_eh",
    "fix_rx",
    "retry_rx",
    "debug_rx",
    "apply_rx",
    "probe_rx",
    "probe_sat_rx",
    "apply_fernanda",
    "publish_fernanda",
    "migrate_fernanda",
    "check_agent_quick",
}


def is_pello_script(path: Path) -> bool:
    if path.suffix not in {".py", ".json", ".txt", ".log", ".md", ".html", ".bat"}:
        return False
    stem = path.stem.lower()
    for pref in GAMMA_ONLY_STEMS:
        if stem.startswith(pref) or pref in stem:
            return False
    if path.name.startswith("pello") or path.name.startswith("migrate"):
        return True
    if path.name in {
        "export_bot_conversas_franchising.py",
        "build_bot_mensagens_csv.py",
        "restrict_store_users_one_location.py",
        "ensure_owner_follower.py",
        "list_store_users.py",
        "list_pello_locations.py",
        "gerar_pdf_financeiro_pello.py",
        "snp-user-template.json",
        "_swap_bot_hut_emails.py",
    }:
        return True
    if path.name.startswith("attach_") and path.name.endswith("_user.py"):
        return True
    if path.suffix == ".py":
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return False
        if "GHL_PELLO" in text or "pellomenos.com" in text.lower():
            return True
    if path.suffix == ".json" and (
        stem.startswith("migrate")
        or stem.startswith("pello")
        or "urg-migrate" in stem
        or stem.startswith("assign")
    ):
        return True
    return False


def rewrite_paths(root: Path):
    old_abs = str(SRC)
    new_abs = str(DST)
    for p in root.rglob("*"):
        if p.suffix not in {".py", ".json", ".bat", ".md", ".js"}:
            continue
        try:
            text = p.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if "gamma-vet" not in text and "gamma-vet" not in text.lower():
            continue
        updated = text.replace(old_abs, new_abs)
        updated = updated.replace("gamma-vet/", "pello-menos/")
        updated = updated.replace("gamma-vet\\", "pello-menos\\")
        if updated != text:
            p.write_text(updated, encoding="utf-8")


def main():
    DST.mkdir(parents=True, exist_ok=True)
    (DST / "exports").mkdir(parents=True, exist_ok=True)

    moved = []

    exp_src = SRC / "exports" / "botafogo-conversas"
    exp_dst = DST / "exports" / "botafogo-conversas"
    if exp_src.exists() and not exp_dst.exists():
        shutil.copytree(exp_src, exp_dst)
        shutil.rmtree(exp_src, ignore_errors=True)
        moved.append("exports/botafogo-conversas")
    elif exp_src.exists() and exp_dst.exists():
        shutil.rmtree(exp_src, ignore_errors=True)
        moved.append("exports/botafogo-conversas (limpeza gamma-vet)")

    zip_src = SRC / "exports" / "botafogo-conversas.zip"
    zip_dst = DST / "exports" / "botafogo-conversas.zip"
    if zip_src.exists():
        if zip_dst.exists():
            zip_dst.unlink()
        shutil.move(str(zip_src), str(zip_dst))
        moved.append("exports/botafogo-conversas.zip")

    for p in sorted(SRC.iterdir()):
        if not p.is_file():
            continue
        if not is_pello_script(p):
            continue
        target = DST / p.name
        if target.exists():
            target.unlink()
        shutil.move(str(p), str(target))
        moved.append(p.name)

    root_html = WS / "pello-menos-franquia-email.html"
    if root_html.exists():
        t = DST / root_html.name
        if not t.exists():
            shutil.move(str(root_html), str(t))
            moved.append(root_html.name)

    rewrite_paths(DST)

    exp_parent = SRC / "exports"
    if exp_parent.exists() and not any(exp_parent.iterdir()):
        exp_parent.rmdir()

    print("movidos", len(moved))
    for m in moved[:30]:
        print(" ", m)
    if len(moved) > 30:
        print(" ", "... +", len(moved) - 30)


if __name__ == "__main__":
    main()
