# -*- coding: utf-8 -*-
"""Exporta conversas Flamengo (FLA) da Franchising + viewer com filtros (sem telefone)."""
from __future__ import annotations

import csv
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import zipfile
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parent
ENV = ROOT.parent / ".env"
OUT_DIR = ROOT / "exports" / "fla-conversas"
CONV_DIR = OUT_DIR / "conversas"
VIEWER_DIR = OUT_DIR / "viewer"
ZIP_PATH = ROOT / "exports" / "fla-conversas.zip"
BASE = "https://services.leadconnectorhq.com"
BRT = timezone(timedelta(hours=-3))

# Usuarios FLA na Franchising
FLA_USERS = {
    "y3WSdOwVSPCzyw59wk1Y": "Unidade fla@",
    "1HJHSz5iRJRPCZKEF0qa": "Gerência Flamengo",
    "L31q26MWXMbwxNl4pa0c": "Unidade frente loja",
    "4tfa8sKha1Hfz6QjEUrX": "Unidade flamengolaser",
}
TAG_FLA = "flamengo"

vals = {}
for line in ENV.read_text(encoding="utf-8").splitlines():
    if "=" in line and not line.strip().startswith("#"):
        k, v = line.split("=", 1)
        vals[k.strip()] = v.strip()

KEY = vals["GHL_PELLO_API_KEY"]
LOC = vals["GHL_PELLO_LOCATION_ID"]


def req(method: str, url: str, body=None):
    data = None if body is None else json.dumps(body, ensure_ascii=False).encode("utf-8")
    headers = {
        "Authorization": "Bearer " + KEY,
        "Version": "2021-07-28",
        "Accept": "application/json",
        "User-Agent": "Mozilla/5.0",
    }
    if body is not None:
        headers["Content-Type"] = "application/json; charset=utf-8"
    r = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(r, timeout=90) as resp:
            raw = resp.read().decode("utf-8")
            return resp.status, json.loads(raw) if raw else {}
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, {"raw": raw[:400]}


def search_contacts(filters: list) -> list:
    out = []
    page = 1
    while True:
        st, d = req(
            "POST",
            BASE + "/contacts/search",
            {
                "locationId": LOC,
                "page": page,
                "pageLimit": 100,
                "filters": filters,
            },
        )
        if st != 200:
            print("search ERR", st, str(d)[:160])
            break
        batch = d.get("contacts") or []
        out.extend(batch)
        total = d.get("total") or 0
        if not batch or page * 100 >= total:
            break
        page += 1
        time.sleep(0.05)
    return out


def load_user_names() -> dict[str, str]:
    names = dict(FLA_USERS)
    st, d = req("GET", BASE + "/users/?locationId=" + urllib.parse.quote(LOC))
    if st == 200:
        for u in d.get("users") or []:
            uid = u.get("id")
            if not uid:
                continue
            name = (
                u.get("name")
                or " ".join(
                    x
                    for x in [u.get("firstName") or "", u.get("lastName") or ""]
                    if x
                ).strip()
                or u.get("email")
                or uid
            )
            names[uid] = name
    return names


def parse_ts(val):
    if val is None:
        return None
    if isinstance(val, (int, float)):
        ts = float(val)
        if ts > 10_000_000_000:
            ts /= 1000.0
        return datetime.fromtimestamp(ts, tz=timezone.utc)
    s = str(val).strip()
    if not s:
        return None
    try:
        if s.endswith("Z"):
            s = s[:-1] + "+00:00"
        return datetime.fromisoformat(s)
    except Exception:
        return None


def fmt_brt(dt: datetime | None) -> str:
    if not dt:
        return ""
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(BRT).strftime("%Y-%m-%d %H:%M")


def day_brt(dt: datetime | None) -> str:
    if not dt:
        return "sem-data"
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(BRT).strftime("%Y-%m-%d")


def safe_name(s: str) -> str:
    s = (s or "sem-nome").strip().lower()
    s = re.sub(r"[^\w\-]+", "_", s, flags=re.UNICODE)
    s = re.sub(r"_+", "_", s).strip("_")
    return (s or "sem-nome")[:60]


def classify_message(m: dict, user_names: dict[str, str]) -> tuple[str, str]:
    """Retorna (origem, detalhe). Origem: CLIENTE|HUMANO|BOT|AUTOMAÇÃO|SISTEMA."""
    direction = (m.get("direction") or "").lower()
    mtype = str(m.get("messageType") or "")
    source = str(m.get("source") or "").lower().strip()
    uid = (m.get("userId") or "").strip()
    body = (m.get("body") or "").strip()

    if direction == "inbound":
        return "CLIENTE", "inbound"

    if mtype.startswith("TYPE_ACTIVITY") or body.lower().startswith("opportunity "):
        return "SISTEMA", mtype or "activity"

    if "ai" in source or "bot" in source or "agent" in source:
        return "BOT", source or mtype

    if source == "workflow":
        # workflows da Pello incluem chatbot de triagem
        return "AUTOMAÇÃO", "workflow"

    if uid:
        return "HUMANO", user_names.get(uid, uid)

    if source in ("app", "api", "campaign", "bulk"):
        return "AUTOMAÇÃO", source or "app"

    return "SISTEMA", source or mtype or "outro"


def all_messages(conversation_id: str):
    rows = []
    seen = set()
    last_id = None
    for _ in range(200):
        url = f"{BASE}/conversations/{conversation_id}/messages?limit=100"
        if last_id:
            url += "&lastMessageId=" + urllib.parse.quote(last_id)
        st, d = req("GET", url)
        if st != 200:
            print("  msgs ERR", conversation_id, st, str(d)[:120])
            break
        block = d.get("messages") or {}
        batch = (
            block.get("messages")
            if isinstance(block, dict)
            else (d.get("messages") or [])
        )
        if not isinstance(batch, list):
            batch = []
        for m in batch:
            mid = m.get("id")
            if mid and mid in seen:
                continue
            if mid:
                seen.add(mid)
            rows.append(m)
        next_page = block.get("nextPage") if isinstance(block, dict) else False
        last_id = block.get("lastMessageId") if isinstance(block, dict) else None
        if not next_page or not last_id or not batch:
            break
        time.sleep(0.08)
    rows.sort(
        key=lambda m: parse_ts(m.get("dateAdded") or m.get("dateUpdated"))
        or datetime.min.replace(tzinfo=timezone.utc)
    )
    return rows


def write_contact_md(path: Path, contact: dict, messages: list, user_names: dict):
    name = contact.get("contactName") or contact.get("name") or "Sem nome"
    email = contact.get("email") or ""
    tags = contact.get("tags") or []
    assigned = contact.get("assignedTo") or ""
    assigned_name = user_names.get(assigned, assigned) if assigned else ""
    lines = [
        f"# {name}",
        "",
        f"- E-mail: {email}",
        f"- Contact ID: {contact.get('id')}",
        f"- Tags: {', '.join(tags) if tags else '—'}",
        f"- Responsável: {assigned_name or '—'}",
        f"- Mensagens: {len(messages)}",
        "",
        "---",
        "",
    ]
    for m in messages:
        dt = parse_ts(m.get("dateAdded") or m.get("dateUpdated"))
        body = (m.get("body") or "").strip() or "[sem texto]"
        if m.get("attachments"):
            body += "\n[anexos: " + str(len(m.get("attachments"))) + "]"
        origem, detalhe = classify_message(m, user_names)
        lines.append(f"## {fmt_brt(dt)} (BRT) | {origem} | {detalhe}")
        lines.append("")
        lines.append(body)
        lines.append("")
    path.write_text("\n".join(lines), encoding="utf-8")


def write_viewer_files():
    VIEWER_DIR.mkdir(parents=True, exist_ok=True)
    (VIEWER_DIR / "data").mkdir(parents=True, exist_ok=True)

    (VIEWER_DIR / "index.html").write_text(
        """<!DOCTYPE html>
<html lang="pt-BR">
  <head>
    <meta charset="UTF-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1" />
    <title>Flamengo — Conversas</title>
    <link rel="stylesheet" href="styles.css" />
  </head>
  <body>
    <div class="app">
      <aside class="sidebar">
        <header class="sidebar-head">
          <h1>Flamengo (FLA)</h1>
          <p class="sub" id="stats">Carregando…</p>
          <div class="filters">
            <input type="search" id="search" placeholder="Nome, e-mail ou mensagem…" autocomplete="off" />
            <div class="filter-row">
              <label>De <input type="date" id="date-from" /></label>
              <label>Até <input type="date" id="date-to" /></label>
            </div>
            <select id="filter-tag">
              <option value="">Todas as tags</option>
            </select>
            <select id="filter-origem">
              <option value="">Todas as origens</option>
              <option value="CLIENTE">Cliente</option>
              <option value="HUMANO">Humano</option>
              <option value="BOT">Bot / IA</option>
              <option value="AUTOMAÇÃO">Automação</option>
              <option value="SISTEMA">Sistema</option>
            </select>
            <label class="check">
              <input type="checkbox" id="filter-replied" />
              Só com resposta do cliente
            </label>
          </div>
        </header>
        <ul class="contact-list" id="contact-list" role="listbox"></ul>
      </aside>
      <main class="chat" id="chat-panel">
        <div class="chat-empty" id="chat-empty">
          <div class="empty-icon">💬</div>
          <p>Selecione um cliente na lista para ver a conversa.</p>
        </div>
        <div class="chat-active hidden" id="chat-active">
          <header class="chat-head">
            <div class="avatar" id="chat-avatar" aria-hidden="true"></div>
            <div class="chat-head-text">
              <strong id="chat-name"></strong>
              <span id="chat-meta"></span>
              <div class="tags" id="chat-tags"></div>
            </div>
            <span class="badge" id="chat-count"></span>
          </header>
          <div class="messages" id="messages" role="log"></div>
        </div>
      </main>
    </div>
    <script src="app.js" type="module"></script>
  </body>
</html>
""",
        encoding="utf-8",
    )

    (VIEWER_DIR / "styles.css").write_text(
        """:root {
  --bg-app: #111b21;
  --bg-sidebar: #111b21;
  --bg-sidebar-hover: #202c33;
  --bg-sidebar-active: #2a3942;
  --bg-chat: #0b141a;
  --bubble-in: #202c33;
  --bubble-out: #005c4b;
  --text: #e9edef;
  --text-muted: #8696a0;
  --accent: #00a884;
  --border: #222d34;
  --tag: #1f3a33;
  --font: "Segoe UI", system-ui, -apple-system, sans-serif;
}
*, *::before, *::after { box-sizing: border-box; }
html, body { height: 100%; margin: 0; font-family: var(--font); background: var(--bg-app); color: var(--text); }
.app { display: grid; grid-template-columns: minmax(300px, 400px) 1fr; height: 100vh; max-height: 100dvh; }
.sidebar { display: flex; flex-direction: column; border-right: 1px solid var(--border); background: var(--bg-sidebar); min-height: 0; }
.sidebar-head { padding: 1rem 1rem 0.75rem; border-bottom: 1px solid var(--border); }
.sidebar-head h1 { margin: 0; font-size: 1.2rem; font-weight: 600; }
.sub { margin: 0.25rem 0 0.75rem; font-size: 0.8rem; color: var(--text-muted); }
.filters { display: flex; flex-direction: column; gap: 0.45rem; }
.filters input[type="search"], .filters select, .filters input[type="date"] {
  width: 100%; padding: 0.45rem 0.65rem; border: none; border-radius: 8px;
  background: var(--bg-sidebar-active); color: var(--text); font-size: 0.85rem;
}
.filter-row { display: grid; grid-template-columns: 1fr 1fr; gap: 0.4rem; }
.filter-row label { font-size: 0.72rem; color: var(--text-muted); display: flex; flex-direction: column; gap: 0.2rem; }
.check { font-size: 0.8rem; color: var(--text-muted); display: flex; align-items: center; gap: 0.4rem; }
.contact-list { list-style: none; margin: 0; padding: 0; overflow-y: auto; flex: 1; }
.contact-item {
  display: grid; grid-template-columns: 44px 1fr; gap: 0.65rem; padding: 0.6rem 1rem;
  cursor: pointer; border-bottom: 1px solid var(--border); transition: background 0.12s;
}
.contact-item:hover { background: var(--bg-sidebar-hover); }
.contact-item.active { background: var(--bg-sidebar-active); }
.contact-avatar {
  width: 44px; height: 44px; border-radius: 50%; background: linear-gradient(135deg, #3a4a55, #1f2c34);
  display: flex; align-items: center; justify-content: center; font-weight: 600; color: var(--accent);
}
.contact-body { min-width: 0; }
.contact-row { display: flex; justify-content: space-between; gap: 0.5rem; align-items: baseline; }
.contact-name { font-weight: 500; white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.contact-time { font-size: 0.7rem; color: var(--text-muted); flex-shrink: 0; }
.contact-preview { margin: 0.15rem 0 0; font-size: 0.78rem; color: var(--text-muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.contact-tags { margin-top: 0.2rem; display: flex; flex-wrap: wrap; gap: 0.2rem; }
.tag-chip {
  font-size: 0.65rem; padding: 0.1rem 0.35rem; border-radius: 999px;
  background: var(--tag); color: var(--accent);
}
.chat { display: flex; flex-direction: column; min-height: 0; background: var(--bg-chat); }
.hidden { display: none !important; }
.chat-empty {
  flex: 1; display: flex; flex-direction: column; align-items: center; justify-content: center;
  color: var(--text-muted); padding: 2rem; text-align: center;
}
.empty-icon { font-size: 3rem; opacity: 0.5; margin-bottom: 0.5rem; }
.chat-active { flex: 1; display: flex; flex-direction: column; min-height: 0; }
.chat-head {
  display: flex; align-items: center; gap: 0.75rem; padding: 0.65rem 1.25rem;
  background: var(--bg-sidebar); border-bottom: 1px solid var(--border);
}
.chat-head .avatar {
  width: 40px; height: 40px; border-radius: 50%; background: var(--bg-sidebar-active);
  display: flex; align-items: center; justify-content: center; font-weight: 600; color: var(--accent);
}
.chat-head-text { flex: 1; min-width: 0; display: flex; flex-direction: column; gap: 0.15rem; }
.chat-head-text strong { white-space: nowrap; overflow: hidden; text-overflow: ellipsis; }
.chat-head-text > span { font-size: 0.78rem; color: var(--text-muted); }
.tags { display: flex; flex-wrap: wrap; gap: 0.25rem; }
.badge { font-size: 0.75rem; color: var(--text-muted); background: var(--bg-sidebar-active); padding: 0.2rem 0.5rem; border-radius: 999px; }
.messages { flex: 1; overflow-y: auto; padding: 1rem 4%; display: flex; flex-direction: column; gap: 0.35rem; }
.msg-row { display: flex; width: 100%; }
.msg-row.in { justify-content: flex-start; }
.msg-row.out { justify-content: flex-end; }
.bubble {
  max-width: min(540px, 85%); padding: 0.45rem 0.65rem 0.35rem; border-radius: 8px;
  box-shadow: 0 1px 0.5px rgba(0,0,0,0.15);
}
.msg-row.in .bubble { background: var(--bubble-in); border-top-left-radius: 2px; }
.msg-row.out .bubble { background: var(--bubble-out); border-top-right-radius: 2px; }
.msg-row.sistema .bubble { background: #1a2330; opacity: 0.85; max-width: min(420px, 90%); }
.bubble-text { margin: 0; font-size: 0.92rem; line-height: 1.45; white-space: pre-wrap; word-break: break-word; }
.bubble-meta { display: flex; justify-content: flex-end; align-items: center; gap: 0.4rem; margin-top: 0.2rem; flex-wrap: wrap; }
.bubble-origem {
  font-size: 0.65rem; text-transform: uppercase; letter-spacing: 0.03em;
  padding: 0.05rem 0.35rem; border-radius: 4px; background: rgba(0,0,0,0.25); color: rgba(233,237,239,0.85);
}
.bubble-time { font-size: 0.68rem; color: rgba(233,237,239,0.65); }
.day-sep {
  align-self: center; margin: 0.75rem 0; padding: 0.25rem 0.75rem; font-size: 0.75rem;
  color: var(--text-muted); background: var(--bg-sidebar-active); border-radius: 8px;
}
.load-error { padding: 1.5rem; color: #f87171; line-height: 1.5; font-size: 0.9rem; }
@media (max-width: 720px) { .app { grid-template-columns: 1fr; } }
""",
        encoding="utf-8",
    )

    (VIEWER_DIR / "app.js").write_text(
        r"""const DATA_URL = "data/conversas.json";
const $ = (sel) => document.querySelector(sel);

const els = {
  stats: $("#stats"),
  search: $("#search"),
  dateFrom: $("#date-from"),
  dateTo: $("#date-to"),
  tag: $("#filter-tag"),
  origem: $("#filter-origem"),
  replied: $("#filter-replied"),
  list: $("#contact-list"),
  empty: $("#chat-empty"),
  active: $("#chat-active"),
  name: $("#chat-name"),
  meta: $("#chat-meta"),
  tags: $("#chat-tags"),
  count: $("#chat-count"),
  avatar: $("#chat-avatar"),
  messages: $("#messages"),
};

let data = { contatos: [], tags: [] };
let selectedId = null;

function initials(name) {
  const parts = (name || "?").trim().split(/\s+/).filter(Boolean);
  if (!parts.length) return "?";
  if (parts.length === 1) return parts[0].slice(0, 2).toUpperCase();
  return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
}

function previewText(text) {
  const t = (text || "").replace(/\s+/g, " ").trim();
  return t.length <= 72 ? t : t.slice(0, 69) + "…";
}

function dayKey(t) {
  return (t || "").slice(0, 10);
}

function formatDay(key) {
  if (!key || key.length < 10) return key;
  const [y, m, d] = key.split("-");
  return `${d}/${m}/${y}`;
}

function formatTime(t) {
  if (!t) return "";
  const part = t.includes(" ") ? t.split(" ")[1] : t;
  return part.slice(0, 5);
}

function escapeHtml(s) {
  return String(s)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;");
}

function contactMatches(c) {
  const q = els.search.value.trim().toLowerCase();
  if (q) {
    const last = c.mensagens[c.mensagens.length - 1];
    const hay = `${c.nome} ${c.email} ${last?.texto || ""}`.toLowerCase();
    if (!hay.includes(q)) return false;
  }
  const tag = els.tag.value;
  if (tag && !(c.tags || []).includes(tag)) return false;

  const origem = els.origem.value;
  if (origem && !(c.mensagens || []).some((m) => m.origem === origem)) return false;

  if (els.replied.checked && !(c.mensagens || []).some((m) => m.origem === "CLIENTE")) {
    return false;
  }

  const from = els.dateFrom.value;
  const to = els.dateTo.value;
  if (from || to) {
    const inRange = (c.mensagens || []).some((m) => {
      const d = dayKey(m.t);
      if (from && d < from) return false;
      if (to && d > to) return false;
      return true;
    });
    if (!inRange) return false;
  }
  return true;
}

function filteredMsgs(c) {
  const origem = els.origem.value;
  const from = els.dateFrom.value;
  const to = els.dateTo.value;
  return (c.mensagens || []).filter((m) => {
    if (origem && m.origem !== origem) return false;
    const d = dayKey(m.t);
    if (from && d < from) return false;
    if (to && d > to) return false;
    return true;
  });
}

function renderList() {
  els.list.innerHTML = "";
  const filtered = data.contatos.filter(contactMatches);
  els.stats.textContent = `${filtered.length} de ${data.totalContatos} clientes · ${data.totalMensagens} msgs`;

  for (const c of filtered) {
    const li = document.createElement("li");
    li.className = "contact-item" + (c.contactId === selectedId ? " active" : "");
    li.dataset.id = c.contactId;
    const last = c.mensagens[c.mensagens.length - 1];
    const tagHtml = (c.tags || [])
      .slice(0, 3)
      .map((t) => `<span class="tag-chip">${escapeHtml(t)}</span>`)
      .join("");
    li.innerHTML = `
      <div class="contact-avatar">${escapeHtml(initials(c.nome))}</div>
      <div class="contact-body">
        <div class="contact-row">
          <span class="contact-name">${escapeHtml(c.nome)}</span>
          <span class="contact-time">${escapeHtml(formatTime(c.data_ultima))}</span>
        </div>
        <p class="contact-preview">${escapeHtml(previewText(last?.texto))}</p>
        <div class="contact-tags">${tagHtml}</div>
      </div>
    `;
    li.addEventListener("click", () => selectContact(c.contactId));
    els.list.appendChild(li);
  }
}

function selectContact(id) {
  selectedId = id;
  const c = data.contatos.find((x) => x.contactId === id);
  if (!c) return;

  els.empty.classList.add("hidden");
  els.active.classList.remove("hidden");
  els.name.textContent = c.nome;
  const bits = [];
  if (c.email) bits.push(c.email);
  if (c.responsavel) bits.push(c.responsavel);
  els.meta.textContent = bits.join(" · ") || c.contactId;
  els.count.textContent = `${c.qtd_mensagens} msgs`;
  els.avatar.textContent = initials(c.nome);
  els.tags.innerHTML = (c.tags || [])
    .map((t) => `<span class="tag-chip">${escapeHtml(t)}</span>`)
    .join("");

  const msgs = filteredMsgs(c);
  els.messages.innerHTML = "";
  let lastDay = null;
  for (const m of msgs) {
    const dk = dayKey(m.t);
    if (dk !== lastDay) {
      lastDay = dk;
      const sep = document.createElement("div");
      sep.className = "day-sep";
      sep.textContent = formatDay(dk);
      els.messages.appendChild(sep);
    }
    const isIn = m.origem === "CLIENTE";
    const isSys = m.origem === "SISTEMA";
    const row = document.createElement("div");
    row.className = "msg-row " + (isIn ? "in" : "out") + (isSys ? " sistema" : "");
    const label =
      m.origem === "HUMANO" && m.detalhe
        ? `HUMANO · ${m.detalhe}`
        : m.origem + (m.detalhe && m.origem !== "CLIENTE" ? `` : "");
    const bubble = document.createElement("div");
    bubble.className = "bubble";
    bubble.innerHTML = `
      <p class="bubble-text">${escapeHtml(m.texto)}</p>
      <div class="bubble-meta">
        <span class="bubble-origem">${escapeHtml(label)}</span>
        <span class="bubble-time">${escapeHtml(formatTime(m.t))}</span>
      </div>
    `;
    row.appendChild(bubble);
    els.messages.appendChild(row);
  }
  els.messages.scrollTop = els.messages.scrollHeight;
  renderList();
}

function fillTagOptions() {
  const tags = data.tags || [];
  for (const t of tags) {
    const opt = document.createElement("option");
    opt.value = t;
    opt.textContent = t;
    els.tag.appendChild(opt);
  }
}

async function load() {
  try {
    const res = await fetch(DATA_URL);
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    data = await res.json();
    fillTagOptions();
    renderList();
    if (data.contatos.length) selectContact(data.contatos[0].contactId);
  } catch (e) {
    els.stats.textContent = "Erro ao carregar dados";
    els.list.innerHTML = `<li class="load-error">Abra com servidor local na pasta viewer:<br><code>python -m http.server 8765</code><br>depois <code>http://localhost:8765</code></li>`;
    console.error(e);
  }
}

["input", "change"].forEach((ev) => {
  els.search.addEventListener(ev, renderList);
  els.dateFrom.addEventListener(ev, () => {
    renderList();
    if (selectedId) selectContact(selectedId);
  });
  els.dateTo.addEventListener(ev, () => {
    renderList();
    if (selectedId) selectContact(selectedId);
  });
  els.tag.addEventListener(ev, renderList);
  els.origem.addEventListener(ev, () => {
    renderList();
    if (selectedId) selectContact(selectedId);
  });
  els.replied.addEventListener(ev, renderList);
});

load();
""",
        encoding="utf-8",
    )

    (VIEWER_DIR / "abrir.bat").write_text(
        """@echo off
cd /d "%~dp0"
echo Abrindo servidor em http://localhost:8765
start "" "http://localhost:8765"
python -m http.server 8765
""",
        encoding="utf-8",
    )


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    CONV_DIR.mkdir(parents=True, exist_ok=True)
    for old in CONV_DIR.glob("*.md"):
        old.unlink()

    write_viewer_files()
    user_names = load_user_names()
    print("users cached", len(user_names))

    by_id: dict[str, dict] = {}
    # tag flamengo
    for c in search_contacts(
        [{"field": "tags", "operator": "eq", "value": TAG_FLA}]
    ):
        if c.get("id"):
            by_id[c["id"]] = c
    print("apos tag", TAG_FLA, len(by_id))

    for uid, label in FLA_USERS.items():
        for field in ("assignedTo", "followers"):
            batch = search_contacts(
                [{"field": field, "operator": "eq", "value": uid}]
            )
            print(label, field, len(batch))
            for c in batch:
                if c.get("id"):
                    by_id[c["id"]] = c

    contacts = list(by_id.values())
    print("contatos unicos", len(contacts))

    index_rows = []
    msg_rows = []
    viewer_contacts = []
    by_day = defaultdict(list)
    total_msgs = 0
    with_conv = 0
    errors = 0
    all_dates = []
    all_tags = set()

    for i, c in enumerate(contacts, 1):
        cid = c["id"]
        name = c.get("contactName") or c.get("name") or "Sem nome"
        email = (c.get("email") or "").strip()
        tags = list(c.get("tags") or [])
        for t in tags:
            all_tags.add(t)
        assigned = c.get("assignedTo") or ""
        assigned_name = user_names.get(assigned, assigned) if assigned else ""
        print(f"[{i}/{len(contacts)}] {name}")

        st, d = req(
            "GET",
            BASE
            + "/conversations/search?"
            + urllib.parse.urlencode(
                {"locationId": LOC, "contactId": cid, "limit": 20}
            ),
        )
        time.sleep(0.12)
        if st != 200:
            errors += 1
            print("  conv ERR", st, str(d)[:120])
            continue

        convs = d.get("conversations") or []
        messages = []
        for conv in convs:
            cvid = conv.get("id")
            if not cvid:
                continue
            messages.extend(all_messages(cvid))
            time.sleep(0.12)

        seen = set()
        uniq = []
        for m in messages:
            mid = m.get("id")
            if mid and mid in seen:
                continue
            if mid:
                seen.add(mid)
            uniq.append(m)
        uniq.sort(
            key=lambda m: parse_ts(m.get("dateAdded") or m.get("dateUpdated"))
            or datetime.min.replace(tzinfo=timezone.utc)
        )
        messages = uniq

        if messages:
            with_conv += 1
        total_msgs += len(messages)

        first_dt = parse_ts(messages[0].get("dateAdded")) if messages else None
        last_dt = parse_ts(messages[-1].get("dateAdded")) if messages else None
        if first_dt:
            all_dates.append(first_dt)
        if last_dt:
            all_dates.append(last_dt)

        fname = f"{safe_name(name)}_{cid}.md"
        fpath = CONV_DIR / fname
        write_contact_md(fpath, c, messages, user_names)

        viewer_msgs = []
        for m in messages:
            dt = parse_ts(m.get("dateAdded") or m.get("dateUpdated"))
            body = (m.get("body") or "").strip() or "[sem texto]"
            if m.get("attachments"):
                body += "\n[anexos: " + str(len(m.get("attachments"))) + "]"
            origem, detalhe = classify_message(m, user_names)
            msg_rows.append(
                {
                    "nome": name,
                    "email": email,
                    "contactId": cid,
                    "tags": "|".join(tags),
                    "responsavel": assigned_name,
                    "data_hora_brt": fmt_brt(dt),
                    "origem": origem,
                    "detalhe": detalhe,
                    "messageType": m.get("messageType") or "",
                    "source": m.get("source") or "",
                    "mensagem": body,
                }
            )
            viewer_msgs.append(
                {
                    "t": fmt_brt(dt),
                    "origem": origem,
                    "detalhe": detalhe,
                    "texto": body,
                }
            )

        index_rows.append(
            {
                "nome": name,
                "email": email,
                "contactId": cid,
                "tags": "|".join(tags),
                "responsavel": assigned_name,
                "qtd_mensagens": len(messages),
                "data_primeira": fmt_brt(first_dt),
                "data_ultima": fmt_brt(last_dt),
                "arquivo": f"conversas/{fname}",
            }
        )
        by_day[day_brt(last_dt)].append(index_rows[-1])
        viewer_contacts.append(
            {
                "contactId": cid,
                "nome": name,
                "email": email,
                "tags": tags,
                "responsavel": assigned_name,
                "data_ultima": fmt_brt(last_dt),
                "qtd_mensagens": len(messages),
                "mensagens": viewer_msgs,
            }
        )

    index_rows.sort(key=lambda r: r["data_ultima"] or "", reverse=True)
    msg_rows.sort(key=lambda r: (r["nome"].lower(), r["data_hora_brt"], r["origem"]))
    viewer_contacts.sort(key=lambda x: x["data_ultima"] or "", reverse=True)

    csv_path = OUT_DIR / "indice.csv"
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "nome",
                "email",
                "contactId",
                "tags",
                "responsavel",
                "qtd_mensagens",
                "data_primeira",
                "data_ultima",
                "arquivo",
            ],
        )
        w.writeheader()
        w.writerows(index_rows)

    msg_csv = OUT_DIR / "mensagens-por-cliente.csv"
    with msg_csv.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(
            f,
            fieldnames=[
                "nome",
                "email",
                "contactId",
                "tags",
                "responsavel",
                "data_hora_brt",
                "origem",
                "detalhe",
                "messageType",
                "source",
                "mensagem",
            ],
        )
        w.writeheader()
        w.writerows(msg_rows)

    resumo = [
        "# Resumo Flamengo (FLA) — conversas Franchising",
        "",
        f"- Contatos: {len(contacts)}",
        f"- Com mensagens: {with_conv}",
        f"- Total mensagens: {total_msgs}",
        f"- Erros: {errors}",
        "- Telefone: **não exportado**",
    ]
    if all_dates:
        resumo.append(
            f"- Periodo: {fmt_brt(min(all_dates))} → {fmt_brt(max(all_dates))} (BRT)"
        )
    resumo += ["", "Agrupado pela data da **ultima** mensagem.", ""]
    for day in sorted(by_day.keys(), reverse=True):
        rows = sorted(by_day[day], key=lambda x: x["nome"].lower())
        resumo.append(f"## {day} ({len(rows)})")
        resumo.append("")
        for r in rows:
            resumo.append(
                f"- **{r['nome']}** | {r['qtd_mensagens']} msgs | tags: {r['tags'] or '—'} | `{r['arquivo']}`"
            )
        resumo.append("")
    (OUT_DIR / "resumo-por-data.md").write_text("\n".join(resumo), encoding="utf-8")

    viewer_payload = {
        "titulo": "Pello Menos Flamengo (FLA) — Franchising",
        "totalContatos": len(viewer_contacts),
        "totalMensagens": total_msgs,
        "tags": sorted(all_tags, key=str.lower),
        "contatos": viewer_contacts,
    }
    (VIEWER_DIR / "data" / "conversas.json").write_text(
        json.dumps(viewer_payload, ensure_ascii=False, indent=0), encoding="utf-8"
    )

    if ZIP_PATH.exists():
        ZIP_PATH.unlink()
    with zipfile.ZipFile(ZIP_PATH, "w", compression=zipfile.ZIP_DEFLATED) as zf:
        zf.write(csv_path, arcname="indice.csv")
        zf.write(msg_csv, arcname="mensagens-por-cliente.csv")
        zf.write(OUT_DIR / "resumo-por-data.md", arcname="resumo-por-data.md")
        for md in sorted(CONV_DIR.glob("*.md")):
            zf.write(md, arcname=f"conversas/{md.name}")
        for rel in (
            "viewer/index.html",
            "viewer/styles.css",
            "viewer/app.js",
            "viewer/abrir.bat",
            "viewer/data/conversas.json",
        ):
            p = OUT_DIR / rel
            if p.exists():
                zf.write(p, arcname=rel)

    summary = {
        "contatos": len(contacts),
        "com_mensagens": with_conv,
        "total_mensagens": total_msgs,
        "erros": errors,
        "periodo_inicio": fmt_brt(min(all_dates)) if all_dates else None,
        "periodo_fim": fmt_brt(max(all_dates)) if all_dates else None,
        "pasta": str(OUT_DIR),
        "zip": str(ZIP_PATH),
        "viewer": str(VIEWER_DIR),
        "sem_telefone": True,
    }
    (OUT_DIR / "summary.json").write_text(
        json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8"
    )
    print("SUMMARY", summary)


if __name__ == "__main__":
    main()
