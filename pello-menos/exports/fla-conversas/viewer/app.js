const DATA_URL = "data/conversas.json";
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
