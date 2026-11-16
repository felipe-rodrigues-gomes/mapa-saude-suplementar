// Mapa da saúde suplementar, v2: a história em capítulos, o estado do leitor valendo para a página toda,
// o ranking de reclamações e o comparador entre concorrentes. Gráficos em SVG à mão, sem biblioteca.
// Dados: site/dados/*.json e site/dados/uf/XX.json (scripts/exportar_site.py e scripts/exportar_uf.py).

const SVG = "http://www.w3.org/2000/svg";
const nf = (d) => new Intl.NumberFormat("pt-BR", { minimumFractionDigits: d, maximumFractionDigits: d });
const pct = (v, d = 1) => (v == null ? "—" : nf(d).format(v * 100) + "%");
const num = (v, d = 0) => (v == null ? "—" : nf(d).format(v));
const brl = (v) => (v == null ? "—" : "R$ " + nf(0).format(v));
const reais = (v) => (v == null ? "—" : "R$ " + nf(2).format(v));
const sinal = (v, d = 1) => (v == null ? "—" : (v > 0 ? "+" : v < 0 ? "−" : "") + nf(d).format(Math.abs(v)));
const mil = (v) => (v >= 1e6 ? nf(1).format(v / 1e6) + " mi" : v >= 1e3 ? nf(0).format(v / 1e3) + " mil" : nf(0).format(v));
const semAcento = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase();
const casa = (chave, q) => q.split(/\s+/).filter(Boolean).every((p) => chave.includes(p));
const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);

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
function dados(nome) {
  if (!cache[nome]) cache[nome] = fetch(`dados/${nome}.json`).then((r) => { if (!r.ok) throw new Error(nome); return r.json(); });
  return cache[nome];
}

const NOMES_UF = { AC: "Acre", AL: "Alagoas", AM: "Amazonas", AP: "Amapá", BA: "Bahia", CE: "Ceará", DF: "Distrito Federal", ES: "Espírito Santo", GO: "Goiás", MA: "Maranhão", MG: "Minas Gerais", MS: "Mato Grosso do Sul", MT: "Mato Grosso", PA: "Pará", PB: "Paraíba", PE: "Pernambuco", PI: "Piauí", PR: "Paraná", RJ: "Rio de Janeiro", RN: "Rio Grande do Norte", RO: "Rondônia", RR: "Roraima", RS: "Rio Grande do Sul", SC: "Santa Catarina", SE: "Sergipe", SP: "São Paulo", TO: "Tocantins" };
const PREP = { AC: "no", AL: "em", AM: "no", AP: "no", BA: "na", CE: "no", DF: "no", ES: "no", GO: "em", MA: "no", MG: "em", MS: "em", MT: "em", PA: "no", PB: "na", PE: "em", PI: "no", PR: "no", RJ: "no", RN: "no", RO: "em", RR: "em", RS: "no", SC: "em", SE: "em", SP: "em", TO: "no" };
const noUF = (uf) => `${PREP[uf]} ${NOMES_UF[uf]}`;
// temas da NIP em português de quem reclama (o nome oficial vai no title)
const TEMAS = {
  "Regras para Acesso aos Atendimentos": "Autorização e acesso a atendimento",
  "Rol de Procedimentos e Cobertura Contratual": "Negativa de cobertura",
  "Rede de Atendimento (rede conveniada)": "Rede credenciada",
  "Prazos Máximos para Atendimento": "Demora para atender",
  "Reembolso": "Reembolso",
  "Suspensão e Rescisão Contratuais": "Cancelamento do plano",
  "Mensalidade ou Outras Cobranças": "Cobranças e mensalidade",
  "Carência": "Carência",
  "Contratação/Adesão e Vigência Contratual": "Contratação",
  "Portabilidade de Carências": "Portabilidade",
  "Itens Obrigatórios e Cláusulas Contratuais": "Contrato",
  "Reajuste por Variação de Custos": "Reajuste anual",
  "Reajuste por Mudança de Faixa Etária": "Reajuste por idade",
  "Doença ou Lesão Preexistente, CPT e Agravo": "Doença preexistente",
};
const tema = (t) => TEMAS[t] || t;

// ---------------------------------------------------------------- estado do leitor
const GUARDA = "mapa.uf";
let UF = (() => { try { return localStorage.getItem(GUARDA) || "SP"; } catch { return "SP"; } })();
const ouvintes = [];
function quandoMudarEstado(f) { ouvintes.push(f); }
function setEstado(uf, { guardar = true } = {}) {
  if (!NOMES_UF[uf]) return;
  UF = uf;
  if (guardar) { try { localStorage.setItem(GUARDA, uf); } catch { /* sem armazenamento: segue sem lembrar */ } }
  $$("[data-estado]").forEach((s) => { s.value = uf; });
  ouvintes.forEach((f) => f(uf));
}
function ligarEstados() {
  const ops = Object.entries(NOMES_UF).sort((a, b) => a[1].localeCompare(b[1], "pt-BR")).map(([k, v]) => `<option value="${k}">${v}</option>`).join("");
  $$("[data-estado]").forEach((s) => { s.innerHTML = ops; s.value = UF; s.addEventListener("change", () => setEstado(s.value)); });
}

// ---------------------------------------------------------------- capítulo 1: pra onde vai a mensalidade (em %)
function cem(m, cu, uf) {
  const d = cu[uf] || cu.BR, onde = cu[uf] ? noUF(uf) : "no Brasil", Onde = onde[0].toUpperCase() + onde.slice(1);
  const mens = d.mensalidade, rs = (p) => mens * p / 100;
  const real = (v) => `R$\u00a0${nf(0).format(v)}`;
  const bi = (v) => Math.abs(v) >= 1 ? `R$\u00a0${nf(1).format(v)}\u00a0${Math.abs(v) < 2 ? "bilhão" : "bilhões"}` : `R$\u00a0${nf(0).format(v * 1000)}\u00a0milhões`;
  const fatias = [["atendimento", "voltam em atendimento"], ["administracao", "administração"], ["venda", "venda e corretagem"], ["outras", "outras despesas da operação"], ["sobra", d.sobra >= 0 ? "sobram para a operadora" : "a operação perde"]];
  // valores em reais inteiros que somam exatamente a mensalidade arredondada (a diferença vai para o atendimento)
  const R = Object.fromEntries(fatias.map(([k]) => [k, Math.round(rs(d[k]))]));
  R.atendimento += Math.round(mens) - fatias.reduce((s, [k]) => s + R[k], 0);
  const barra = (alvo, rotulos) => {
    alvo.innerHTML = fatias.map(([k, t]) => `<span class="f-${k}" style="flex:${Math.max(d[k], 0).toFixed(2)} 1 0" title="${real(Math.abs(R[k]))} (${nf(1).format(d[k])}%): ${t}">${rotulos && d[k] >= 6 ? real(R[k]) : ""}</span>`).join("");
  };
  barra($("[data-cem-mini]"), false);
  barra($("[data-cem]"), true);
  $("[data-cem-legenda]").innerHTML = fatias.map(([k, t]) => `<li class="l-${k}"><strong class="num">${real(Math.abs(R[k]))}</strong><span>${t} (${nf(1).format(Math.abs(d[k]))}%)</span></li>`).join("");
  $("[data-cem]").setAttribute("aria-label", `Divisão da mensalidade média ${onde}, de ${real(mens)}`);
  $("[data-cem-valor]").textContent = `Média ${onde}: ${real(mens)} por mês.`;
  $("[data-cem-lucro]").textContent = `Mas o lucro das operadoras ${onde} foi de ${bi(d.lucro_bi)}.`;
  $("[data-cem-figura]").setAttribute("aria-label", `Mensalidade média ${onde}: ${real(mens)}. ${nf(1).format(d.atendimento)}% voltam em atendimento. O lucro das operadoras ${onde} foi de ${bi(d.lucro_bi)} em 12 meses`);
  $("[data-cem-titulo]").textContent = d.sobra >= 0
    ? `${Onde}, a mensalidade média é de ${real(mens)}. Sobram ${real(R.sobra)} para a operadora.`
    : `${Onde}, a mensalidade média é de ${real(mens)}, e a operação perde ${real(-R.sobra)} por cliente.`;
  $("[data-cem-lead]").textContent = `É a média de todos os planos médicos ${onde}, empresariais incluídos: ${bi(d.receita_bi)} de mensalidades em 12 meses. ${d.sobra >= 0 ? `Os ${real(R.sobra)} são o que fica` : "O resultado é o que fica"} depois de pagar atendimento, administração, venda e as demais despesas da operação.`;
  $("[data-cem-ponte]").textContent = `${d.sobra >= 0 ? `Na operação, sobraram ${bi(d.sobra_bi)}.` : `Na operação, faltaram ${bi(-d.sobra_bi)}.`} Mas o lucro das operadoras ${onde} foi de ${bi(d.lucro_bi)}.`;
}

// ---------------------------------------------------------------- capítulo 2: resultado ano a ano
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
      el("rect", { x: cx + dx, y: y(Math.max(0, v)), width: bw, height: Math.max(1, Math.abs(y(v) - y(0))), class: cls, rx: 2 }, s);
      texto(s, cx + dx + bw / 2, v >= 0 ? y(v) - 6 : y(v) + 14, sinal(v), "g-rotulo-fraco");
    });
    texto(s, cx, H - 8, a.ano, "g-eixo");
    pts.push([cx, y(a.lucro), a.lucro]);
  });
  el("path", { d: "M" + pts.map((p) => p.slice(0, 2).join(",")).join("L"), class: "g-linha" }, s);
  pts.forEach(([x, yy, v]) => { el("circle", { cx: x, cy: yy, r: 4, class: "g-ponto" }, s); texto(s, x, yy - 10, nf(1).format(v), "g-rotulo"); });
  $('[data-tabela="anos"]').insertAdjacentHTML("beforeend", "<thead><tr><th>Ano</th><th>Operação</th><th>Aplicações</th><th>Lucro</th></tr></thead><tbody>" +
    m.anos.map((a) => `<tr><td>${a.ano}</td><td>${sinal(a.operacao)}</td><td>${sinal(a.aplicacoes)}</td><td>${sinal(a.lucro)}</td></tr>`).join("") + "</tbody>");
}

// ---------------------------------------------------------------- capítulo 3: clientes e mapa
function corCobertura(v) {
  const t = Math.max(0, Math.min(1, (v - 0.04) / (0.41 - 0.04)));
  return `color-mix(in oklab, var(--color-scale-hi) ${Math.round(t * 100)}%, var(--color-scale-lo))`;
}
function painelUF(c, uf) {
  const u = c.ufs[uf]; if (!u) return;
  $("[data-painel-uf]").innerHTML = `<dl>
      <dt>Com plano médico</dt><dd>${pct(u.cobertura)} da população</dd>
      <dt>Clientes</dt><dd>${mil(u.vidas)}</dd>
      <dt>Desde dez/2021</dt><dd>${sinal(u.cresc * 100)}%</dd>
    </dl>`;
  const t = $('[data-uf-titulo="clientes"]'), f = $('[data-uf-frase="clientes"]');
  t.textContent = `${noUF(uf).replace(/^./, (x) => x.toUpperCase())}, ${pct(u.cobertura, 0)} da população tem plano médico.`;
  f.textContent = `No Brasil, são ${pct(c.brasil.cobertura, 0)}: ${nf(1).format(c.brasil.vidas / 1e6)} milhões de pessoas. Toque em outro estado no mapa para comparar.`;
  $$(".mapa path").forEach((e) => e.setAttribute("aria-pressed", e.dataset.uf === uf ? "true" : "false"));
}
// participação de mercado no estado: as 6 maiores e o resto somado; cada linha abre o comparador
async function participacao(c, uf) {
  const d = await dados(`uf/${uf}`); if (uf !== UF) return;
  const ops = [...d.operadoras].sort((a, b) => b.vidas - a.vidas), top = ops.slice(0, 6);
  // "outras" = o que falta para 100% depois de arredondar as 6 maiores, para a soma da tela fechar
  const resto = Math.max(0, 1000 - top.reduce((s, o) => s + Math.round(o.participacao * 1000), 0)) / 1000, n = (d.operadoras_com_clientes ?? ops.length) - top.length;
  const linha = (nome, p, href) => `<${href ? `a href="${href}"` : "div"} class="share-linha"><span class="share-nome">${nome}</span><span class="share-barra"><i style="width:${(p * 100).toFixed(1)}%"></i></span><span class="share-valor num">${pct(p)}</span></${href ? "a" : "div"}>`;
  $("[data-share-titulo]").textContent = `Participação de mercado ${noUF(uf)}`;
  $("[data-share]").innerHTML = top.map((o) => linha(esc(o.nome), o.participacao, `#compare/${uf}/${o.reg}`)).join("") +
    (n > 0 && resto > 0.0005 ? linha(`Outras ${nf(0).format(n)} operadoras`, resto, null) : "");
  const hhi = ops.reduce((s, o) => s + (o.participacao * 100) ** 2, 0), top3 = ops.slice(0, 3).reduce((s, o) => s + o.participacao, 0);
  const conc = hhi > 2500 ? "muito concentrado" : hhi > 1500 ? "concentrado" : "pouco concentrado";
  $("[data-share-nota]").textContent = `Mercado ${conc}: as 3 maiores têm ${pct(top3, 0)} dos ${mil(d.clientes)} clientes, em jun/2026. Toque numa operadora para compará-la.`;
}
function graficoMapa(c) {
  const { largura: W, altura: H, caminhos } = c.mapa;
  const s = svgBase($('[data-grafico="mapa"]'), W, H, "Mapa do Brasil com a parte da população que tem plano médico em cada estado");
  for (const [uf, d] of Object.entries(caminhos)) {
    const u = c.ufs[uf];
    const p = el("path", { d, fill: u ? corCobertura(u.cobertura) : "var(--color-rule)", tabindex: 0, role: "button", "data-uf": uf,
      "aria-label": `${NOMES_UF[uf]}: ${u ? pct(u.cobertura) : "sem dado"} com plano médico`, "aria-pressed": "false" }, s);
    el("title", {}, p).textContent = `${NOMES_UF[uf]}: ${u ? pct(u.cobertura) : "—"}`;
    p.addEventListener("click", () => setEstado(uf));
    p.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); setEstado(uf); } });
  }
}
function graficoContratacao(c) {
  const W = 640, H = 260, ml = 48, mr = 16, mt = 16, mb = 28;
  const s = svgBase($('[data-grafico="contratacao"]'), W, H, "Variação de clientes por tipo de contratação desde dezembro de 2021, em mil");
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

// ---------------------------------------------------------------- busca com teclado (cidade)
function sugestor(inp, lista, buscar, linha, escolher) {
  let itens = [], ativo = -1, t;
  const fechar = () => { lista.hidden = true; ativo = -1; inp.setAttribute("aria-expanded", "false"); };
  const desenhar = () => {
    lista.innerHTML = "";
    itens.forEach((it, i) => {
      const li = document.createElement("li"); li.setAttribute("role", "option"); li.setAttribute("aria-selected", i === ativo ? "true" : "false");
      const [a, b] = linha(it); li.innerHTML = "<span></span><span></span>"; li.children[0].textContent = a; li.children[1].textContent = b;
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
function ligarCidade() {
  const inp = $("[data-cidade-input]"), lista = $("[data-cidade-lista]"), resp = $("[data-cidade-resposta]");
  let base = null;
  const carregar = async () => (base ??= (await dados("municipios")).map((m) => ({ nome: m[1], uf: m[2], pop: m[3], vidas: m[4], chave: semAcento(m[1]) })));
  const escolher = (m) => {
    lista.hidden = true; inp.value = `${m.nome} (${m.uf})`;
    const c = m.pop ? m.vidas / m.pop : null;
    resp.textContent = c == null ? `${m.nome}: sem população estimada.` :
      `${m.nome} (${m.uf}): ${pct(Math.min(c, 1))} da população tem plano médico, ${num(m.vidas)} clientes em set/2026.` + (c > 1 ? " Há mais clientes que moradores: o plano é registrado no município da empresa, não no de residência." : "");
  };
  sugestor(inp, lista, async (q) => (await carregar()).filter((m) => casa(m.chave, q)).sort((a, b) => b.pop - a.pop).slice(0, 8), (m) => [m.nome, m.uf], escolher);
  inp.closest("form").addEventListener("submit", async (e) => { e.preventDefault(); const r = (await carregar()).filter((m) => casa(m.chave, semAcento(inp.value.trim()))).sort((a, b) => b.pop - a.pop); if (r[0]) escolher(r[0]); });
}

// ---------------------------------------------------------------- capítulo 4: reclamações
let DESTAQUE = null;   // registro ANS a destacar (vem do link ou do comparador)
async function reclamacoes(uf) {
  const [d, br] = await Promise.all([dados(`uf/${uf}`), dados("uf/brasil")]);
  $('[data-uf-titulo="reclamacoes"]').textContent = `Quem mais gera reclamação ${noUF(uf)}?`;
  $("[data-rec-estado]").textContent = nf(1).format(d.rec_por_mil_estado);
  $("[data-rec-estado-texto]").textContent = `reclamações por mil clientes ${noUF(uf)} em 12 meses. No Brasil, ${nf(1).format(br.rec_por_mil)}.`;
  const rank = d.operadoras.filter((o) => o.no_ranking_reclamacoes && o.rec_por_mil != null).sort((a, b) => b.rec_por_mil - a.rec_por_mil);
  const alvo = $("[data-rec-ranking]");
  if (!rank.length) {
    alvo.innerHTML = `<p class="nota">Nenhuma operadora tem 20 mil clientes ou mais ${noUF(uf)}: com carteiras pequenas, o índice oscila demais para comparar. A média do estado está ao lado.</p>`;
  } else {
    const max = Math.max(...rank.map((o) => o.rec_por_mil), d.rec_por_mil_estado) * 1.05;
    alvo.innerHTML = rank.map((o) => `
      <a class="rec-linha" href="#compare/${uf}/${o.reg}" data-reg="${o.reg}" ${o.reg === DESTAQUE ? 'aria-current="true"' : ""}
         title="${esc(o.nome)}: ${num(o.reclamacoes)} reclamações em 12 meses; principal motivo: ${esc(o.temas[0] ? tema(o.temas[0][0]) : "—")}">
        <span class="rec-nome">${esc(o.nome)}<small>${mil(o.vidas)} clientes, ${pct(o.participacao, 0)} do estado</small></span>
        <span class="rec-barra" aria-hidden="true"><i style="width:${(o.rec_por_mil / max * 100).toFixed(1)}%"></i><b style="left:${(d.rec_por_mil_estado / max * 100).toFixed(1)}%"></b></span>
        <span class="rec-valor">${nf(1).format(o.rec_por_mil)}<small>${o.resolvidas == null ? "—" : "resolveu " + pct(o.resolvidas, 0)}</small></span>
      </a>`).join("") + `<p class="rec-media">Traço escuro: média ${noUF(uf)} (${nf(1).format(d.rec_por_mil_estado)}). ${d.operadoras.length - rank.length} operadoras menores ficam fora da comparação, mas aparecem no comparador.</p>`;
  }
  $("[data-rec-unidade]").textContent = `${rank.length} operadoras com 20 mil clientes ou mais ${noUF(uf)}`;
  $("[data-tema-estado]").innerHTML = `<p><strong>Do que mais se reclama ${noUF(uf)}</strong></p><ul class="tema-lista">${d.temas_estado.slice(0, 4).map(([t, q]) => `<li title="${esc(t)}"><span>${esc(tema(t))}</span><span>${pct(q / d.reclamacoes_estado, 0)}</span></li>`).join("")}</ul>`;
}

// ---------------------------------------------------------------- capítulo 5: comparador
const LINHAS = [
  ["bloco", "No estado"],
  ["vidas", "Clientes no estado", (o) => o.vidas, (v) => mil(v), ""],
  ["participacao", "Participação de mercado no estado", (o) => o.participacao, (v) => pct(v), ""],
  ["cresc_12m", "Crescimento de clientes em 12 meses", (o) => o.cresc_12m, (v) => (v == null ? "—" : sinal(v * 100) + "%"), "maior"],
  ["rec_por_mil", "Reclamações por mil clientes, por ano", (o) => o.rec_por_mil, (v) => num(v, 1), "menor", "NIP/ANS, jul/2025 a jun/2026; oscila em carteiras pequenas"],
  ["resolvidas", "Reclamações resolvidas na mediação", (o) => o.resolvidas, (v) => pct(v, 0), "maior", "Fórmula da ANS"],
  ["tema", "Motivo mais comum de reclamação", (o) => (o.temas[0] ? tema(o.temas[0][0]) : null), (v) => v ?? "—", ""],
  ["hospitais", "Hospitais na rede no estado", (o) => o.hospitais, (v) => num(v), "maior", "Em pelo menos um plano ativo; não mede qualidade"],
  ["hospitais_urgencia", "Desses, com pronto-socorro", (o) => o.hospitais_urgencia, (v) => num(v), "maior"],
  ["preco", "Preço de tabela", null, null, "", "Valor informado à ANS para planos à venda; não é o que cada cliente paga"],
  ["sus", "Ida ao SUS por possível falha de acesso", (o) => o.sus_falha_por_mil, (v) => num(v, 1), "menor", "Por mil clientes, 2024: parto, psiquiatria e cirurgia programável"],
  ["pct59", "Clientes com 59 anos ou mais", (o) => o.pct59, (v) => pct(v, 0), ""],
  ["pct_individual", "Clientes em plano individual", (o) => o.pct_individual, (v) => pct(v, 0), ""],
  ["bloco", "Na operadora inteira"],
  ["sinistralidade", "Quanto da mensalidade volta em atendimento", (o) => o.nacional?.sinistralidade, (v) => pct(v), "", "12 meses, critério da ANS"],
  ["margem", "Lucro sobre a receita", (o) => o.nacional?.margem_liquida, (v) => pct(v), ""],
  ["idss", "Nota de qualidade da ANS (0 a 1)", (o) => o.nacional?.idss, (v) => (v == null ? "—" : nf(3).format(v)), "maior", "IDSS 2025"],
  ["tempo", "Dias para pagar a rede", (o) => o.nacional?.tempo_pagamento_dias, (v) => num(v), "menor"],
  ["glosa", "Quanto da conta da rede é recusado", (o) => o.nacional?.glosa_inicial, (v) => pct(v), ""],
  ["justica", "Cobrança do SUS parada na Justiça", (o) => o.nacional?.sus_pct_justica, (v) => pct(v, 0), "menor"],
];
const ESCOLHA = { faixa: "05", contratacao: "Coletivo empresarial", acomodacao: "Enfermaria" };
const FAIXAS = { "01": "0 a 18 anos", "02": "19 a 23", "03": "24 a 28", "04": "29 a 33", "05": "34 a 38", "06": "39 a 43", "07": "44 a 48", "08": "49 a 53", "09": "54 a 58", "10": "59 anos ou mais" };
let SELECAO = null;    // registros escolhidos no comparador: [principal, ...concorrentes]
let LISTA_DA_ROTA = null, iniciado = false;

function precoDe(o) {
  if (!o.preco) return null;
  const v = o.preco[`${ESCOLHA.faixa}|${ESCOLHA.contratacao}|${ESCOLHA.acomodacao}`];
  return v ? v[0] : null;
}
async function comparador(uf, pedido) {
  const d = await dados(`uf/${uf}`);
  const ops = [...d.operadoras].sort((a, b) => b.vidas - a.vidas);
  $('[data-uf-titulo="compare"]').textContent = `Sua operadora contra as concorrentes ${noUF(uf)}.`;
  const regs = new Set(ops.map((o) => o.reg));
  let sel = (pedido && pedido.length ? pedido : SELECAO || []).filter((r) => regs.has(r));
  if (!sel.length) sel = [ops[0]?.reg].filter(Boolean);
  for (const o of ops) { if (sel.length >= 4) break; if (!sel.includes(o.reg)) sel.push(o.reg); }
  SELECAO = sel;
  const opcoes = (atual) => ops.map((o) => `<option value="${o.reg}" ${o.reg === atual ? "selected" : ""}>${esc(o.nome)} (${mil(o.vidas)})</option>`).join("");
  const temPreco = ops.some((o) => o.preco);
  $("[data-comparar-escolha]").innerHTML = sel.map((r, i) => `<label class="${i === 0 ? "principal" : ""}">${i === 0 ? "Sua operadora" : "Concorrente " + i}<select data-sel="${i}">${opcoes(r)}</select></label>`).join("") +
    (temPreco ? `<label>Idade para o preço<select data-preco="faixa">${Object.entries(FAIXAS).map(([k, v]) => `<option value="${k}" ${k === ESCOLHA.faixa ? "selected" : ""}>${v}</option>`).join("")}</select></label>
      <label>Tipo de plano<select data-preco="contratacao">${["Coletivo empresarial", "Coletivo por adesão", "Individual ou familiar"].map((v) => `<option ${v === ESCOLHA.contratacao ? "selected" : ""}>${v}</option>`).join("")}</select></label>
      <label>Acomodação<select data-preco="acomodacao">${["Enfermaria", "Apartamento"].map((v) => `<option ${v === ESCOLHA.acomodacao ? "selected" : ""}>${v}</option>`).join("")}</select></label>` : "");
  $$("[data-sel]").forEach((s) => s.addEventListener("change", () => {
    const i = +s.dataset.sel, novo = [...SELECAO]; const j = novo.indexOf(s.value);
    if (j >= 0 && j !== i) novo[j] = novo[i];       // trocou para uma já escolhida: inverte as duas
    novo[i] = s.value; SELECAO = novo;
    history.replaceState(null, "", `#compare/${uf}/${novo.join(",")}`);
    comparador(uf, novo);
  }));
  $$("[data-preco]").forEach((s) => s.addEventListener("change", () => { ESCOLHA[s.dataset.preco] = s.value; comparador(uf, SELECAO); }));
  const cols = sel.map((r) => ops.find((o) => o.reg === r));
  const cab = `<thead><tr><th scope="col" class="t-nome">Indicador</th>${cols.map((o, i) => `<th scope="col" class="${i === 0 ? "sua" : ""}">${esc(o.nome)}<br><a href="#operadora/${o.reg}" data-ficha-de="${o.reg}">ver a ficha</a></th>`).join("")}</tr></thead>`;
  const corpo = LINHAS.filter((l) => l[0] === "bloco" || (l[0].startsWith("hospitais") ? cols.some((o) => o.hospitais != null) : true) && (l[0] !== "preco" || temPreco)).map((l) => {
    if (l[0] === "bloco") return `<tr class="bloco"><td colspan="${cols.length + 1}"><span>${l[1]}</span></td></tr>`;
    const [id, nome, ler, fmt, melhor, dica] = l;
    if (id === "preco") {
      const vals = cols.map(precoDe);
      return `<tr><td class="t-ind">${nome}<small>${FAIXAS[ESCOLHA.faixa]}, ${ESCOLHA.contratacao.toLowerCase()}, ${ESCOLHA.acomodacao.toLowerCase()}. ${dica}</small></td>${vals.map((v, i) => `<td class="${i === 0 ? "sua" : ""} num">${v == null ? "sem plano à venda" : reais(v)}</td>`).join("")}</tr>`;
    }
    const vals = cols.map((o) => ler(o));
    const validos = vals.filter((v) => typeof v === "number");
    const alvoMelhor = melhor && validos.length > 1 ? (melhor === "maior" ? Math.max(...validos) : Math.min(...validos)) : null;
    return `<tr><td class="t-ind">${nome}${dica ? `<small>${dica}</small>` : ""}</td>${vals.map((v, i) => `<td class="${i === 0 ? "sua " : ""}${alvoMelhor != null && typeof v === "number" && fmt(v) === fmt(alvoMelhor) ? "melhor" : ""}">${esc(fmt(v))}</td>`).join("")}</tr>`;
  }).join("");
  $("[data-comparar]").innerHTML = cab + "<tbody>" + corpo + "</tbody>";
  $$("[data-ficha-de]").forEach((a) => a.addEventListener("click", (e) => { e.preventDefault(); abrirFicha(a.dataset.fichaDe, true); }));
  DESTAQUE = sel[0];
  $$(".rec-linha").forEach((a) => a.setAttribute("aria-current", a.dataset.reg === DESTAQUE ? "true" : "false"));
  abrirFicha(sel[0], false);
}

// ---------------------------------------------------------------- ficha completa (operadora inteira)
let OPS = null;
async function operadoras() {
  if (!OPS) OPS = await dados("operadoras");
  return OPS;
}
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
const IND = [
  ["sinistralidade", "Quanto da mensalidade volta em atendimento", "pct", "", "Sinistralidade 12 meses, critério da ANS"],
  ["indice_combinado", "Custos para cada R$ 100 recebidos", "pct", "menor", "Acima de 100%, a operação dá prejuízo"],
  ["margem_liquida", "Lucro final sobre a receita", "pct", "maior", "12 meses"],
  ["indice_desp_adm", "Quanto vai para administração", "pct", "menor", "Despesas administrativas sobre as receitas"],
  ["receita_vida_mes", "Receita por cliente, por mês", "brl", "", "Contraprestações por cliente médio"],
  ["custo_vida_mes", "Custo assistencial por cliente, por mês", "brl", "", "Eventos por cliente médio"],
  ["cresc_vidas_12m", "Crescimento de clientes em 12 meses", "pct", "maior", "Brasil, jun/2026 sobre jun/2025"],
  ["pct_59mais", "Clientes com 59 anos ou mais", "pct", "", "Última faixa de reajuste da ANS"],
  ["igr_12m", "Reclamações por 100 mil clientes, por mês", "num1", "menor", "IGR da ANS, Brasil"],
  ["idss", "Nota de qualidade da ANS (0 a 1)", "num3", "maior", "IDSS 2025, ano-base 2024"],
  ["glosa_inicial", "Quanto da conta da rede é recusado (glosa)", "pct", "", "2º semestre de 2025"],
  ["tempo_pagamento_dias", "Dias para pagar a rede", "num0", "menor", "Da cobrança do prestador ao pagamento"],
  ["sus_falha_por_mil", "Uso do SUS por possível falha de acesso", "num1", "menor", "Por mil clientes, 2024"],
  ["sus_pct_justica", "Cobrança do SUS parada na Justiça", "pct", "menor", "2019 a 2025"],
  ["pct_judicial", "Gasto com decisões judiciais", "pct", "menor", "Em % dos eventos, 12 meses"],
  ["pct_ev_rede_propria", "Atendimento em rede própria", "pct", "", "Em % dos eventos, 12 meses"],
];
const FMT = { pct: (v) => pct(v), brl: (v) => brl(v), num0: (v) => num(v, 0), num1: (v) => num(v, 1), num3: (v) => (v == null ? "—" : nf(3).format(v)) };
const FORMAS = { procedimento: "Por procedimento", pacote: "Em pacote", rede_propria: "Rede própria", rede_indireta: "Rede indireta", reembolso: "Reembolso", capitation: "Capitation", orcamento_global: "Orçamento global" };
function faixa(v, q, melhor) {
  if (v == null || !q) return { html: '<div class="faixa" aria-hidden="true"></div>', txt: "" };
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
  const vals = s.filter((v) => v != null); if (vals.length < 2) return '<p class="nota">Sem série trimestral suficiente.</p>';
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
  if (!o) { alvo.innerHTML = `<p class="nota">A operadora de registro ${esc(reg)} não está entre as ativas com dados recentes.</p>`; return; }
  const q = o.ranking ? d.quartis[o.porte] || {} : {};
  const aviso = o.ranking ? `Comparada com as ${q.sinistralidade?.[3] ?? ""} operadoras de porte ${o.porte.toLowerCase()} do Brasil.` : `Fora da comparação por porte: ${esc(o.motivo)}. Os números aparecem, sem comparação.`;
  const linhas = IND.map(([c, nome, f, melhor, expl]) => {
    const v = o.ind[c], fx = faixa(v, q[c], melhor);
    return `<li class="ind"><div class="ind-nome">${nome}<small>${fx.txt || expl}</small></div><div class="ind-valor">${FMT[f](v)}</div>${fx.html}</li>`;
  }).join("");
  const rede = Object.entries(o.rede).filter(([, v]) => v > 0.005).sort((a, b) => b[1] - a[1]);
  const r = o.resultado;
  const fmtMi = (v) => (v == null ? "—" : Math.abs(v) >= 1000 ? sinal(v / 1000, 1) + " bi" : sinal(v, 0) + " mi");
  alvo.innerHTML = `
    <header class="ficha-cabeca">
      <h3>${esc(o.nome)}</h3>
      <p class="ficha-perfil">${esc(o.modalidade)}, porte ${esc(o.porte.toLowerCase())}, registro ANS ${o.reg}, sede em ${esc(o.uf_sede || "—")}${o.vidas ? `, ${num(o.vidas)} clientes no Brasil em jun/2026` : ""}.</p>
      <p class="ficha-aviso">${aviso}</p>
    </header>
    <div class="ficha-grade">
      <div>
        <ul class="ind-lista">${linhas}</ul>
        <p class="faixa-legenda">Faixa cinza: metade do meio das operadoras do mesmo porte no Brasil; traço: mediana; ponto: a operadora. Verde e coral só quando o indicador tem direção clara.</p>
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
        <div><h4>Onde estão os clientes</h4><p>${Object.entries(o.ufs).slice(0, 6).map(([u, v]) => `${NOMES_UF[u] || u} ${mil(v)}`).join("; ") || "—"}.</p></div>
      </div>
    </div>`;
  if (rede.length) barrasHorizontais($("[data-rede]", alvo), rede.map(([k, v]) => ({ rot: FORMAS[k], v, txt: pct(v, 0) })), "Eventos por forma de pagamento à rede", { ml: 130, w: 380, lh: 28 });
  if (rolar) rolarPara(document.getElementById("operadora"));
}
// rola até a seção e confere depois: o conteúdo acima ainda pode estar chegando e empurrar a página
function rolarPara(sec) {
  const ir = () => sec.scrollIntoView({ behavior: "instant", block: "start" });
  ir();
  const conferir = () => { if (Math.abs(sec.getBoundingClientRect().top - 64) > 8) ir(); };
  setTimeout(conferir, 450); setTimeout(conferir, 1500);
}

// ---------------------------------------------------------------- navegação: capítulo atual e links
function capituloAtual() {
  const links = $$(".menu a[data-cap]");
  const io = new IntersectionObserver((ents) => {
    ents.forEach((e) => { if (e.isIntersecting) links.forEach((a) => a.setAttribute("aria-current", a.getAttribute("href") === "#" + e.target.id ? "true" : "false")); });
  }, { rootMargin: "-45% 0px -50% 0px" });
  links.forEach((a) => { const s = document.querySelector(a.getAttribute("href")); if (s) io.observe(s); });
}
// #reclamacoes/CE[/REG] · #compare/CE/REG[,REG...] · #operadora/REG
function rota() {
  let m = location.hash.match(/^#(reclamacoes|compare)\/([A-Z]{2})(?:\/([\d,]+))?$/);
  if (m) {
    const [, onde, uf, regs] = m;
    const lista = regs ? regs.split(",").filter((r) => /^\d{6}$/.test(r)) : null;
    if (lista) { SELECAO = lista; DESTAQUE = lista[0]; }
    if (uf !== UF || !iniciado) { LISTA_DA_ROTA = lista; setEstado(uf); } else { reclamacoes(uf); comparador(uf, lista); }
    rolarPara(document.getElementById(onde === "compare" ? "compare" : "reclamacoes"));
    return;
  }
  m = location.hash.match(/^#operadora\/(\d{6})$/);
  if (m) abrirFicha(m[1], true);
}

// ---------------------------------------------------------------- início
(async () => {
  if (/^#(reclamacoes|compare|operadora)\//.test(location.hash)) history.scrollRestoration = "manual";
  ligarEstados();
  capituloAtual();
  const [m, c, cu] = await Promise.all([dados("mercado"), dados("clientes"), dados("cada_uf")]);
  graficoAnos(m); graficoMapa(c); graficoContratacao(c); ligarCidade();
  quandoMudarEstado((uf) => {
    cem(m, cu, uf); painelUF(c, uf); participacao(c, uf); reclamacoes(uf);
    // trocou de estado: a "sua operadora" fica, se atuar lá; as concorrentes passam a ser as do novo estado
    comparador(uf, LISTA_DA_ROTA || (SELECAO ? SELECAO.slice(0, 1) : null));
    LISTA_DA_ROTA = null;
    const h = location.hash.match(/^#(reclamacoes|compare)\/([A-Z]{2})/);
    if (h && h[2] !== uf) history.replaceState(null, "", `#${h[1]}/${uf}`);
  });
  if (/^#(reclamacoes|compare)\//.test(location.hash)) rota();
  else { setEstado(UF, { guardar: false }); if (/^#operadora\//.test(location.hash)) rota(); }
  iniciado = true;
  window.addEventListener("hashchange", rota);
})();
