// Mapa da saúde suplementar — gráficos em SVG escritos à mão, sem biblioteca.
// Dados: site/dados/*.json (gerados por scripts/exportar_site.py). Operadoras e municípios
// só carregam quando alguém usa a busca, o ranking ou a ficha.

const SVG = "http://www.w3.org/2000/svg";
const nf = (d) => new Intl.NumberFormat("pt-BR", { minimumFractionDigits: d, maximumFractionDigits: d });
const pct = (v, d = 1) => (v == null ? "—" : nf(d).format(v * 100) + "%");
const num = (v, d = 0) => (v == null ? "—" : nf(d).format(v));
const brl = (v) => (v == null ? "—" : "R$ " + nf(0).format(v));
const sinal = (v, d = 1) => (v == null ? "—" : (v > 0 ? "+" : v < 0 ? "−" : "") + nf(d).format(Math.abs(v)));
const mil = (v) => (v >= 1e6 ? nf(1).format(v / 1e6) + " mi" : v >= 1e3 ? nf(0).format(v / 1e3) + " mil" : nf(0).format(v));
const semAcento = (s) => s.normalize("NFD").replace(/[\u0300-\u036f]/g, "").toLowerCase();
// casa palavra por palavra: "unimed fortal" acha "UNIMED DE FORTALEZA"
const casa = (chave, q) => q.split(/\s+/).filter(Boolean).every((p) => chave.includes(p));
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];

function el(tag, attrs = {}, pai) {
  const e = document.createElementNS(SVG, tag);
  for (const [k, v] of Object.entries(attrs)) if (v != null) e.setAttribute(k, v);
  if (pai) pai.appendChild(e);
  return e;
}
function texto(pai, x, y, t, cls, ancora = "middle") {
  const e = el("text", { x, y, class: cls, "text-anchor": ancora }, pai);
  e.textContent = t;
  return e;
}
function svgBase(alvo, w, h, rotulo) {
  alvo.innerHTML = "";
  const s = el("svg", { viewBox: `0 0 ${w} ${h}`, role: "img", "aria-label": rotulo, preserveAspectRatio: "xMidYMid meet" });
  alvo.appendChild(s);
  return s;
}
const cache = {};
async function dados(nome) {
  if (!cache[nome]) cache[nome] = fetch(`dados/${nome}.json`).then((r) => r.json());
  return cache[nome];
}

// ---------------------------------------------------------------- resultado ano a ano
function graficoAnos(m) {
  const alvo = $('[data-grafico="anos"]');
  const W = 640, H = 360, ml = 36, mr = 12, mt = 24, mb = 32;
  const s = svgBase(alvo, W, H, "Resultado da operação, das aplicações e lucro líquido por ano, 2021 a 2025");
  const vals = m.anos.flatMap((a) => [a.operacao, a.aplicacoes, a.lucro]);
  const ymin = Math.min(-12, Math.floor(Math.min(...vals) / 5) * 5), ymax = Math.ceil(Math.max(...vals) / 5) * 5;
  const y = (v) => mt + ((ymax - v) / (ymax - ymin)) * (H - mt - mb);
  for (let v = ymin; v <= ymax; v += 10) {
    el("line", { x1: ml, x2: W - mr, y1: y(v), y2: y(v), class: v === 0 ? "g-zero" : "g-grade" }, s);
    texto(s, ml - 6, y(v) + 4, v === 0 ? "0" : sinal(v, 0), "g-eixo", "end");
  }
  const banda = (W - ml - mr) / m.anos.length, bw = Math.min(24, banda / 4);
  const pts = [];
  m.anos.forEach((a, i) => {
    const cx = ml + banda * (i + 0.5);
    [[a.operacao, "g-perda", -bw - 2], [a.aplicacoes, "g-ganho", 2]].forEach(([v, cls, dx]) => {
      const y0 = y(Math.max(0, v)), h = Math.abs(y(v) - y(0));
      el("rect", { x: cx + dx, y: y0, width: bw, height: Math.max(1, h), class: cls, rx: 2 }, s);
      texto(s, cx + dx + bw / 2, v >= 0 ? y(v) - 6 : y(v) + 14, sinal(v), "g-rotulo-fraco");
    });
    texto(s, cx, H - 8, a.ano, "g-eixo");
    pts.push([cx, y(a.lucro), a.lucro]);
  });
  el("path", { d: "M" + pts.map((p) => p.slice(0, 2).join(",")).join("L"), class: "g-linha" }, s);
  pts.forEach(([x, yy, v]) => { el("circle", { cx: x, cy: yy, r: 4, class: "g-ponto" }, s); texto(s, x, yy - 10, nf(1).format(v), "g-rotulo"); });
  const tab = $('[data-tabela="anos"]');
  tab.insertAdjacentHTML("beforeend", "<thead><tr><th>Ano</th><th>Operação</th><th>Aplicações</th><th>Lucro</th></tr></thead><tbody>" +
    m.anos.map((a) => `<tr><td>${a.ano}</td><td>${sinal(a.operacao)}</td><td>${sinal(a.aplicacoes)}</td><td>${sinal(a.lucro)}</td></tr>`).join("") + "</tbody>");
}

// ---------------------------------------------------------------- sinistralidade 12m
function graficoSinist(m) {
  const alvo = $('[data-grafico="sinistralidade"]');
  const W = 640, H = 320, ml = 40, mr = 150, mt = 16, mb = 28;
  const s = svgBase(alvo, W, H, "Sinistralidade em 12 meses, mercado e modalidades, de 2021 a 2026");
  const ser = m.sinist_12m, mods = Object.keys(m.modalidades).filter((k) => k !== "Seguradora" || true);
  const ymin = 0.7, ymax = 1.0;
  const x = (i) => ml + (i / (ser.length - 1)) * (W - ml - mr);
  const y = (v) => mt + ((ymax - v) / (ymax - ymin)) * (H - mt - mb);
  for (let v = 0.7; v <= 1.0001; v += 0.1) {
    el("line", { x1: ml, x2: W - mr, y1: y(v), y2: y(v), class: "g-grade" }, s);
    texto(s, ml - 6, y(v) + 4, pct(v, 0), "g-eixo", "end");
  }
  ser.forEach((p, i) => { if (p.periodo.endsWith("T4")) texto(s, x(i), H - 4, p.periodo.slice(0, 4), "g-eixo"); });
  const linha = (k, cls) => {
    const pts = ser.map((p, i) => (p[k] == null ? null : [x(i), y(p[k])])).filter(Boolean);
    el("path", { d: "M" + pts.map((p) => p.join(",")).join("L"), class: cls }, s);
    return pts.at(-1);
  };
  const fim = {};
  mods.forEach((k) => { fim[k] = linha(k, "g-linha-quieta"); });
  const pm = linha("mercado", "g-linha");
  // rótulos no fim das linhas, afastados para não se sobreporem
  const rot = mods.map((k) => ({ k, y: fim[k][1], v: ser.at(-1)[k] })).concat([{ k: "Mercado", y: pm[1], v: ser.at(-1).mercado, forte: true }]).sort((a, b) => a.y - b.y);
  for (let i = 1; i < rot.length; i++) if (rot[i].y - rot[i - 1].y < 17) rot[i].y = rot[i - 1].y + 17;
  rot.forEach((r) => texto(s, W - mr + 8, r.y + 4, `${r.k} ${pct(r.v, 0)}`, r.forte ? "g-rotulo" : "g-rotulo-fraco", "start"));
  el("circle", { cx: pm[0], cy: pm[1], r: 4, class: "g-ponto" }, s);
  const pico = ser.reduce((a, p, i) => (p.mercado > ser[a].mercado ? i : a), 0);
  el("circle", { cx: x(pico), cy: y(ser[pico].mercado), r: 4, class: "g-ponto" }, s);
  texto(s, x(pico), y(ser[pico].mercado) - 10, `pico ${pct(ser[pico].mercado)}`, "g-rotulo");
}

// ---------------------------------------------------------------- mapa e clientes
function corCobertura(v) {
  const t = Math.max(0, Math.min(1, (v - 0.04) / (0.41 - 0.04)));
  return `color-mix(in oklab, var(--color-scale-hi) ${Math.round(t * 100)}%, var(--color-scale-lo))`;
}
const NOMES_UF = { AC: "Acre", AL: "Alagoas", AM: "Amazonas", AP: "Amapá", BA: "Bahia", CE: "Ceará", DF: "Distrito Federal", ES: "Espírito Santo", GO: "Goiás", MA: "Maranhão", MG: "Minas Gerais", MS: "Mato Grosso do Sul", MT: "Mato Grosso", PA: "Pará", PB: "Paraíba", PE: "Pernambuco", PI: "Piauí", PR: "Paraná", RJ: "Rio de Janeiro", RN: "Rio Grande do Norte", RO: "Rondônia", RR: "Roraima", RS: "Rio Grande do Sul", SC: "Santa Catarina", SE: "Sergipe", SP: "São Paulo", TO: "Tocantins" };

function mostrarUF(c, uf) {
  const u = c.ufs[uf]; const p = $("[data-painel-uf]");
  if (!u) return;
  const conc = u.hhi > 2500 ? "muito concentrado" : u.hhi > 1500 ? "concentrado" : "pouco concentrado";
  p.innerHTML = `<p class="uf-nome">${NOMES_UF[uf]}</p>
    <dl>
      <dt>Com plano médico</dt><dd>${pct(u.cobertura)} da população</dd>
      <dt>Clientes</dt><dd>${mil(u.vidas)}</dd>
      <dt>Desde dez/2021</dt><dd>${sinal(u.cresc * 100)}%</dd>
      <dt>Maior operadora</dt><dd>${u.lider}, com ${pct(u.lider_pct, 0)} dos clientes</dd>
      <dt>Mercado</dt><dd>${conc} (as 3 maiores têm ${pct(u.top3_pct, 0)})</dd>
    </dl>`;
  $$(".mapa path").forEach((e) => e.setAttribute("aria-pressed", e.dataset.uf === uf ? "true" : "false"));
}
function graficoMapa(c) {
  const alvo = $('[data-grafico="mapa"]');
  const { largura: W, altura: H, caminhos } = c.mapa;
  const s = svgBase(alvo, W, H, "Mapa do Brasil com a parte da população que tem plano médico em cada estado");
  for (const [uf, d] of Object.entries(caminhos)) {
    const u = c.ufs[uf];
    const p = el("path", { d, fill: u ? corCobertura(u.cobertura) : "var(--color-rule)", tabindex: 0, role: "button", "data-uf": uf,
      "aria-label": `${NOMES_UF[uf]}: ${u ? pct(u.cobertura) : "sem dado"} com plano médico`, "aria-pressed": "false" }, s);
    const t = el("title", {}, p); t.textContent = `${NOMES_UF[uf]}: ${u ? pct(u.cobertura) : "—"}`;
    p.addEventListener("click", () => mostrarUF(c, uf));
    p.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); mostrarUF(c, uf); } });
  }
  mostrarUF(c, "CE");
}
function graficoContratacao(c) {
  const alvo = $('[data-grafico="contratacao"]');
  const W = 640, H = 260, ml = 48, mr = 16, mt = 16, mb = 28;
  const s = svgBase(alvo, W, H, "Variação de clientes por tipo de contratação desde dezembro de 2021, em mil");
  const ev = c.evolucao, b = ev[0];
  const series = [["empresarial", "g-linha"], ["individual", "g-linha-perda"], ["adesao", "g-linha-quieta"]];
  const vals = ev.flatMap((e) => series.map(([k]) => (e[k] - b[k]) / 1e3));
  const ymin = Math.floor(Math.min(...vals) / 1000) * 1000, ymax = Math.ceil(Math.max(...vals) / 1000) * 1000;
  const x = (i) => ml + (i / (ev.length - 1)) * (W - ml - mr);
  const y = (v) => mt + ((ymax - v) / (ymax - ymin)) * (H - mt - mb);
  for (let v = ymin; v <= ymax; v += 1000) {
    el("line", { x1: ml, x2: W - mr, y1: y(v), y2: y(v), class: v === 0 ? "g-zero" : "g-grade" }, s);
    texto(s, ml - 6, y(v) + 4, v === 0 ? "0" : sinal(v, 0), "g-eixo", "end");
  }
  ev.forEach((e, i) => { if (e.comp.endsWith("12")) texto(s, x(i), H - 6, e.comp.slice(0, 4), "g-eixo"); });
  series.forEach(([k, cls]) => {
    const pts = ev.map((e, i) => [x(i), y((e[k] - b[k]) / 1e3)]);
    el("path", { d: "M" + pts.map((q) => q.join(",")).join("L"), class: cls }, s);
    const fim = pts.at(-1), v = (ev.at(-1)[k] - b[k]) / 1e3;
    texto(s, fim[0] - 4, fim[1] + (v < 0 ? 16 : -8), sinal(v, 0) + " mil", "g-rotulo", "end");
  });
}
async function ligarCidade() {
  const inp = $("[data-cidade-input]"), lista = $("[data-cidade-lista]"), resp = $("[data-cidade-resposta]");
  let base = null;
  const carregar = async () => (base ??= (await dados("municipios")).map((m) => ({ cod: m[0], nome: m[1], uf: m[2], pop: m[3], vidas: m[4], chave: semAcento(m[1]) })));
  const escolher = (m) => {
    lista.hidden = true; inp.value = `${m.nome} (${m.uf})`;
    const c = m.pop ? m.vidas / m.pop : null;
    resp.textContent = c == null ? `${m.nome}: sem população estimada.` :
      `${m.nome} (${m.uf}): ${pct(Math.min(c, 1))} da população tem plano médico, ${num(m.vidas)} clientes em set/2026.` + (c > 1 ? " Há mais clientes do que moradores: planos registrados no município da empresa, não no de residência." : "");
  };
  sugestor(inp, lista, async (q) => (await carregar()).filter((m) => casa(m.chave, q)).sort((a, b) => b.pop - a.pop).slice(0, 8),
    (m) => [m.nome, m.uf], escolher);
  inp.closest("form").addEventListener("submit", async (e) => { e.preventDefault(); const r = (await carregar()).filter((m) => casa(m.chave, semAcento(inp.value.trim()))).sort((a, b) => b.pop - a.pop); if (r[0]) escolher(r[0]); });
}

// ---------------------------------------------------------------- dispersão custo × qualidade
function graficoDispersao(q) {
  const alvo = $('[data-grafico="dispersao"]');
  const W = 640, H = 420, ml = 44, mr = 16, mt = 16, mb = 40;
  const s = svgBase(alvo, W, H, "Sinistralidade contra reclamações por 100 mil clientes, operadoras com 20 mil clientes ou mais");
  const pts = q.pontos.filter((p) => p[4] != null && p[5] != null);
  const xmin = 0.55, xmax = 1.1, ymax = 150;
  const x = (v) => ml + ((Math.max(xmin, Math.min(xmax, v)) - xmin) / (xmax - xmin)) * (W - ml - mr);
  const y = (v) => mt + (1 - Math.min(v, ymax) / ymax) * (H - mt - mb);
  for (let v = 0; v <= ymax; v += 50) { el("line", { x1: ml, x2: W - mr, y1: y(v), y2: y(v), class: "g-grade" }, s); texto(s, ml - 6, y(v) + 4, num(v), "g-eixo", "end"); }
  for (let v = 0.6; v <= xmax + 1e-9; v += 0.1) texto(s, x(v), H - 20, pct(v, 0), "g-eixo");
  texto(s, (W + ml) / 2, H - 2, "Quanto da mensalidade volta em atendimento", "g-rotulo-fraco");
  texto(s, ml, mt - 4, "Reclamações por 100 mil clientes/mês", "g-rotulo-fraco", "start");
  el("line", { x1: x(q.mediana_sinist), x2: x(q.mediana_sinist), y1: mt, y2: H - mb, class: "g-mediana" }, s);
  el("line", { x1: ml, x2: W - mr, y1: y(q.mediana_igr), y2: y(q.mediana_igr), class: "g-mediana" }, s);
  texto(s, ml + 8, mt + 14, "gasta menos com o cliente e recebe mais reclamações", "g-rotulo-fraco", "start");
  texto(s, W - mr - 4, H - mb - 8, "gasta mais e recebe menos", "g-rotulo-fraco", "end");
  texto(s, W - mr, mt + 14, "acima de 150: na borda", "g-rotulo-fraco", "end");
  const info = $("[data-ponto-info]");
  const mostrar = (p, c) => {
    $$(".g-disp", s).forEach((e) => e.setAttribute("data-ativo", "false")); c.setAttribute("data-ativo", "true");
    info.innerHTML = `<a href="#operadora/${p[0]}">${p[1]}</a><br>${p[2]}, ${mil(p[7])} clientes. Volta em atendimento: ${pct(p[4])}. Reclamações: ${num(p[5], 1)} por 100 mil clientes/mês. Nota da ANS: ${p[6] == null ? "—" : nf(3).format(p[6])}.`;
  };
  pts.forEach((p) => {
    const c = el("circle", { cx: x(p[4]), cy: y(p[5]), r: Math.max(3, Math.min(11, Math.sqrt(p[7]) / 90)), class: "g-disp", tabindex: 0, "aria-label": `${p[1]}: ${pct(p[4])}, ${num(p[5], 1)} reclamações` }, s);
    c.addEventListener("mouseenter", () => mostrar(p, c)); c.addEventListener("focus", () => mostrar(p, c)); c.addEventListener("click", () => mostrar(p, c));
  });
}

// ---------------------------------------------------------------- SUS
function barrasHorizontais(alvo, itens, rotulo, opts = {}) {
  const W = opts.w ?? 640, lh = opts.lh ?? 30, ml = opts.ml ?? 260, H = itens.length * lh + 8;
  const s = svgBase(alvo, W, H, rotulo);
  const max = Math.max(...itens.map((i) => i.v));
  itens.forEach((it, i) => {
    const yy = 4 + i * lh, w = (it.v / max) * (W - ml - 60);
    texto(s, ml - 10, yy + 17, it.rot, "g-eixo", "end");
    el("rect", { x: ml, y: yy + 5, width: Math.max(1, w), height: 18, rx: 2, class: it.cls || "g-barra" }, s);
    texto(s, ml + w + 6, yy + 18, it.txt, "g-rotulo", "start");
  });
}
function graficosSUS(sus) {
  const g = sus.grupos;
  const ordem = [["Não indica falha", "g-barra-quieta"], ["Zona cinzenta", "g-barra"], ["Provável falha de acesso", "g-perda"]];
  barrasHorizontais($('[data-grafico="sus-grupos"]'), ordem.map(([k, cls]) => ({ rot: k, v: g[k].pct_atend, txt: pct(g[k].pct_atend, 0), cls })),
    "Atendimentos de clientes de plano no SUS por grupo de leitura, 2019 a 2025", { ml: 200 });
  const cor = { "Não indica falha": "g-barra-quieta", "Zona cinzenta": "g-barra", "Provável falha de acesso": "g-perda" };
  const mot = sus.motivos.filter((m) => m.motivo !== "Outros" && m.pct_atend >= 0.02).slice(0, 9);
  barrasHorizontais($('[data-grafico="sus-motivos"]'), mot.map((m) => ({ rot: m.motivo, v: m.pct_atend, txt: pct(m.pct_atend, 0), cls: cor[m.grupo] })),
    "Principais motivos dos atendimentos no SUS", { ml: 200 });
}

// ---------------------------------------------------------------- sugestões (busca com teclado)
function sugestor(inp, lista, buscar, linha, escolher) {
  let itens = [], ativo = -1, t;
  const fechar = () => { lista.hidden = true; ativo = -1; inp.setAttribute("aria-expanded", "false"); };
  const desenhar = () => {
    lista.innerHTML = "";
    itens.forEach((it, i) => {
      const li = document.createElement("li"); li.setAttribute("role", "option"); li.setAttribute("aria-selected", i === ativo ? "true" : "false");
      const [a, b] = linha(it); li.innerHTML = `<span></span><span></span>`; li.children[0].textContent = a; li.children[1].textContent = b;
      li.addEventListener("mousedown", (e) => { e.preventDefault(); escolher(it); fechar(); });
      lista.appendChild(li);
    });
    lista.hidden = !itens.length; inp.setAttribute("aria-expanded", itens.length ? "true" : "false");
  };
  inp.setAttribute("role", "combobox"); inp.setAttribute("aria-autocomplete", "list");
  inp.addEventListener("input", () => {
    clearTimeout(t);
    t = setTimeout(async () => { const q = semAcento(inp.value.trim()); if (q.length < 2) { itens = []; desenhar(); return; } itens = await buscar(q); ativo = -1; desenhar(); }, 120);
  });
  inp.addEventListener("keydown", (e) => {
    if (lista.hidden) return;
    if (e.key === "ArrowDown") { ativo = Math.min(itens.length - 1, ativo + 1); desenhar(); e.preventDefault(); }
    else if (e.key === "ArrowUp") { ativo = Math.max(0, ativo - 1); desenhar(); e.preventDefault(); }
    else if (e.key === "Enter" && ativo >= 0) { e.preventDefault(); escolher(itens[ativo]); fechar(); }
    else if (e.key === "Escape") fechar();
  });
  inp.addEventListener("blur", () => setTimeout(fechar, 150));
}

// ---------------------------------------------------------------- operadoras: busca, ranking e ficha
let OPS = null;
async function operadoras() {
  if (!OPS) {
    const d = await dados("operadoras");
    d.operadoras.forEach((o) => { o.chave = semAcento(`${o.nome} ${o.razao} ${o.reg}`); });
    OPS = d;
  }
  return OPS;
}
function buscarOps(q) {
  return OPS.operadoras.filter((o) => casa(o.chave, q)).sort((a, b) => (b.vidas || 0) - (a.vidas || 0)).slice(0, 8);
}
function ligarBuscas() {
  $$("[data-busca]").forEach((form) => {
    const inp = $("[data-busca-input]", form), lista = $("[data-busca-lista]", form);
    const ir = (o) => { location.hash = `operadora/${o.reg}`; };
    inp.addEventListener("focus", operadoras, { once: true });
    sugestor(inp, lista, async (q) => { await operadoras(); return buscarOps(q); }, (o) => [o.nome, `${o.uf_sede || ""} ${o.vidas ? mil(o.vidas) + " clientes" : ""}`.trim()], ir);
    form.addEventListener("submit", async (e) => {
      e.preventDefault(); await operadoras();
      const r = buscarOps(semAcento(inp.value.trim()));
      if (r[0]) { inp.removeAttribute("aria-invalid"); ir(r[0]); }
      else { inp.setAttribute("aria-invalid", "true"); lista.innerHTML = "<li role=\"option\" aria-disabled=\"true\"><span>Nenhuma operadora ativa com esse nome ou registro.</span><span></span></li>"; lista.hidden = false; }
    });
  });
}

const IND = [
  ["sinistralidade", "Quanto da mensalidade volta em atendimento", "pct", "", "Sinistralidade 12 meses, critério da ANS"],
  ["indice_combinado", "Custos para cada R$ 100 recebidos", "pct", "menor", "Atendimento, administração e venda; acima de 100% a operação dá prejuízo"],
  ["margem_liquida", "Lucro final sobre a receita", "pct", "maior", "Resultado líquido ÷ contraprestações, 12 meses"],
  ["indice_desp_adm", "Quanto vai para administração", "pct", "menor", "Despesas administrativas ÷ receitas"],
  ["receita_vida_mes", "Receita por cliente, por mês", "brl", "", "Contraprestações ÷ clientes médios ÷ 12"],
  ["custo_vida_mes", "Custo assistencial por cliente, por mês", "brl", "", "Eventos ÷ clientes médios ÷ 12"],
  ["cresc_vidas_12m", "Crescimento de clientes em 12 meses", "pct", "maior", "jun/2026 sobre jun/2025"],
  ["pct_59mais", "Clientes com 59 anos ou mais", "pct", "", "Última faixa de reajuste da ANS"],
  ["igr_12m", "Reclamações por 100 mil clientes, por mês", "num1", "menor", "IGR da ANS; abaixo de 20 mil clientes o índice oscila muito"],
  ["idss", "Nota de qualidade da ANS (0 a 1)", "num3", "maior", "IDSS 2025, ano-base 2024"],
  ["glosa_inicial", "Quanto da conta da rede é recusado (glosa)", "pct", "", "2º semestre de 2025; valores improváveis ficam em branco"],
  ["tempo_pagamento_dias", "Dias para pagar a rede", "num0", "menor", "Da cobrança do prestador ao pagamento"],
  ["sus_falha_por_mil", "Uso do SUS por possível falha de acesso", "num1", "menor", "Parto, psiquiatria e cirurgia programável, por mil clientes, 2024"],
  ["sus_pct_justica", "Cobrança do SUS parada na Justiça", "pct", "menor", "Ressarcimento cobrado de 2019 a 2025"],
  ["pct_judicial", "Gasto com decisões judiciais", "pct", "menor", "Em % dos eventos, 12 meses"],
  ["pct_ev_rede_propria", "Atendimento em rede própria", "pct", "", "Em % dos eventos, 12 meses"],
];
const FMT = { pct: (v) => pct(v), brl: (v) => brl(v), num0: (v) => num(v, 0), num1: (v) => num(v, 1), num3: (v) => (v == null ? "—" : nf(3).format(v)) };
const FORMAS = { procedimento: "Por procedimento", pacote: "Em pacote", rede_propria: "Rede própria", rede_indireta: "Rede indireta", reembolso: "Reembolso", capitation: "Capitation", orcamento_global: "Orçamento global" };

function faixa(v, q, melhor) {
  if (v == null || !q) return { html: `<div class="faixa" aria-hidden="true"></div>`, txt: "" };
  const [p25, p50, p75] = q;
  const lo = Math.min(v, p25 - (p75 - p25) * 0.6), hi = Math.max(v, p75 + (p75 - p25) * 0.6);
  const pos = (z) => (hi === lo ? 50 : ((z - lo) / (hi - lo)) * 100);
  let txt = v < p25 ? "entre as 25% mais baixas" : v > p75 ? "entre as 25% mais altas" : "na faixa do meio";
  let cls = "";
  if ((melhor === "menor" && v < p25) || (melhor === "maior" && v > p75)) { txt += " (melhor)"; cls = "melhor"; }
  if ((melhor === "menor" && v > p75) || (melhor === "maior" && v < p25)) { txt += " (pior)"; cls = "pior"; }
  return { txt, html: `<div class="faixa" role="img" aria-label="${txt}"><div class="faixa-trilho"></div><div class="faixa-meio" style="left:${pos(p25)}%;width:${pos(p75) - pos(p25)}%"></div><div class="faixa-mediana" style="left:${pos(p50)}%"></div><div class="faixa-ponto ${cls}" style="left:${pos(v)}%"></div></div>` };
}
function sparkSinist(o, d) {
  const s = o.sinist_tri, W = 400, H = 132, ml = 40, mr = 8, mt = 16, mb = 28;
  const vals = s.filter((v) => v != null); if (vals.length < 2) return "<p class=\"nota\">Sem série trimestral suficiente.</p>";
  const ymin = Math.min(0.6, ...vals), ymax = Math.max(1.0, ...vals);
  const x = (i) => ml + (i / (s.length - 1)) * (W - ml - mr), y = (v) => mt + ((ymax - v) / (ymax - ymin)) * (H - mt - mb);
  const pts = s.map((v, i) => (v == null ? null : `${x(i).toFixed(1)},${y(v).toFixed(1)}`)).filter(Boolean);
  const med = d.quartis[o.porte]?.sinistralidade?.[1];
  const anos = d.trimestres.map((t, i) => (t.endsWith("T1") ? `<text x="${x(i)}" y="${H - 4}" class="g-eixo" text-anchor="middle">${t.slice(0, 4)}</text>` : "")).join("");
  return `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="Sinistralidade em 12 meses, trimestre a trimestre">
    ${[0.6, 0.8, 1.0].map((v) => `<line x1="${ml}" x2="${W - mr}" y1="${y(v)}" y2="${y(v)}" class="g-grade"/><text x="${ml - 4}" y="${y(v) + 4}" class="g-eixo" text-anchor="end">${pct(v, 0)}</text>`).join("")}
    ${med ? `<line x1="${ml}" x2="${W - mr}" y1="${y(med)}" y2="${y(med)}" class="g-mediana" stroke-dasharray="4 3"/><text x="${W - mr}" y="${y(med) - 4}" class="g-rotulo-fraco" text-anchor="end">mediana do porte hoje</text>` : ""}
    <path d="M${pts.join("L")}" class="g-linha"/>${anos}</svg>`;
}
async function abrirFicha(reg, rolar = true) {
  const d = await operadoras();
  const o = d.operadoras.find((x) => x.reg === reg);
  const alvo = $("[data-ficha]");
  if (!o) { alvo.innerHTML = `<p class="nota">Não encontrei a operadora com registro ${reg} entre as ativas.</p>`; return; }
  const q = o.ranking ? d.quartis[o.porte] || {} : {};
  const aviso = o.ranking ? `Comparada com as ${q.sinistralidade?.[3] ?? ""} operadoras de porte ${o.porte.toLowerCase()} do ranking.` : `Fora do ranking: ${o.motivo}. Os números aparecem, sem comparação.`;
  const linhas = IND.map(([c, nome, f, melhor, expl]) => {
    const v = o.ind[c], fx = faixa(v, q[c], melhor);
    return `<li class="ind"><div class="ind-nome">${nome}<small>${fx.txt || expl}</small></div><div class="ind-valor">${FMT[f](v)}</div>${fx.html}</li>`;
  }).join("");
  const rede = Object.entries(o.rede).filter(([, v]) => v > 0.005).sort((a, b) => b[1] - a[1]);
  const r = o.resultado;
  const fmtMi = (v) => (v == null ? "—" : (Math.abs(v) >= 1000 ? sinal(v / 1000, 1) + " bi" : sinal(v, 0) + " mi"));
  alvo.innerHTML = `
    <header class="ficha-cabeca">
      <h3>${o.nome}</h3>
      <p class="ficha-perfil">${o.modalidade}, porte ${o.porte.toLowerCase()}, registro ANS ${o.reg}, sede em ${o.uf_sede || "—"}${o.vidas ? `, ${num(o.vidas)} clientes em jun/2026` : ""}.</p>
      <p class="ficha-aviso">${aviso}</p>
    </header>
    <div class="ficha-grade">
      <div>
        <ul class="ind-lista">${linhas}</ul>
        <p class="faixa-legenda">Faixa cinza: metade do meio das operadoras do mesmo porte; traço: mediana; ponto: a operadora. Verde e coral só quando o indicador tem direção clara.</p>
      </div>
      <div class="ficha-lado">
        <div><h4>Resultado em 12 meses (R$)</h4>
          <div class="resultado-op">
            <div><span class="num">${fmtMi(r.operacao)}</span><span>operação do plano</span></div>
            <div><span class="num">${fmtMi(r.aplicacoes)}</span><span>aplicações</span></div>
            <div><span class="num">${fmtMi(r.lucro)}</span><span>lucro líquido</span></div>
          </div></div>
        <div><h4>Quanto da mensalidade volta em atendimento</h4>${sparkSinist(o, d)}</div>
        <div><h4>Como paga a rede</h4><div class="svg-alvo" data-rede></div></div>
        <div><h4>Onde estão os clientes</h4><p>${Object.entries(o.ufs).slice(0, 6).map(([uf, v]) => `${NOMES_UF[uf] || uf} ${mil(v)}`).join("; ") || "—"}.</p></div>
      </div>
    </div>`;
  if (rede.length) barrasHorizontais($("[data-rede]", alvo), rede.map(([k, v]) => ({ rot: FORMAS[k], v, txt: pct(v, 0) })), "Eventos por forma de pagamento à rede", { ml: 130, w: 380, lh: 28 });
  if (rolar) {
    // rolagem direta e conferida: o ranking carrega no caminho e empurra a página
    const alvoSec = document.getElementById("operadora");
    alvoSec.scrollIntoView();
    const conferir = () => { if (Math.abs(alvoSec.getBoundingClientRect().top - 64) > 8) alvoSec.scrollIntoView(); };
    setTimeout(conferir, 450); setTimeout(conferir, 1500);
  }
}

async function ligarRanking(m) {
  const box = $("[data-ranking]"), tb = $("[data-ranking-tabela] tbody"), mais = $("[data-ranking-mais]");
  const fmod = $('[data-filtro="modalidade"]'), fuf = $('[data-filtro="uf"]'), fporte = $('[data-filtro="porte"]');
  Object.keys(m.modalidades).forEach((k) => fmod.insertAdjacentHTML("beforeend", `<option>${k}</option>`));
  Object.entries(NOMES_UF).sort((a, b) => a[1].localeCompare(b[1])).forEach(([k, v]) => fuf.insertAdjacentHTML("beforeend", `<option value="${k}">${v}</option>`));
  let todos = false;
  const desenhar = () => {
    const lst = OPS.operadoras.filter((o) => o.ranking && o.porte === fporte.value && (!fmod.value || o.modalidade === fmod.value) && (!fuf.value || (o.ufs[fuf.value] || 0) >= 1000))
      .sort((a, b) => b.ind.sinistralidade - a.ind.sinistralidade);
    const ver = todos ? lst : lst.slice(0, 15);
    tb.innerHTML = ver.length ? ver.map((o) => `<tr><td><a href="#operadora/${o.reg}">${o.nome}</a></td><td>${mil(o.vidas)}</td><td class="${o.ind.sinistralidade > 0.9 ? "alto" : ""}">${pct(o.ind.sinistralidade)}</td><td class="${o.ind.indice_combinado > 1 ? "alto" : ""}">${pct(o.ind.indice_combinado)}</td><td class="${o.ind.margem_liquida < 0 ? "alto" : ""}">${pct(o.ind.margem_liquida)}</td></tr>`).join("")
      : `<tr><td colspan="5" class="nota">Nenhuma operadora desse porte com esse filtro.</td></tr>`;
    mais.hidden = todos || lst.length <= 15; mais.textContent = `Mostrar todas as ${lst.length}`;
  };
  [fmod, fuf, fporte].forEach((s) => s.addEventListener("change", () => { todos = false; desenhar(); }));
  mais.addEventListener("click", () => { todos = true; desenhar(); });
  // carrega em segundo plano logo depois da primeira pintura: a tabela fica pronta antes de a pessoa rolar
  // e não empurra a página quando ela navega pelo menu
  const quandoOcioso = window.requestIdleCallback || ((f) => setTimeout(f, 800));
  quandoOcioso(async () => { await operadoras(); desenhar(); });
}

function rota() {
  const m = location.hash.match(/^#operadora\/(\d{6})$/);
  if (m) abrirFicha(m[1]);
}

// ---------------------------------------------------------------- início
(async () => {
  const [m, c, q, sus] = await Promise.all([dados("mercado"), dados("clientes"), dados("qualidade"), dados("sus")]);
  graficoAnos(m); graficoSinist(m); graficoMapa(c); graficoContratacao(c); graficoDispersao(q); graficosSUS(sus);
  ligarBuscas(); ligarCidade(); ligarRanking(m);
  window.addEventListener("hashchange", rota);
  if (/^#operadora\/\d{6}$/.test(location.hash)) rota();
  // sem operadora na URL: a ficha de exemplo só carrega quando a seção se aproxima da tela
  const io = new IntersectionObserver((ents) => {
    if (ents.some((e) => e.isIntersecting)) { io.disconnect(); if (!/^#operadora\//.test(location.hash)) abrirFicha("326305", false); }
  }, { rootMargin: "600px" });
  io.observe(document.getElementById("operadora"));
})();
