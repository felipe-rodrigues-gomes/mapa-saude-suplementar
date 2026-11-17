// Contador de visitas do Mapa, próprio e sem cookie.
// Não guarda IP nem nada que identifique a pessoa: o visitante do dia vira um resumo (hash) de
// segredo + dia + IP + navegador, que só serve para não contar a mesma pessoa duas vezes no dia
// e é apagado na virada do dia. Fica só a contagem: visitas, visitantes, origem, capítulos vistos,
// tempo na página, estado escolhido e perguntas ao assistente.
//
// Pasta permanente: DADOS_DIR (padrão /data, volume do EasyPanel). Painel: GET /api/painel?chave=VISITAS_CHAVE.
import { createHash, randomBytes } from "node:crypto";
import { existsSync, mkdirSync, readFileSync, renameSync, writeFileSync } from "node:fs";
import { join } from "node:path";

const DIR = process.env.DADOS_DIR || "/data";
const ARQ = join(DIR, "visitas.json");
const ROBO = /bot|crawl|spider|slurp|preview|headless|lighthouse|facebookexternalhit|whatsapp\/|linkedinbot|slackbot|telegrambot|python|curl|wget|httpclient|okhttp/i;
const CAPITULOS = new Set(["inicio", "mensalidade", "lucro", "clientes", "reclamacoes", "compare", "operadora", "metodo"]);
const UFS = new Set("AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO".split(" "));

// dia no horário de Fortaleza (UTC−3)
export const hoje = () => new Date(Date.now() - 3 * 3600e3).toISOString().slice(0, 10);

let base = { segredo: null, dias: {}, idsDoDia: { dia: null, ids: [] } };
let sujo = false;
try { mkdirSync(DIR, { recursive: true }); } catch { /* sem pasta: só memória */ }
try { if (existsSync(ARQ)) base = { ...base, ...JSON.parse(readFileSync(ARQ, "utf8")) }; } catch (e) { console.error("visitas: arquivo ilegível, começando do zero", e.message); }
if (!base.segredo) { base.segredo = randomBytes(24).toString("hex"); sujo = true; }
let ids = new Set(base.idsDoDia.dia === hoje() ? base.idsDoDia.ids : []);

function salvar() {
  if (!sujo) return;
  try {
    base.idsDoDia = { dia: hoje(), ids: [...ids] };
    writeFileSync(ARQ + ".tmp", JSON.stringify(base));
    renameSync(ARQ + ".tmp", ARQ);
    sujo = false;
  } catch (e) { console.error("visitas: não consegui gravar", e.message); }
}
setInterval(salvar, 5000).unref();
for (const s of ["SIGTERM", "SIGINT"]) process.on(s, () => { salvar(); process.exit(0); });

function dia() {
  const d = hoje();
  if (base.idsDoDia.dia !== d && ids.size && base.idsDoDia.dia) { ids = new Set(); }
  base.idsDoDia.dia = d;
  return (base.dias[d] ??= { visitas: 0, visitantes: 0, origens: {}, capitulos: {}, estados: {}, tempo: { soma: 0, n: 0, faixas: {} }, perguntas: 0 });
}
const soma = (obj, k, n = 1) => { obj[k] = (obj[k] || 0) + n; };

function origem(o, ref) {
  if (o && /^[a-z0-9-]{1,24}$/.test(o)) return o;
  let h = "";
  try { h = new URL(ref).hostname.replace(/^www\./, ""); } catch { /* sem referência */ }
  if (!h) return "direto";
  if (/feliperodrigues\.cloud$|github\.io$/.test(h)) return "interno";
  if (/linkedin\.com$|lnkd\.in$/.test(h)) return "linkedin";
  if (/github\.com$/.test(h)) return "github";
  if (/whatsapp/.test(h)) return "whatsapp";
  if (/google\./.test(h)) return "google";
  if (/(facebook|instagram)\.com$/.test(h)) return "meta";
  if (/(t\.co|x\.com|twitter\.com)$/.test(h)) return "x";
  return "outro:" + h.slice(0, 40); // o site de origem (não é dado pessoal), para saber de onde vem o "outro"
}

export function ehRobo(ua) { return !ua || ROBO.test(ua); }

// uma visita por carregamento da página
export function visita({ o, ref } = {}, ip, ua) {
  if (ehRobo(ua)) return;
  const d = dia();
  const id = createHash("sha256").update(`${base.segredo}|${hoje()}|${ip}|${ua}`).digest("hex").slice(0, 16);
  soma(d, "visitas");
  if (!ids.has(id)) { ids.add(id); soma(d, "visitantes"); }
  soma(d.origens, origem(String(o || ""), String(ref || "")));
  sujo = true;
}

// ao sair: capítulos que apareceram na tela, tempo na página e o estado escolhido
export function saida({ c, s, uf } = {}, ua) {
  if (ehRobo(ua)) return;
  const d = dia();
  for (const x of Array.isArray(c) ? c.slice(0, 12) : []) if (CAPITULOS.has(x)) soma(d.capitulos, x);
  const seg = Number(s);
  if (Number.isFinite(seg) && seg >= 0 && seg < 6 * 3600) {
    d.tempo.soma += seg; d.tempo.n += 1;
    soma(d.tempo.faixas, seg < 10 ? "<10s" : seg < 30 ? "10-30s" : seg < 60 ? "30-60s" : seg < 180 ? "1-3min" : "3min+");
  }
  if (UFS.has(uf)) soma(d.estados, uf);
  sujo = true;
}

export function pergunta() { soma(dia(), "perguntas"); sujo = true; }

// do que se perguntou: só a classificação da IA (listas fechadas), nunca o texto
const INTENCOES = new Set(["operadora", "reclamacoes", "comparar", "preco", "lucro", "mensalidade", "mercado", "glossario", "fora"]);
const TEMAS = new Set(["cancelamento", "negativa", "cobertura", "reembolso", "carencia", "reajuste", "rede", "portabilidade", "como_reclamar", "outro"]);
export function assunto(intencao, tema) {
  if (!INTENCOES.has(intencao)) return;
  const d = dia();
  soma((d.intencoes ??= {}), intencao);
  if (intencao === "fora" && TEMAS.has(tema)) soma((d.temas ??= {}), tema);
  sujo = true;
}

export function resumo(dias = 30) {
  const chaves = Object.keys(base.dias).sort().slice(-dias);
  return Object.fromEntries(chaves.map((k) => [k, base.dias[k]]));
}

const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
const lista = (obj) => Object.entries(obj || {}).sort((a, b) => b[1] - a[1]).map(([k, v]) => `${esc(k)} ${v}`).join(", ") || "—";

export function painelHtml() {
  const r = resumo(60), dias = Object.keys(r).sort().reverse();
  const tot = { visitas: 0, visitantes: 0, perguntas: 0, origens: {}, capitulos: {}, estados: {}, faixas: {}, intencoes: {}, temas: {}, tempo: 0, n: 0 };
  for (const k of dias) {
    const d = r[k];
    tot.visitas += d.visitas; tot.visitantes += d.visitantes; tot.perguntas += d.perguntas; tot.tempo += d.tempo.soma; tot.n += d.tempo.n;
    for (const [a, b] of [["origens", d.origens], ["capitulos", d.capitulos], ["estados", d.estados], ["faixas", d.tempo.faixas], ["intencoes", d.intencoes], ["temas", d.temas]]) for (const [x, v] of Object.entries(b || {})) soma(tot[a], x, v);
  }
  const media = (s, n) => (n ? `${Math.round(s / n)} s` : "—");
  const linhas = dias.map((k) => { const d = r[k]; return `<tr><td>${k}</td><td>${d.visitantes}</td><td>${d.visitas}</td><td>${lista(d.origens)}</td><td>${media(d.tempo.soma, d.tempo.n)}</td><td>${d.perguntas}</td></tr>`; }).join("");
  return `<!doctype html><html lang="pt-BR"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta name="robots" content="noindex"><title>Visitas do Mapa</title>
<style>body{font-family:system-ui,sans-serif;background:#f6f4f0;color:#0d344b;margin:0;padding:24px;max-width:960px}h1{font-size:24px}h2{font-size:17px;margin-top:28px}
table{border-collapse:collapse;width:100%;font-size:14px;background:#fefdfc}td,th{border-bottom:1px solid #dfdcd5;padding:8px;text-align:left;vertical-align:top}th{background:#ece9e3}
.n{font-size:34px;font-weight:800}.cartoes{display:flex;gap:16px;flex-wrap:wrap}.cartoes div{background:#fefdfc;padding:14px 18px;border-radius:8px;min-width:140px}p{color:#59656e;font-size:13px}</style></head><body>
<h1>Visitas do Mapa da saúde suplementar</h1>
<div class="cartoes"><div><div class="n">${tot.visitantes}</div>visitantes</div><div><div class="n">${tot.visitas}</div>visitas</div><div><div class="n">${media(tot.tempo, tot.n)}</div>tempo médio na página</div><div><div class="n">${tot.perguntas}</div>perguntas ao assistente</div></div>
<h2>De onde vieram</h2><p>${lista(tot.origens)}</p>
<h2>Até onde leram (capítulos que apareceram na tela)</h2><p>${lista(tot.capitulos)}</p>
<h2>Tempo na página</h2><p>${lista(tot.faixas)}</p>
<h2>Estado escolhido ao sair</h2><p>${lista(tot.estados)}</p>
<h2>O que perguntaram ao assistente</h2><p>${lista(tot.intencoes)}</p>
<h2>Perguntas que o mapa ainda não responde, por tema</h2><p>${lista(tot.temas)}</p>
<h2>Por dia</h2><table><tr><th>Dia</th><th>Visitantes</th><th>Visitas</th><th>Origem</th><th>Tempo médio</th><th>Perguntas</th></tr>${linhas}</table>
<p>Das perguntas fica só a classificação (intenção e tema, de listas fechadas), nunca o texto. Contagem desde 17/11/2026. Sem cookie e sem IP guardado. Visitante = pessoa distinta no dia (resumo apagado na virada do dia). Robôs e prévias de link não contam. Horário de Fortaleza.</p>
</body></html>`;
}
