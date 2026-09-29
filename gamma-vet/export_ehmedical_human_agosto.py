# -*- coding: utf-8 -*-
"""
Exporta negociacoes EHMEDICAL que passaram por Atendimento Humano em agosto/2026.

A API GHL nao expoe historico de etapas. Criterios (melhor aproximacao possivel):
  A) Etapa atual = Atendimento Humano e entrou nessa etapa ate 31/08/2026
  B) Saiu da etapa em agosto: lastStageChangeAt em ago/2026 e etapa atual e posterior
     a Atendimento Humano no mesmo pipeline (fluxo normal para frente)

Negociacoes criadas em set/2026+ sao excluidas.
Para lista 100% exata (incl. pulos de etapa e saida em set): Audit Logs CSV do GHL.
"""
from __future__ import annotations

import csv
import json
import os
import subprocess
import sys
import time
from datetime import datetime, timezone, timedelta
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

OUT = Path(r"c:\Users\GC1\Desktop\Automação GHL\gamma-vet\exports")
OUT.mkdir(parents=True, exist_ok=True)

ENV = Path(r"c:\Users\GC1\Desktop\Automação GHL\.env")
_env: dict[str, str] = {}
if ENV.exists():
    for line in ENV.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, v = line.split("=", 1)
            _env[k.strip()] = v.strip()

TOKEN = os.getenv("GHL_EHMEDICAL_API_KEY") or _env.get("GHL_EHMEDICAL_API_KEY", "")
LOC = os.getenv("GHL_EHMEDICAL_LOCATION_ID") or _env.get("GHL_EHMEDICAL_LOCATION_ID", "9Ahv460EPGTwS2J1sxYP")
BRT = timezone(timedelta(hours=-3))
AUG_START = datetime(2026, 8, 1, 0, 0, 0, tzinfo=BRT)
SEP_START = datetime(2026, 9, 1, 0, 0, 0, tzinfo=BRT)

HUMAN_STAGES = {
    "e6485698-a548-475c-beff-d79f4da174cd": ("Locação", "Atendimento Humano"),
    "2fc3880f-055e-4271-8ca2-0d1e624fa4ef": ("Vendas", "Atendimento Humano"),
    "05944105-d9ed-4f8e-bf65-45f0404f1b29": ("Workshop", "Atendimento Humano"),
}

FIELD_EQUIPAMENTO = "TjLtVGuzQFfqqYFuZI3q"
FIELD_PRODUTO_BAIXA_GAMA = "ki0qk2q1NGLQohqyi4kC"


def curl(url: str, ver="2021-07-28") -> dict:
    cmd = [
        "curl.exe", "-s", url,
        "-H", f"Authorization: Bearer {TOKEN}",
        "-H", f"Version: {ver}",
        "-H", "Accept: application/json",
        "-H", "User-Agent: Mozilla/5.0",
    ]
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace")
    raw = r.stdout.strip()
    if not raw.startswith("{"):
        return {}
    return json.loads(raw)


def parse_dt(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, (int, float)):
        return datetime.fromtimestamp(value / 1000, tz=timezone.utc)
    if isinstance(value, str):
        s = value.strip()
        if s.isdigit():
            return datetime.fromtimestamp(int(s) / 1000, tz=timezone.utc)
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        try:
            return datetime.fromisoformat(s)
        except ValueError:
            return None
    return None


def dt_to_str(value) -> str:
    dt = parse_dt(value)
    if not dt:
        return str(value or "")
    return dt.astimezone(BRT).strftime("%Y-%m-%d %H:%M")


def in_august_2026(value) -> bool:
    dt = parse_dt(value)
    if not dt:
        return False
    local = dt.astimezone(BRT)
    return AUG_START <= local < SEP_START


def created_on_or_before_august(value) -> bool:
    dt = parse_dt(value)
    if not dt:
        return False
    return dt.astimezone(BRT) < SEP_START


def load_pipeline_maps() -> tuple[dict[str, tuple[str, str, int, str]], dict[str, int]]:
    """stage_id -> (pipeline_id, pipeline_name, index, stage_name); pipeline_id -> human_index."""
    data = curl(f"https://services.leadconnectorhq.com/opportunities/pipelines?locationId={LOC}")
    stage_map: dict[str, tuple[str, str, int, str]] = {}
    human_index: dict[str, int] = {}
    for pipe in data.get("pipelines") or []:
        pid = pipe.get("id") or ""
        pname = pipe.get("name") or pid
        for i, stage in enumerate(pipe.get("stages") or []):
            sid = stage.get("id") or ""
            sname = stage.get("name") or sid
            stage_map[sid] = (pid, pname, i, sname)
            if sid in HUMAN_STAGES:
                human_index[pid] = i
    return stage_map, human_index


def fetch_all_opportunities() -> list[dict]:
    all_opps: list[dict] = []
    start_after_id = None
    start_after = None
    page = 1
    while page <= 200:
        q = [f"location_id={LOC}", "limit=100", "status=all"]
        if start_after_id:
            q.append(f"startAfterId={start_after_id}")
        if start_after:
            q.append(f"startAfter={start_after}")
        url = "https://services.leadconnectorhq.com/opportunities/search?" + "&".join(q)
        data = curl(url)
        opps = data.get("opportunities") or []
        if not opps:
            break
        all_opps.extend(opps)
        meta = data.get("meta") or {}
        start_after_id = meta.get("startAfterId")
        start_after = meta.get("startAfter")
        if not start_after_id:
            break
        page += 1
        time.sleep(0.1)
    return all_opps


def classify_pass_through(
    opp: dict,
    stage_map: dict[str, tuple[str, str, int, str]],
    human_index: dict[str, int],
) -> str | None:
    """Retorna motivo de inclusao ou None se nao passou por humano em ago/2026."""
    if not created_on_or_before_august(opp.get("createdAt")):
        return None

    sid = opp.get("pipelineStageId") or ""
    pid = opp.get("pipelineId") or ""
    if pid not in human_index or sid not in stage_map:
        return None

    lsc = parse_dt(opp.get("lastStageChangeAt"))
    lsc_local = lsc.astimezone(BRT) if lsc else None
    cur_idx = stage_map[sid][2]
    hi = human_index[pid]

    if sid in HUMAN_STAGES:
        if lsc_local and lsc_local < SEP_START:
            return "A_em_humano_entrada_ate_31ago"
        return None

    if in_august_2026(opp.get("lastStageChangeAt")) and cur_idx > hi:
        return "B_saiu_humano_mudanca_etapa_em_agosto"

    return None


def custom_field_value(opp: dict, field_id: str) -> str:
    for cf in opp.get("customFields") or []:
        if cf.get("id") != field_id:
            continue
        if cf.get("fieldValueArray"):
            return ", ".join(str(x) for x in cf["fieldValueArray"])
        for key in ("fieldValueString", "value", "fieldValue"):
            if cf.get(key):
                return str(cf[key])
    return ""


def significado_data(criterio: str, lsc_em_agosto: bool) -> str:
    if criterio == "B_saiu_humano_mudanca_etapa_em_agosto":
        return (
            "Data em que SAIU de Atendimento Humano (foi para a etapa atual). "
            "Passou por humano em agosto."
        )
    if criterio == "A_em_humano_entrada_ate_31ago" and lsc_em_agosto:
        return (
            "Data em que ENTROU ou REENTROU em Atendimento Humano "
            "(ex.: voltou de Perdido). Passou por humano em agosto."
        )
    if criterio == "A_em_humano_entrada_ate_31ago":
        return (
            "Ja estava em Atendimento Humano antes de agosto; "
            "ultima mudanca de etapa foi a ENTRADA nessa etapa (data anterior). "
            "Esteve em humano durante agosto, mas nao entrou em agosto."
        )
    return ""


def enrich_row(opp: dict, criterio: str, stage_map: dict) -> dict:
    contact = opp.get("contact") or {}
    sid = opp.get("pipelineStageId") or ""
    pipe_name, stage_name = "", sid
    if sid in stage_map:
        pipe_name = stage_map[sid][1]
        stage_name = stage_map[sid][3]
    lsc_em_agosto = in_august_2026(opp.get("lastStageChangeAt"))
    return {
        "criterio_inclusao": criterio,
        "mudanca_etapa_em_agosto": "Sim" if lsc_em_agosto else "Nao",
        "significado_ultima_mudanca_etapa": significado_data(criterio, lsc_em_agosto),
        "opportunity_id": opp.get("id") or "",
        "nome_negociacao": opp.get("name") or "",
        "pipeline": pipe_name,
        "etapa_atual": stage_name,
        "equipamento": custom_field_value(opp, FIELD_EQUIPAMENTO),
        "produto_baixa_gama": custom_field_value(opp, FIELD_PRODUTO_BAIXA_GAMA),
        "pipeline_stage_id": sid,
        "status": opp.get("status") or "",
        "valor": opp.get("monetaryValue") or "",
        "criado_em": dt_to_str(opp.get("createdAt")),
        "ultima_mudanca_etapa": dt_to_str(opp.get("lastStageChangeAt")),
        "atualizado_em": dt_to_str(opp.get("updatedAt") or opp.get("lastStatusChangeAt")),
        "contato_id": contact.get("id") or opp.get("contactId") or "",
        "contato_nome": contact.get("name") or "",
        "contato_email": contact.get("email") or "",
        "contato_telefone": contact.get("phone") or "",
        "responsavel": opp.get("assignedTo") or "",
    }


def main():
    if not TOKEN:
        print("Defina GHL_EHMEDICAL_API_KEY no .env")
        sys.exit(1)

    print("=== EHMEDICAL | passaram por Atendimento Humano em ago/2026 ===")
    print("Location:", LOC)
    print("Criadas: ate 31/08/2026 | Passagem em humano: criterios A + B (ver docstring)")

    stage_map, human_index = load_pipeline_maps()
    all_opps = fetch_all_opportunities()
    print(f"Total negociacoes na conta: {len(all_opps)}")

    rows: list[dict] = []
    counts: dict[str, int] = {}
    by_pipe: dict[str, int] = {}

    for opp in all_opps:
        criterio = classify_pass_through(opp, stage_map, human_index)
        if not criterio:
            continue
        row = enrich_row(opp, criterio, stage_map)
        rows.append(row)
        counts[criterio] = counts.get(criterio, 0) + 1
        by_pipe[row["pipeline"]] = by_pipe.get(row["pipeline"], 0) + 1

    rows.sort(key=lambda r: (r["pipeline"], r["ultima_mudanca_etapa"], r["nome_negociacao"]))
    rows_agosto = [r for r in rows if r["mudanca_etapa_em_agosto"] == "Sim"]

    ts = datetime.now(BRT).strftime("%Y%m%d_%H%M")
    path_csv = OUT / f"ehmedical_passaram_atendimento_humano_agosto2026_{ts}.csv"
    path_csv_agosto = OUT / f"ehmedical_atendimento_humano_mudanca_etapa_agosto2026_{ts}.csv"
    fields = list(enrich_row({}, "x", {}).keys())

    with path_csv.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows)

    with path_csv_agosto.open("w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=fields, extrasaction="ignore")
        w.writeheader()
        w.writerows(rows_agosto)

    summary = {
        "location": LOC,
        "periodo": "agosto/2026 (passagem pela etapa Atendimento Humano)",
        "criado_em": "ate 31/08/2026 inclusive",
        "total_exportadas": len(rows),
        "total_mudanca_etapa_em_agosto": len(rows_agosto),
        "por_criterio": counts,
        "por_pipeline": by_pipe,
        "csv_completo": str(path_csv),
        "csv_mudanca_etapa_agosto": str(path_csv_agosto),
        "colunas_relatorio": ["nome_negociacao", "ultima_mudanca_etapa", "equipamento", "produto_baixa_gama"],
        "nota_ultima_mudanca_etapa": (
            "ultima_mudanca_etapa = data da ULTIMA mudanca de etapa no funil (nao e atualizado_em). "
            "Se entrou/reentrou em Atendimento Humano em agosto (ex. voltou de Perdido), essa data "
            "e quando passou por humano. Se ja estava em humano desde antes, a data e a entrada "
            "anterior — use mudanca_etapa_em_agosto=Sim para filtrar so agosto."
        ),
        "limitacao": (
            "Sem historico de etapas na API. Pode faltar quem entrou em humano em ago e saiu em set; "
            "pode incluir falso positivo se etapa foi pulada manualmente. "
            "Para 100%: Settings > Audit Logs > Module Opportunities > export CSV ago/2026."
        ),
    }
    path_json = OUT / f"ehmedical_passaram_human_summary_{ts}.json"
    path_json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    print("\n=== RESUMO ===")
    print(f"Exportadas (completo): {len(rows)}")
    print(f"Mudanca de etapa em ago/2026: {len(rows_agosto)}")
    print("Por criterio:", counts)
    print("Por pipeline:", by_pipe)
    print("CSV completo:", path_csv)
    print("CSV filtro agosto (ultima_mudanca_etapa em ago):", path_csv_agosto)
    print("\n", summary["limitacao"])
    print("\nDONE")


if __name__ == "__main__":
    main()
