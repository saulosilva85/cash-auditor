/* Cash Auditor — frontend SPA */
(() => {
  "use strict";

  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => Array.from(document.querySelectorAll(sel));

  const state = {
    view: "dashboard",
    agencias: [],
    contadoras: [],
    charts: {},
    feed: [],
    periodo: {
      dashboard: { inicio: "", fim: "" },
      contagens: { inicio: "", fim: "" },
    },
  };

  const VIEW_META = {
    dashboard: ["Visão Geral", "Monitoramento em tempo real da rede de agências"],
    agencias: ["Agências", "Cadastro das agências da rede estadual"],
    contadoras: ["Contadoras", "Cadastro das máquinas contadoras de cédulas"],
    contagens: ["Contagens", "Histórico de contagens recebidas"],
  };

  // ---------------- helpers ----------------
  const brl = (v) =>
    (v || 0).toLocaleString("pt-BR", { style: "currency", currency: "BRL", maximumFractionDigits: 0 });
  const num = (v) => (v || 0).toLocaleString("pt-BR");
  const fmtTime = (iso) => {
    try { return new Date(iso).toLocaleTimeString("pt-BR"); } catch { return "—"; }
  };
  const fmtDateTime = (iso) => {
    try { return new Date(iso).toLocaleString("pt-BR"); } catch { return "—"; }
  };
  const toISODate = (d) => {
    const tz = d.getTimezoneOffset() * 60000;
    return new Date(d - tz).toISOString().slice(0, 10);
  };
  // Converte "AAAA-MM-DD" em "DD/MM/AAAA" para exibição.
  const fmtDiaBR = (iso) => {
    const [y, m, d] = (iso || "").split("-");
    return d ? `${d}/${m}/${y}` : iso;
  };
  // Constrói "?inicio=...&fim=..." a partir de um período {inicio, fim}.
  function periodoQuery(p) {
    const params = new URLSearchParams();
    if (p.inicio) params.set("inicio", p.inicio);
    if (p.fim) params.set("fim", p.fim);
    const s = params.toString();
    return s ? `&${s}` : "";
  }
  // Resolve um preset ("hoje" | "7" | "30" | "mes") em {inicio, fim} (ISO).
  function resolvePreset(preset) {
    const hoje = new Date();
    const fim = toISODate(hoje);
    if (preset === "hoje") return { inicio: fim, fim };
    if (preset === "mes") {
      const ini = new Date(hoje.getFullYear(), hoje.getMonth(), 1);
      return { inicio: toISODate(ini), fim };
    }
    const dias = parseInt(preset, 10) || 7;
    const ini = new Date(hoje);
    ini.setDate(ini.getDate() - (dias - 1));
    return { inicio: toISODate(ini), fim };
  }

  async function api(path, options = {}) {
    const res = await fetch(`/api${path}`, {
      headers: { "Content-Type": "application/json" },
      ...options,
    });
    if (!res.ok) {
      let detail = res.statusText;
      try {
        const body = await res.json();
        if (typeof body.detail === "string") detail = body.detail;
        else if (Array.isArray(body.detail)) detail = body.detail.map((e) => e.msg).join("; ");
        else if (body.detail) detail = JSON.stringify(body.detail);
      } catch {}
      throw new Error(detail);
    }
    if (res.status === 204) return null;
    return res.json();
  }

  // ---------------- toasts ----------------
  function toast(title, sub, type = "ok") {
    const el = document.createElement("div");
    el.className = `toast ${type === "error" ? "error" : ""}`;
    el.innerHTML = `<div class="toast-title">${title}</div>${sub ? `<div class="toast-sub">${sub}</div>` : ""}`;
    $("#toasts").appendChild(el);
    setTimeout(() => { el.style.opacity = "0"; el.style.transform = "translateX(20px)"; }, 3600);
    setTimeout(() => el.remove(), 4100);
  }

  // ---------------- navigation ----------------
  function setView(view) {
    state.view = view;
    $$(".nav-item").forEach((b) => b.classList.toggle("active", b.dataset.view === view));
    $$(".view").forEach((v) => v.classList.add("hidden"));
    $(`#view-${view}`).classList.remove("hidden");
    const [title, sub] = VIEW_META[view];
    $("#view-title").textContent = title;
    $("#view-sub").textContent = sub;
    refresh();
  }

  // ---------------- dashboard ----------------
  async function loadDashboard() {
    const p = state.periodo.dashboard;
    const d = await api(`/dashboard/resumo?_=1${periodoQuery(p)}`);
    $("#kpi-valor").textContent = brl(d.valor_total_hoje);
    $("#kpi-valor-geral").textContent = `Acumulado: ${brl(d.valor_total_geral)}`;
    $("#kpi-cedulas").textContent = num(d.total_cedulas_hoje);
    $("#kpi-rejeitadas").textContent = `${num(d.cedulas_rejeitadas_hoje)} rejeitadas`;
    $("#kpi-contagens").textContent = num(d.total_contagens_hoje);
    $("#kpi-online").textContent = d.contadoras_online;
    $("#kpi-total-contadoras").textContent = `/${d.total_contadoras}`;
    $("#kpi-agencias").textContent = `${d.total_agencias} agências`;

    // Rótulos dinâmicos conforme o período selecionado.
    const ehHoje = d.periodo_label === "hoje";
    const suf = ehHoje ? "hoje" : "no período";
    $("#lbl-valor").textContent = `Valor contado ${suf}`;
    $("#lbl-cedulas").textContent = `Cédulas ${suf}`;
    $("#lbl-contagens").textContent = `Contagens ${suf}`;
    $("#title-horaria").textContent = d.serie_titulo;
    $("#title-denom").textContent = `Cédulas por denominação (${d.periodo_label})`;
    $("#title-ranking").textContent = `Ranking de agências (${d.periodo_label})`;
    $("#dash-periodo").textContent = `Período: ${d.periodo_label}`;

    renderRanking(d.top_agencias);
    renderChartHoraria(d.serie_horaria);
    renderChartDenom(d.por_denominacao);
  }

  function renderRanking(rows) {
    const tb = $("#tbl-ranking");
    if (!rows.length) { tb.innerHTML = `<tr><td colspan="5" class="empty">Sem contagens no período</td></tr>`; return; }
    tb.innerHTML = rows.map((r) => `
      <tr>
        <td><strong>${r.codigo}</strong> · ${r.nome}</td>
        <td>${r.regiao || "—"}</td>
        <td class="num">${brl(r.valor_total)}</td>
        <td class="num">${num(r.total_cedulas)}</td>
        <td class="num">${r.contadoras_online}/${r.total_contadoras}</td>
      </tr>`).join("");
  }

  function chartTheme() {
    return { grid: "rgba(36,49,84,0.6)", tick: "#8b97b8" };
  }

  function renderChartHoraria(serie) {
    const ctx = $("#chart-horaria");
    if (!ctx || !window.Chart) return;
    const t = chartTheme();
    const data = {
      labels: serie.map((s) => s.hora),
      datasets: [{
        label: "Valor (R$)",
        data: serie.map((s) => s.valor),
        borderColor: "#5b8cff",
        backgroundColor: (c) => {
          const { ctx: cc, chartArea } = c.chart;
          if (!chartArea) return "rgba(91,140,255,0.2)";
          const g = cc.createLinearGradient(0, chartArea.top, 0, chartArea.bottom);
          g.addColorStop(0, "rgba(91,140,255,0.45)");
          g.addColorStop(1, "rgba(91,140,255,0)");
          return g;
        },
        fill: true, tension: 0.4, pointRadius: 0, borderWidth: 2.5,
      }],
    };
    const opts = {
      responsive: true, maintainAspectRatio: false,
      plugins: { legend: { display: false }, tooltip: { callbacks: { label: (i) => brl(i.parsed.y) } } },
      scales: {
        x: { grid: { color: t.grid }, ticks: { color: t.tick, maxTicksLimit: 8 } },
        y: { grid: { color: t.grid }, ticks: { color: t.tick, callback: (v) => "R$ " + (v / 1000) + "k" } },
      },
    };
    upsertChart("horaria", ctx, "line", data, opts);
  }

  function renderChartDenom(denoms) {
    const ctx = $("#chart-denom");
    if (!ctx || !window.Chart) return;
    const t = chartTheme();
    const palette = ["#19c39c", "#5b8cff", "#f7c948", "#ff8b96", "#a78bfa", "#38bdf8", "#fb923c"];
    const data = {
      labels: denoms.map((d) => "R$ " + d.denominacao),
      datasets: [{
        label: "Cédulas",
        data: denoms.map((d) => d.quantidade),
        backgroundColor: denoms.map((_, i) => palette[i % palette.length]),
        borderRadius: 8, borderSkipped: false,
      }],
    };
    const opts = {
      responsive: true, maintainAspectRatio: false,
      plugins: {
        legend: { display: false },
        tooltip: { callbacks: { label: (i) => `${num(i.parsed.y)} cédulas` } },
      },
      scales: {
        x: { grid: { display: false }, ticks: { color: t.tick } },
        y: { grid: { color: t.grid }, ticks: { color: t.tick } },
      },
    };
    upsertChart("denom", ctx, "bar", data, opts);
  }

  function upsertChart(key, ctx, type, data, options) {
    if (state.charts[key]) {
      state.charts[key].data = data;
      state.charts[key].update();
    } else {
      state.charts[key] = new Chart(ctx, { type, data, options });
    }
  }

  // ---------------- live feed ----------------
  function pushFeed(c, flash = false) {
    const ul = $("#feed");
    const placeholder = ul.querySelector(".empty");
    if (placeholder) placeholder.remove();
    const li = document.createElement("li");
    li.className = "feed-item" + (flash ? " flash" : "");
    li.innerHTML = `
      <div class="feed-ico">₵</div>
      <div class="feed-main">
        <div class="feed-title">${c.agencia_codigo || ""} · ${c.agencia_nome || "Agência"}</div>
        <div class="feed-sub">${c.contadora_serie || "—"} · ${num(c.total_cedulas)} cédulas · ${fmtTime(c.finalizada_em)}</div>
      </div>
      <div class="feed-val">${brl(c.valor_total)}</div>`;
    ul.prepend(li);
    while (ul.children.length > 25) ul.lastChild.remove();
  }

  async function loadFeed() {
    const rows = await api("/contagens?limite=25");
    const ul = $("#feed");
    ul.innerHTML = "";
    if (!rows.length) { ul.innerHTML = `<li class="empty">Aguardando contagens…</li>`; return; }
    rows.reverse().forEach((c) => pushFeed(c, false));
  }

  // ---------------- agencias ----------------
  async function loadAgencias() {
    state.agencias = await api("/agencias");
    const tb = $("#tbl-agencias");
    if (!state.agencias.length) { tb.innerHTML = `<tr><td colspan="8" class="empty">Nenhuma agência cadastrada</td></tr>`; return; }
    tb.innerHTML = state.agencias.map((a) => `
      <tr>
        <td><strong>${a.codigo}</strong>${a.central ? ' <span class="badge online">CENTRAL</span>' : ""}</td>
        <td>${a.nome}</td>
        <td>${a.cidade}</td>
        <td>${a.regiao || "—"}</td>
        <td>${a.gerente || "—"}</td>
        <td class="num">${a.total_contadoras}</td>
        <td><span class="badge ${a.ativa ? "ativa" : "inativa"}">${a.ativa ? "Ativa" : "Inativa"}</span></td>
        <td><div class="row-actions">
          <button class="icon-btn" data-edit-agencia="${a.id}">✎</button>
          <button class="icon-btn danger" data-del-agencia="${a.id}">🗑</button>
        </div></td>
      </tr>`).join("");
  }

  function agenciaForm(a = {}) {
    return `
      <div class="field"><label>Código *</label><input name="codigo" value="${a.codigo || ""}" ${a.id ? "readonly" : ""} required></div>
      <div class="field"><label>Nome *</label><input name="nome" value="${a.nome || ""}" required></div>
      <div class="field"><label>Cidade *</label><input name="cidade" value="${a.cidade || ""}" required></div>
      <div class="field"><label>Região</label><input name="regiao" value="${a.regiao || ""}"></div>
      <div class="field full"><label>Endereço</label><input name="endereco" value="${a.endereco || ""}"></div>
      <div class="field"><label>Gerente</label><input name="gerente" value="${a.gerente || ""}"></div>
      <div class="field checkbox"><input type="checkbox" name="central" ${a.central ? "checked" : ""}><label>É a central</label></div>
      <div class="field checkbox"><input type="checkbox" name="ativa" ${a.id ? (a.ativa ? "checked" : "") : "checked"}><label>Ativa</label></div>`;
  }

  // ---------------- contadoras ----------------
  async function loadContadoras() {
    const [contadoras, agencias] = await Promise.all([api("/contadoras"), api("/agencias")]);
    state.contadoras = contadoras;
    state.agencias = agencias;
    const tb = $("#tbl-contadoras");
    if (!contadoras.length) { tb.innerHTML = `<tr><td colspan="8" class="empty">Nenhuma contadora cadastrada</td></tr>`; return; }
    tb.innerHTML = contadoras.map((c) => `
      <tr>
        <td><strong>${c.numero_serie}</strong></td>
        <td>${c.agencia_nome || "—"}</td>
        <td>${c.modelo || "—"}</td>
        <td>${c.fabricante || "—"}</td>
        <td class="mono">${c.ip || "—"}</td>
        <td class="mono" title="${c.api_key}">${c.api_key.slice(0, 14)}…
          <button class="icon-btn" data-copy="${c.api_key}" title="Copiar chave">⧉</button></td>
        <td><span class="badge ${c.status}">${c.status}</span></td>
        <td><div class="row-actions">
          <button class="icon-btn" data-edit-contadora="${c.id}">✎</button>
          <button class="icon-btn danger" data-del-contadora="${c.id}">🗑</button>
        </div></td>
      </tr>`).join("");
  }

  function contadoraForm(c = {}) {
    const opts = state.agencias.map((a) =>
      `<option value="${a.id}" ${c.agencia_id === a.id ? "selected" : ""}>${a.codigo} · ${a.nome}</option>`).join("");
    const statusOpts = ["online", "offline", "contando", "manutencao"].map((s) =>
      `<option value="${s}" ${c.status === s ? "selected" : ""}>${s}</option>`).join("");
    return `
      <div class="field"><label>Número de série *</label><input name="numero_serie" value="${c.numero_serie || ""}" ${c.id ? "readonly" : ""} required></div>
      <div class="field"><label>Agência *</label><select name="agencia_id" required>${opts}</select></div>
      <div class="field"><label>Modelo</label><input name="modelo" value="${c.modelo || ""}"></div>
      <div class="field"><label>Fabricante</label><input name="fabricante" value="${c.fabricante || ""}"></div>
      <div class="field"><label>IP na rede</label><input name="ip" value="${c.ip || ""}" placeholder="10.0.0.10"></div>
      ${c.id ? `<div class="field"><label>Status</label><select name="status">${statusOpts}</select></div>` : ""}
      <div class="field checkbox"><input type="checkbox" name="ativa" ${c.id ? (c.ativa ? "checked" : "") : "checked"}><label>Ativa</label></div>`;
  }

  // ---------------- contagens ----------------
  async function loadContagens() {
    const p = state.periodo.contagens;
    const rows = await api(`/contagens?limite=200${periodoQuery(p)}`);
    const temPeriodo = p.inicio || p.fim;
    let periodoTxt = "tudo";
    if (temPeriodo) {
      periodoTxt = p.inicio && p.inicio === p.fim
        ? fmtDiaBR(p.inicio)
        : `${fmtDiaBR(p.inicio) || "…"} – ${fmtDiaBR(p.fim) || "…"}`;
    }
    $("#cont-periodo").textContent = `Período: ${periodoTxt}`;
    const tb = $("#tbl-contagens");
    if (!rows.length) { tb.innerHTML = `<tr><td colspan="8" class="empty">Nenhuma contagem registrada</td></tr>`; return; }
    tb.innerHTML = rows.map((c) => `
      <tr>
        <td>${fmtDateTime(c.finalizada_em)}</td>
        <td>${c.agencia_codigo || ""} · ${c.agencia_nome || "—"}</td>
        <td>${c.contadora_serie || "—"}</td>
        <td>${c.operador || "—"}</td>
        <td class="num">${brl(c.valor_total)}</td>
        <td class="num">${num(c.total_cedulas)}</td>
        <td class="num">${num(c.cedulas_rejeitadas)}</td>
        <td>${c.lote || "—"}</td>
      </tr>`).join("");
  }

  // ---------------- modal ----------------
  let modalOnSave = null;
  function openModal(title, html, onSave) {
    $("#modal-title").textContent = title;
    $("#modal-form").innerHTML = html;
    modalOnSave = onSave;
    $("#modal-backdrop").classList.remove("hidden");
  }
  function closeModal() { $("#modal-backdrop").classList.add("hidden"); modalOnSave = null; }

  function formData() {
    const form = $("#modal-form");
    const data = {};
    form.querySelectorAll("input, select").forEach((el) => {
      if (el.type === "checkbox") data[el.name] = el.checked;
      else if (el.name === "agencia_id") data[el.name] = parseInt(el.value, 10);
      else data[el.name] = el.value;
    });
    return data;
  }

  // ---------------- refresh dispatch ----------------
  async function refresh() {
    try {
      if (state.view === "dashboard") { await loadDashboard(); await loadFeed(); }
      else if (state.view === "agencias") await loadAgencias();
      else if (state.view === "contadoras") await loadContadoras();
      else if (state.view === "contagens") await loadContagens();
    } catch (e) {
      toast("Erro ao carregar", e.message, "error");
    }
  }

  // ---------------- websocket ----------------
  function connectWS() {
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const ws = new WebSocket(`${proto}://${location.host}/ws`);
    ws.onopen = () => {
      $("#conn-dot").className = "conn-dot on";
      $("#conn-label").textContent = "tempo real ativo";
    };
    ws.onclose = () => {
      $("#conn-dot").className = "conn-dot off";
      $("#conn-label").textContent = "reconectando…";
      setTimeout(connectWS, 2500);
    };
    ws.onmessage = (ev) => {
      try {
        const msg = JSON.parse(ev.data);
        if (msg.event === "nova_contagem") onNovaContagem(msg.data);
      } catch {}
    };
    // keepalive
    setInterval(() => { if (ws.readyState === 1) ws.send("ping"); }, 25000);
  }

  function onNovaContagem(c) {
    toast(`Nova contagem · ${c.agencia_codigo || ""}`, `${brl(c.valor_total)} · ${c.contadora_serie || ""}`);
    if (state.view === "dashboard") {
      pushFeed(c, true);
      loadDashboard().catch(() => {});
    } else if (state.view === "contagens") {
      loadContagens().catch(() => {});
    }
  }

  // ---------------- filtros de período ----------------
  function bindFiltros() {
    // Dashboard
    $("#dash-aplicar").addEventListener("click", () => {
      state.periodo.dashboard = {
        inicio: $("#dash-inicio").value,
        fim: $("#dash-fim").value,
      };
      loadDashboard().catch((e) => toast("Erro ao filtrar", e.message, "error"));
    });
    $("#dash-limpar").addEventListener("click", () => {
      $("#dash-inicio").value = "";
      $("#dash-fim").value = "";
      state.periodo.dashboard = { inicio: "", fim: "" };
      loadDashboard().catch(() => {});
    });
    $$("#filtro-dashboard .chip").forEach((b) =>
      b.addEventListener("click", () => {
        const r = resolvePreset(b.dataset.dpreset);
        $("#dash-inicio").value = r.inicio;
        $("#dash-fim").value = r.fim;
        state.periodo.dashboard = r;
        loadDashboard().catch((e) => toast("Erro ao filtrar", e.message, "error"));
      }));

    // Contagens
    $("#cont-aplicar").addEventListener("click", () => {
      state.periodo.contagens = {
        inicio: $("#cont-inicio").value,
        fim: $("#cont-fim").value,
      };
      loadContagens().catch((e) => toast("Erro ao filtrar", e.message, "error"));
    });
    $("#cont-limpar").addEventListener("click", () => {
      $("#cont-inicio").value = "";
      $("#cont-fim").value = "";
      state.periodo.contagens = { inicio: "", fim: "" };
      loadContagens().catch(() => {});
    });
    $$("#filtro-contagens .chip").forEach((b) =>
      b.addEventListener("click", () => {
        const r = resolvePreset(b.dataset.cpreset);
        $("#cont-inicio").value = r.inicio;
        $("#cont-fim").value = r.fim;
        state.periodo.contagens = r;
        loadContagens().catch((e) => toast("Erro ao filtrar", e.message, "error"));
      }));
  }

  // ---------------- events ----------------
  function bindEvents() {
    $$(".nav-item").forEach((b) => b.addEventListener("click", () => setView(b.dataset.view)));
    $("#btn-refresh").addEventListener("click", refresh);
    $("#modal-close").addEventListener("click", closeModal);
    $("#modal-cancel").addEventListener("click", closeModal);
    $("#modal-backdrop").addEventListener("click", (e) => { if (e.target.id === "modal-backdrop") closeModal(); });

    $("#modal-save").addEventListener("click", async () => {
      const form = $("#modal-form");
      if (!form.reportValidity()) return;
      if (modalOnSave) {
        try { await modalOnSave(formData()); closeModal(); }
        catch (e) { toast("Erro ao salvar", e.message, "error"); }
      }
    });

    bindFiltros();

    $("#btn-nova-agencia").addEventListener("click", () =>
      openModal("Nova agência", agenciaForm(), async (data) => {
        await api("/agencias", { method: "POST", body: JSON.stringify(data) });
        toast("Agência criada", data.nome);
        loadAgencias();
      }));

    $("#btn-nova-contadora").addEventListener("click", async () => {
      if (!state.agencias.length) state.agencias = await api("/agencias");
      openModal("Nova contadora", contadoraForm(), async (data) => {
        const c = await api("/contadoras", { method: "POST", body: JSON.stringify(data) });
        toast("Contadora criada", `Chave: ${c.api_key}`);
        loadContadoras();
      });
    });

    // delegated clicks for table actions
    document.body.addEventListener("click", async (e) => {
      const t = e.target.closest("button");
      if (!t) return;

      if (t.dataset.editAgencia) {
        const a = state.agencias.find((x) => x.id == t.dataset.editAgencia);
        openModal("Editar agência", agenciaForm(a), async (data) => {
          delete data.codigo;
          await api(`/agencias/${a.id}`, { method: "PATCH", body: JSON.stringify(data) });
          toast("Agência atualizada", a.nome);
          loadAgencias();
        });
      }
      if (t.dataset.delAgencia) {
        if (confirm("Remover esta agência e suas contadoras?")) {
          await api(`/agencias/${t.dataset.delAgencia}`, { method: "DELETE" });
          toast("Agência removida");
          loadAgencias();
        }
      }
      if (t.dataset.editContadora) {
        if (!state.agencias.length) state.agencias = await api("/agencias");
        const c = state.contadoras.find((x) => x.id == t.dataset.editContadora);
        openModal("Editar contadora", contadoraForm(c), async (data) => {
          delete data.numero_serie;
          await api(`/contadoras/${c.id}`, { method: "PATCH", body: JSON.stringify(data) });
          toast("Contadora atualizada", c.numero_serie);
          loadContadoras();
        });
      }
      if (t.dataset.delContadora) {
        if (confirm("Remover esta contadora?")) {
          await api(`/contadoras/${t.dataset.delContadora}`, { method: "DELETE" });
          toast("Contadora removida");
          loadContadoras();
        }
      }
      if (t.dataset.copy) {
        navigator.clipboard?.writeText(t.dataset.copy);
        toast("Chave copiada");
      }
    });
  }

  // ---------------- clock ----------------
  function startClock() {
    const tick = () => { $("#clock").textContent = new Date().toLocaleTimeString("pt-BR"); };
    tick(); setInterval(tick, 1000);
  }

  // ---------------- init ----------------
  function init() {
    bindEvents();
    startClock();
    connectWS();
    setView("dashboard");
    setInterval(() => { if (state.view === "dashboard") loadDashboard().catch(() => {}); }, 30000);
  }

  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", init);
  else init();
})();
