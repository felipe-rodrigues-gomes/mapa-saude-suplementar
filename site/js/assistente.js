// "Pergunte ao mapa": botão flutuante que responde com os números do próprio site.
// A IA (servidor /api/perguntar, ver ia/servidor.mjs) só diz QUAL é a pergunta; a resposta é montada aqui,
// a partir dos mesmos JSON das telas. Sem o servidor (cópia no GitHub Pages, cota esgotada, fora do ar),
// uma leitura local por palavras-chave faz o mesmo papel para as perguntas mais comuns.

const nf = (d) => new Intl.NumberFormat("pt-BR", { minimumFractionDigits: d, maximumFractionDigits: d });
const pct = (v, d = 1) => (v == null ? "—" : nf(d).format(v * 100) + "%");
const mil = (v) => (v >= 1e6 ? `${nf(1).format(v / 1e6)} ${v >= 2e6 ? "milhões" : "milhão"}` : v >= 1e3 ? nf(0).format(v / 1e3) + " mil" : nf(0).format(v));
const clientes = (v) => `${mil(v)}${v >= 1e6 ? " de" : ""} clientes`;
const real = (v) => `R$ ${nf(0).format(v)}`;
const reais = (v) => `R$ ${nf(2).format(v)}`;
const esc = (s) => String(s ?? "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" })[c]);
const norm = (s) => String(s || "").normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9 ]+/g, " ").replace(/\s+/g, " ").trim();

const VERSAO = new URL(import.meta.url).searchParams.get("v") || "";
const cache = {};
const dados = (nome) => (cache[nome] ??= fetch(`dados/${nome}.json?v=${VERSAO}`).then((r) => { if (!r.ok) throw new Error(nome); return r.json(); }));

const NOMES_UF = { AC: "Acre", AL: "Alagoas", AM: "Amazonas", AP: "Amapá", BA: "Bahia", CE: "Ceará", DF: "Distrito Federal", ES: "Espírito Santo", GO: "Goiás", MA: "Maranhão", MG: "Minas Gerais", MS: "Mato Grosso do Sul", MT: "Mato Grosso", PA: "Pará", PB: "Paraíba", PE: "Pernambuco", PI: "Piauí", PR: "Paraná", RJ: "Rio de Janeiro", RN: "Rio Grande do Norte", RO: "Rondônia", RR: "Roraima", RS: "Rio Grande do Sul", SC: "Santa Catarina", SE: "Sergipe", SP: "São Paulo", TO: "Tocantins" };
const PREP = { AC: "no", AL: "em", AM: "no", AP: "no", BA: "na", CE: "no", DF: "no", ES: "no", GO: "em", MA: "no", MG: "em", MS: "em", MT: "em", PA: "no", PB: "na", PE: "em", PI: "no", PR: "no", RJ: "no", RN: "no", RO: "em", RR: "em", RS: "no", SC: "em", SE: "em", SP: "em", TO: "no" };
const noUF = (uf) => `${PREP[uf]} ${NOMES_UF[uf]}`;
const ufAtual = () => document.querySelector("[data-estado]")?.value || (() => { try { return localStorage.getItem("mapa.uf"); } catch { return null; } })() || "SP";
const FAIXAS = { "01": "0 a 18 anos", "02": "19 a 23 anos", "03": "24 a 28 anos", "04": "29 a 33 anos", "05": "34 a 38 anos", "06": "39 a 43 anos", "07": "44 a 48 anos", "08": "49 a 53 anos", "09": "54 a 58 anos", "10": "59 anos ou mais" };
const faixaDe = (idade) => (idade == null ? "05" : idade <= 18 ? "01" : idade >= 59 ? "10" : String(Math.floor((idade - 19) / 5) + 2).padStart(2, "0"));
const CONTRATACAO = { individual: "Individual ou familiar", empresarial: "Coletivo empresarial", adesao: "Coletivo por adesão" };

// ---------------------------------------------------------------- achar operadora pelo nome
const VAZIAS = new Set(["de", "do", "da", "dos", "das", "e", "s", "a", "sa", "ltda", "saude", "plano", "planos", "assistencia", "medica", "medico", "hospitalar", "operadora", "cooperativa", "trabalho", "coop", "the", "o"]);
const GENERICAS = new Set(["unimed", "sul", "associacao", "caixa", "fundacao", "central", "sao", "santa", "hospital", "clinica", "sociedade", "uniao", "federacao", "instituto", "servico", "prevent"]);
const fichas = (nome) => norm(nome).split(" ").filter((t) => t && !VAZIAS.has(t));
// mencionada pelo usuário (texto livre) -> operadora de uma lista, a maior quando houver empate
function acharPorMencao(mencao, lista) {
  const m = fichas(mencao); if (!m.length) return null;
  // palavra a palavra ("unimed fortaleza") ou tudo junto ("sulamerica" = "sul america", "notredame")
  const junto = m.join("");
  const cands = lista.filter((o) => { const t = fichas(o.nome); return m.every((p) => t.some((x) => x.startsWith(p))) || (junto.length >= 4 && t.join("").includes(junto)); });
  return cands.sort((a, b) => (b.vidas || 0) - (a.vidas || 0))[0] || null;
}
// leitura local: quais operadoras da lista aparecem na pergunta
function acharNaPergunta(q, lista) {
  const qt = new Set(norm(q).split(" "));
  // cada operadora casa por uma "chave" (1ª palavra do nome; 2 palavras se a 1ª for genérica, como Unimed);
  // por chave fica a que tem mais palavras do nome na pergunta e, no empate, a maior: "Hapvida" é a HAPVIDA, não a NotreDame
  const porChave = new Map();
  for (const o of lista) {
    const t = fichas(o.nome); if (!t.length) continue;
    const precisa = GENERICAS.has(t[0]) && t[1] ? t.slice(0, 2) : t.slice(0, 1);
    if (!precisa.every((p) => qt.has(p)) && !qt.has(precisa.join(""))) continue;
    const ponto = t.filter((p) => qt.has(p)).length, chave = precisa.join(" "), atual = porChave.get(chave);
    if (!atual || ponto > atual.ponto || (ponto === atual.ponto && (o.vidas || 0) > (atual.o.vidas || 0))) porChave.set(chave, { o, ponto });
  }
  let achadas = [...porChave.values()].map((x) => x.o);
  // palavra genérica sozinha ("unimed", sem a cidade): a maior operadora com esse nome
  for (const g of GENERICAS) {
    if (!qt.has(g) || achadas.some((o) => fichas(o.nome)[0] === g)) continue;
    const u = lista.filter((o) => fichas(o.nome)[0] === g).sort((a, b) => b.vidas - a.vidas)[0];
    if (u) achadas.push(u);
  }
  // ordem em que aparecem na pergunta
  const nq = " " + norm(q) + " ", pos = (o) => { const i = nq.indexOf(" " + fichas(o.nome)[0]); return i < 0 ? 999 : i; };
  return achadas.sort((a, b) => pos(a) - pos(b)).slice(0, 4);
}

// ---------------------------------------------------------------- leitura local (sem IA)
const ESTADOS = [["rio grande do sul", "RS"], ["rio grande do norte", "RN"], ["rio de janeiro", "RJ"], ["mato grosso do sul", "MS"], ["mato grosso", "MT"], ["espirito santo", "ES"], ["distrito federal", "DF"], ["brasilia", "DF"], ["sao paulo", "SP"], ["minas gerais", "MG"], ["minas", "MG"], ["santa catarina", "SC"], ["parana", "PR"], ["paraiba", "PB"], ["pernambuco", "PE"], ["ceara", "CE"], ["fortaleza", "CE"], ["bahia", "BA"], ["salvador", "BA"], ["goias", "GO"], ["amazonas", "AM"], ["manaus", "AM"], ["amapa", "AP"], ["acre", "AC"], ["alagoas", "AL"], ["maranhao", "MA"], ["piaui", "PI"], ["rondonia", "RO"], ["roraima", "RR"], ["sergipe", "SE"], ["tocantins", "TO"], ["recife", "PE"], ["belo horizonte", "MG"], ["curitiba", "PR"], ["porto alegre", "RS"]];
function lerLocal(q) {
  const n = ` ${norm(q)} `;
  let uf = null;
  for (const [nome, s] of ESTADOS) if (n.includes(` ${nome} `)) { uf = s; break; }
  if (!uf && /\bPará\b/.test(q)) uf = "PA";
  if (!uf) { const m = q.match(/\b(AC|AL|AM|AP|BA|CE|DF|ES|GO|MA|MG|MS|MT|PA|PB|PE|PI|PR|RJ|RN|RO|RR|RS|SC|SE|SP|TO)\b/); if (m) uf = m[1]; }
  const idade = (n.match(/ (\d{1,2}) anos /) || [])[1];
  const tem = (re) => re.test(n);
  const termo = tem(/o que (e|sao|significa)|significa|quer dizer|como funciona/) ? (
    tem(/sinistral/) ? "sinistralidade" : tem(/idss|nota de qualidade/) ? "idss" : tem(/indice combinado/) ? "indice_combinado" : tem(/glosa/) ? "glosa" :
    tem(/ressarc|sus/) ? "ressarcimento_sus" : tem(/aplica/) ? "aplicacoes" : tem(/participa|market share/) ? "participacao_mercado" :
    tem(/preco de tabela|tabela/) ? "preco_tabela" : tem(/reclama|nip/) ? "reclamacao" : tem(/mensalidade media/) ? "mensalidade_media" : null) : null;
  const intencao = termo ? "glossario"
    : tem(/compar| versus | vs | ou a | x /) ? "comparar"
    : tem(/reclam/) ? "reclamacoes"
    : tem(/lucr|aplicac|ganha dinheiro|prejuiz/) ? "lucro"
    : tem(/preco|custa|caro|barat|valor do plano|tabela/) || idade ? "preco"
    : tem(/mensalidade|para onde vai|pra onde vai|atendimento/) ? "mensalidade"
    : tem(/maior|maiores|mercado|participa|lider|domina|concentr/) ? "mercado"
    : "operadora";
  const ordem = tem(/menos|menor|melhor|mais barat/) ? "menos" : tem(/mais|maior|pior/) ? "mais" : null;
  const contratacao = tem(/individual|familiar/) ? "individual" : tem(/empresa|empresarial/) ? "empresarial" : tem(/adesao/) ? "adesao" : null;
  const acomodacao = tem(/apartamento/) ? "apartamento" : tem(/enfermaria/) ? "enfermaria" : null;
  return { intencao, operadoras: null, uf, idade: idade ? Number(idade) : null, contratacao, acomodacao, ordem, termo, local: true };
}

async function interpretar(q, uf) {
  try {
    const r = await fetch("api/perguntar", { method: "POST", headers: { "content-type": "application/json" }, body: JSON.stringify({ pergunta: q, uf }), signal: AbortSignal.timeout(9000) });
    if (r.ok) { const j = await r.json(); if (j?.intencao) return j; }
  } catch { /* sem servidor: leitura local */ }
  return lerLocal(q);
}

// ---------------------------------------------------------------- respostas (números dos JSON do site)
const GLOSSARIO = {
  sinistralidade: ["Sinistralidade é quanto da mensalidade volta em atendimento: consultas, exames, internações. O resto paga administração, venda e impostos, e o que sobra é o resultado da operadora.", "#mensalidade", "Ver para onde vai a mensalidade"],
  idss: ["IDSS é a nota de qualidade que a ANS dá a cada operadora, de 0 a 1. Considera cuidado com a saúde, acesso à rede, situação financeira e atendimento ao cliente. O site usa o IDSS 2025, com dados de 2024.", "#compare", "Comparar operadoras"],
  reclamacao: ["São as reclamações registradas na ANS (a NIP), contadas a cada mil clientes por ano, para comparar operadoras de tamanhos diferentes. \"Resolvida na mediação\" é quando a operadora resolveu sem virar processo.", "#reclamacoes", "Ver o ranking de reclamações"],
  indice_combinado: ["Índice combinado é quanto a operadora gasta com atendimento, administração e venda para cada R$ 100 que recebe de mensalidade. Acima de 100%, a operação do plano dá prejuízo.", "#lucro", "Ver o lucro das operadoras"],
  preco_tabela: ["Preço de tabela é o valor que a operadora informa à ANS para os planos à venda, por idade e tipo de plano. Não é o que cada cliente paga: empresas costumam negociar desconto.", "#compare", "Ver preços no comparador"],
  glosa: ["Glosa é a parte da conta que o hospital ou a clínica cobra e a operadora se recusa a pagar.", "#compare", "Comparar operadoras"],
  ressarcimento_sus: ["Quando um cliente de plano é atendido no SUS, a operadora tem de devolver o valor ao SUS. O site destaca os casos que indicam falha de acesso à rede do plano, como parto e cirurgia programável.", "#compare", "Comparar operadoras"],
  aplicacoes: ["A operadora recebe a mensalidade antes de pagar os atendimentos e é obrigada pela ANS a guardar reservas. Esse dinheiro fica aplicado, e o rendimento entra no resultado.", "#lucro", "Ver de onde vem o lucro"],
  participacao_mercado: ["Participação de mercado é a parte dos clientes de plano médico de um estado que está em cada operadora.", "#clientes", "Ver a participação de mercado"],
  mensalidade_media: ["Mensalidade média é o que as operadoras receberam de mensalidade no estado, dividido pelos clientes, por mês. É uma estimativa: a ANS publica as contas por operadora, não por estado.", "#mensalidade", "Ver a mensalidade do seu estado"],
};

function origemLucro(r) {
  const { operacao: op, aplicacoes: ap, lucro: lu } = r || {};
  if (op == null || ap == null || lu == null) return "";
  const em = (v) => { const a = Math.abs(v); return a >= 1000 ? `R$ ${nf(1).format(a / 1000)} ${a < 2000 ? "bilhão" : "bilhões"}` : `R$ ${nf(a < 10 ? 1 : 0).format(a)} ${a < 2 ? "milhão" : "milhões"}`; };
  if (lu >= 0 && op < 0) return `Em 12 meses, a operação do plano deu prejuízo de ${em(op)}, e o lucro de ${em(lu)} veio de fora dela${ap > 0 ? ", das aplicações" : ""}.`;
  if (lu >= 0 && ap <= 0) return `Em 12 meses, lucrou ${em(lu)}, e o lucro vem da operação do plano.`;
  if (lu >= 0) {
    const s = op / (op + ap);
    return `Em 12 meses, lucrou ${em(lu)}, ` + (s >= 0.6 ? `principalmente com a operação do plano (${pct(s, 0)} do que operação e aplicações somaram).` : s <= 0.4 ? `principalmente com as aplicações (${pct(1 - s, 0)} do que operação e aplicações somaram).` : `em partes parecidas da operação e das aplicações.`);
  }
  if (op < 0) return `Em 12 meses, a operação do plano deu prejuízo de ${em(op)}${ap > 0 ? `, e as aplicações (${em(ap)}) não cobriram` : ""}: prejuízo final de ${em(lu)}.`;
  return `Em 12 meses, a operação do plano deu lucro, mas o resultado final foi prejuízo de ${em(lu)}.`;
}

async function resolverOperadoras(intent, q, d) {
  if (intent.operadoras == null) return { estado: acharNaPergunta(q, d.operadoras), fora: [] };
  const estado = [], fora = [];
  const nac = (await dados("operadoras")).operadoras;
  for (const m of intent.operadoras) {
    const o = acharPorMencao(m, d.operadoras);
    if (o) { if (!estado.some((x) => x.reg === o.reg)) estado.push(o); continue; }
    const n = acharPorMencao(m, nac);
    if (n) fora.push(n);
  }
  return { estado, fora };
}

async function responder(q) {
  const ufTela = ufAtual();
  const intent = await interpretar(q, ufTela);
  const uf = intent.uf && NOMES_UF[intent.uf] ? intent.uf : ufTela;
  const d = await dados(`uf/${uf}`);
  const { estado: ops, fora } = await resolverOperadoras(intent, q, d);
  const rank = d.operadoras.filter((o) => o.no_ranking_reclamacoes && o.rec_por_mil != null).sort((a, b) => b.rec_por_mil - a.rec_por_mil);
  const nac = async (reg) => (await dados("operadoras")).operadoras.find((x) => x.reg === reg);
  const r = { texto: "", links: [], via: intent.local ? "local" : "ia" };
  let it = intent.intencao;
  if (ops.length >= 2 && ["operadora", "reclamacoes", "lucro", "mercado"].includes(it)) it = "comparar";
  if (it === "operadora" && !ops.length && !fora.length && intent.local) return foraDoSite(uf);

  if (it === "glossario" && GLOSSARIO[intent.termo]) {
    const [t, h, rot] = GLOSSARIO[intent.termo];
    r.texto = esc(t); r.links.push([h.startsWith("#compare") ? `#compare/${uf}` : h, rot]);
    return r;
  }
  if (it === "fora" || (it === "glossario")) return foraDoSite(uf);

  if (it === "reclamacoes" && !ops.length) {
    if (!rank.length) { r.texto = `Nenhuma operadora tem 20 mil clientes ou mais ${noUF(uf)}, e com carteiras pequenas o índice oscila demais para um ranking. A média do estado é de ${nf(1).format(d.rec_por_mil_estado)} reclamações por mil clientes por ano.`; r.links.push([`#reclamacoes/${uf}`, "Ver reclamações"]); return r; }
    const menos = intent.ordem === "menos", lista = (menos ? [...rank].reverse() : rank).slice(0, 3);
    r.texto = `${menos ? "Menos" : "Mais"} reclamação ${noUF(uf)}, entre as ${rank.length} operadoras com 20 mil clientes ou mais: ` +
      lista.map((o) => `<strong>${esc(o.nome)}</strong> (${nf(1).format(o.rec_por_mil)})`).join(", ") +
      `, em reclamações na ANS por mil clientes por ano. A média do estado é ${nf(1).format(d.rec_por_mil_estado)}.`;
    r.links.push([`#reclamacoes/${uf}`, "Ver o ranking completo"]);
    return r;
  }
  if (it === "mensalidade" || (it === "lucro" && !ops.length && !fora.length)) {
    const [cu, merc] = await Promise.all([dados("cada_uf"), dados("mercado")]), c = cu[uf], m = Math.round(c.mensalidade);
    const k = merc.cada100, br = { mensalidade: cu.BR.mensalidade, sobra_bi: k.sobra * k.receita_bi / 100, lucro_bi: k.lucro * k.receita_bi / 100, aplicacoes_bi: k.aplicacoes * k.receita_bi / 100 };
    const R = { atendimento: Math.round(c.mensalidade * c.atendimento / 100), administracao: Math.round(c.mensalidade * c.administracao / 100), venda: Math.round(c.mensalidade * c.venda / 100), outras: Math.round(c.mensalidade * c.outras / 100), sobra: Math.round(c.mensalidade * c.sobra / 100) };
    R.atendimento += m - (R.atendimento + R.administracao + R.venda + R.outras + R.sobra);
    const bi = (v) => (Math.abs(v) >= 1 ? `R$ ${nf(1).format(v)} ${Math.abs(v) < 2 ? "bilhão" : "bilhões"}` : `R$ ${nf(0).format(v * 1000)} milhões`);
    if (it === "mensalidade") {
      r.texto = `A mensalidade média ${noUF(uf)} é de <strong>${real(m)}</strong> por mês (no Brasil, ${real(br.mensalidade)}). Dela, ${real(R.atendimento)} voltam em atendimento, ${real(R.administracao)} vão para administração, ${real(R.venda)} para venda e ${real(R.outras)} para outras despesas; ${R.sobra >= 0 ? `sobram ${real(R.sobra)} para a operadora` : `a operação perde ${real(-R.sobra)}`}. É uma estimativa: a ANS publica as contas por operadora, não por estado.`;
      r.links.push(["#mensalidade", "Ver a conta da mensalidade"]);
    } else {
      r.texto = `${noUF(uf)[0].toUpperCase() + noUF(uf).slice(1)}, a operação dos planos deixou ${bi(c.sobra_bi)} em 12 meses, e o lucro das operadoras foi de <strong>${bi(c.lucro_bi)}</strong>. No Brasil, foram ${bi(br.sobra_bi)} da operação e ${bi(br.lucro_bi)} de lucro: a diferença vem principalmente das aplicações financeiras (${bi(br.aplicacoes_bi)}). Valores do estado são estimados.`;
      r.links.push(["#lucro", "Ver de onde vem o lucro"]);
    }
    return r;
  }
  if (it === "mercado" && !ops.length) {
    const top = [...d.operadoras].sort((a, b) => b.vidas - a.vidas).slice(0, 5), t3 = top.slice(0, 3).reduce((s, o) => s + o.participacao, 0);
    r.texto = `As maiores ${noUF(uf)}, pela participação nos ${clientes(d.clientes)} de plano médico: ` + top.map((o) => `<strong>${esc(o.nome)}</strong> (${pct(o.participacao)})`).join(", ") + `. As 3 maiores somam ${pct(t3, 0)}.`;
    r.links.push(["#clientes", "Ver a participação de mercado"]);
    return r;
  }
  if (it === "preco") {
    const fx = faixaDe(intent.idade), ct = CONTRATACAO[intent.contratacao] || "Coletivo empresarial", ac = intent.acomodacao === "apartamento" ? "Apartamento" : "Enfermaria";
    const chave = `${fx}|${ct}|${ac}`, quem = `${FAIXAS[fx]}, ${ct.toLowerCase()}, ${ac.toLowerCase()}`;
    const precoDe = (o) => o.preco?.[chave]?.[0] ?? null;
    if (ops.length) {
      r.texto = `Preço de tabela ${noUF(uf)} (${quem}): ` + ops.map((o) => `<strong>${esc(o.nome)}</strong> ${precoDe(o) == null ? "sem plano à venda nesse perfil" : reais(precoDe(o))}`).join("; ") + ".";
    } else {
      const com = d.operadoras.filter((o) => precoDe(o) != null).sort((a, b) => precoDe(a) - precoDe(b));
      if (!com.length) return Object.assign(r, { texto: `Não há preço de tabela informado ${noUF(uf)} para ${quem}.`, links: [[`#compare/${uf}`, "Abrir o comparador"]] });
      const mediana = precoDe(com[Math.floor(com.length / 2)]);
      r.texto = `Preço de tabela ${noUF(uf)} para ${quem}: os menores são ` + com.slice(0, 3).map((o) => `<strong>${esc(o.nome)}</strong> (${reais(precoDe(o))})`).join(", ") + `. O preço do meio, entre ${com.length} operadoras, é ${reais(mediana)}.`;
    }
    r.texto += " É o valor informado à ANS para planos à venda, não o que cada cliente paga.";
    if (!intent.contratacao || !intent.acomodacao) r.texto += ` Para outro perfil, pergunte com o tipo: individual, empresarial ou por adesão; enfermaria ou apartamento.`;
    r.links.push([`#compare/${uf}${ops.length ? "/" + ops.map((o) => o.reg).join(",") : ""}`, "Ver no comparador"]);
    return r;
  }
  if (it === "comparar" && ops.length) {
    const lista = ops.length >= 2 ? ops : [ops[0], ...[...d.operadoras].sort((a, b) => b.vidas - a.vidas).filter((o) => o.reg !== ops[0].reg).slice(0, 2)];
    r.texto = `${ops.length >= 2 ? "Comparação" : `${esc(ops[0].nome)} e as maiores concorrentes`} ${noUF(uf)}:<ul>` + lista.map((o) =>
      `<li><strong>${esc(o.nome)}</strong>: ${clientes(o.vidas)} (${pct(o.participacao)}), ${o.rec_por_mil == null ? "sem índice de reclamação" : `${nf(1).format(o.rec_por_mil)} reclamações por mil`}${o.hospitais != null ? `, ${nf(0).format(o.hospitais)} hospitais na rede` : ""}${o.nacional?.sinistralidade != null ? `, ${pct(o.nacional.sinistralidade, 0)} da mensalidade volta em atendimento` : ""}.</li>`).join("") + `</ul>Média de reclamações ${noUF(uf)}: ${nf(1).format(d.rec_por_mil_estado)} por mil clientes.`;
    r.links.push([`#compare/${uf}/${lista.map((o) => o.reg).join(",")}`, "Ver a comparação completa"]);
    return r;
  }
  // operadora (e reclamações, mercado ou lucro de uma operadora citada)
  if (ops.length) {
    const o = ops[0], n = await nac(o.reg), pos = rank.findIndex((x) => x.reg === o.reg);
    const partes = [`<strong>${esc(o.nome)}</strong> tem ${clientes(o.vidas)} ${noUF(uf)}, ${pct(o.participacao)} do mercado do estado.`];
    if (o.rec_por_mil != null) partes.push(`Reclamações na ANS: ${nf(1).format(o.rec_por_mil)} por mil clientes por ano, contra ${nf(1).format(d.rec_por_mil_estado)} na média do estado` + (pos >= 0 ? ` (${pos + 1}ª maior entre ${rank.length})` : ", com carteira pequena demais para o ranking") + ".");
    if (it !== "reclamacoes" && o.nacional?.sinistralidade != null) partes.push(`Da mensalidade, ${pct(o.nacional.sinistralidade, 0)} volta em atendimento (operadora inteira).`);
    if (it === "lucro" || it === "operadora") { const f = origemLucro(n?.resultado); if (f) partes.push(f); }
    r.texto = partes.join(" ");
    r.links.push([`#operadora/${o.reg}`, "Abrir a ficha completa"], [`#compare/${uf}/${o.reg}`, "Comparar com as concorrentes"]);
    return r;
  }
  if (fora.length) {
    const n = fora[0], f = origemLucro(n.resultado);
    r.texto = `<strong>${esc(n.nome)}</strong> não está entre as operadoras com clientes ${noUF(uf)}. No Brasil, tem ${n.vidas ? clientes(n.vidas) : "— clientes"} de plano médico.` + (f ? " " + f : "");
    r.links.push([`#operadora/${n.reg}`, "Abrir a ficha completa"]);
    return r;
  }
  if (it === "comparar" || it === "operadora") {
    r.texto = `Não achei essa operadora ${noUF(uf)}. Escreva o nome como aparece na carteirinha, por exemplo “${esc(titulo([...d.operadoras].sort((a, b) => b.vidas - a.vidas)[0]?.nome || "Hapvida"))}”, ou escolha outro estado no topo da página.`;
    return r;
  }
  return foraDoSite(uf);
}
const titulo = (s) => s.toLowerCase().replace(/(^|\s)\S/g, (c) => c.toUpperCase());
function foraDoSite(uf) {
  return { texto: `Eu respondo com os números deste site: operadoras, reclamações, preço de tabela, lucro, mensalidade e participação de mercado, por estado. Para dúvidas sobre o seu contrato ou uma negativa de cobertura, o canal é a própria operadora ou a ANS (Disque ANS 0800 701 9656).`, links: [], sugestoes: true };
}

// ---------------------------------------------------------------- interface
async function sugestoes() {
  const uf = ufAtual();
  let maior = "Hapvida";
  try { const d = await dados(`uf/${uf}`); maior = titulo([...d.operadoras].sort((a, b) => b.vidas - a.vidas)[0].nome); } catch { /* fica o exemplo */ }
  return [`Quem tem menos reclamação ${noUF(uf)}?`, `Como está a ${maior}?`, "Quanto custa um plano para 40 anos?", "De onde vem o lucro das operadoras?", "O que é sinistralidade?"];
}

function montar() {
  const botao = document.createElement("button");
  botao.type = "button"; botao.className = "ia-botao"; botao.textContent = "Pergunte ao mapa";
  botao.setAttribute("aria-expanded", "false"); botao.setAttribute("aria-controls", "ia-painel");
  const painel = document.createElement("section");
  painel.id = "ia-painel"; painel.className = "ia-painel"; painel.hidden = true;
  painel.setAttribute("role", "dialog"); painel.setAttribute("aria-labelledby", "ia-titulo");
  painel.innerHTML = `
    <header class="ia-cabeca">
      <h2 id="ia-titulo">Pergunte ao mapa</h2>
      <button type="button" class="ia-fechar" data-ia-fechar>Fechar</button>
    </header>
    <div class="ia-conversa" data-ia-conversa aria-live="polite">
      <p class="ia-intro">Respondo com os números do próprio site, para o estado escolhido no topo. Não digite dados pessoais.</p>
      <div class="ia-sugestoes" data-ia-sugestoes></div>
    </div>
    <form class="ia-form" data-ia-form>
      <label class="ia-rotulo" for="ia-pergunta">Sua pergunta</label>
      <div class="ia-campo">
        <input id="ia-pergunta" type="text" maxlength="300" autocomplete="off" placeholder="Ex.: a Unimed reclama mais que a Hapvida?">
        <button type="submit" class="ia-enviar">Perguntar</button>
      </div>
    </form>`;
  document.body.append(botao, painel);
  const conversa = painel.querySelector("[data-ia-conversa]"), inp = painel.querySelector("#ia-pergunta"), form = painel.querySelector("[data-ia-form]");

  const desenharSugestoes = async (alvo) => {
    alvo.innerHTML = (await sugestoes()).map((s) => `<button type="button" class="ia-chip">${esc(s)}</button>`).join("");
    alvo.querySelectorAll(".ia-chip").forEach((b) => b.addEventListener("click", () => perguntar(b.textContent)));
  };
  const abrir = () => { painel.hidden = false; botao.setAttribute("aria-expanded", "true"); desenharSugestoes(painel.querySelector("[data-ia-sugestoes]")); inp.focus(); };
  const fechar = () => { painel.hidden = true; botao.setAttribute("aria-expanded", "false"); botao.focus(); };
  botao.addEventListener("click", () => (painel.hidden ? abrir() : fechar()));
  painel.querySelector("[data-ia-fechar]").addEventListener("click", fechar);
  painel.addEventListener("keydown", (e) => { if (e.key === "Escape") fechar(); });

  let ocupado = false;
  async function perguntar(q) {
    q = String(q || "").trim(); if (!q || ocupado) return;
    ocupado = true; inp.value = "";
    const eu = document.createElement("p"); eu.className = "ia-eu"; eu.textContent = q;
    const resp = document.createElement("div"); resp.className = "ia-resp"; resp.textContent = "Procurando nos dados…";
    conversa.append(eu, resp); resp.scrollIntoView({ block: "end" });
    try {
      const r = await responder(q);
      resp.innerHTML = `<p>${r.texto}</p>` + (r.links.length ? `<p class="ia-links">${r.links.map(([h, t]) => `<a href="${esc(h)}">${esc(t)}</a>`).join("")}</p>` : "");
      if (r.sugestoes) { const s = document.createElement("div"); s.className = "ia-sugestoes"; resp.append(s); await desenharSugestoes(s); }
      resp.querySelectorAll(".ia-links a").forEach((a) => a.addEventListener("click", () => { if (window.matchMedia("(max-width: 40rem)").matches) fechar(); }));
    } catch {
      resp.textContent = "Não consegui ler os dados agora. Tente de novo em instantes.";
    }
    resp.scrollIntoView({ block: "end" });
    ocupado = false;
  }
  form.addEventListener("submit", (e) => { e.preventDefault(); perguntar(inp.value); });
}

if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", montar); else montar();
// para testes no console
window.__mapaIA = { responder, lerLocal, acharPorMencao };
