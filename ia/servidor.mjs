// Assistente do Mapa da saúde suplementar: só INTERPRETA a pergunta.
// Recebe {pergunta, uf}, pede a um modelo gratuito (Gemini; Groq de reserva) a intenção em JSON
// e devolve só campos de listas fechadas. Os números da resposta saem dos dados do site, no navegador:
// o modelo nunca escreve número nenhum.
// Sem dependências: Node 22 (fetch e http nativos).
//
// Variáveis (EasyPanel): GEMINI_API_KEY, GEMINI_MODELO (padrão gemini-flash-lite-latest),
// GROQ_API_KEY + GROQ_MODELO (opcional, reserva), LIMITE_DIA (padrão 1200 interpretações/dia no total),
// LIMITE_IP_MIN (padrão 8), LIMITE_IP_DIA (padrão 40), PORTA (padrão 3000).
// Contador de visitas (visitas.mjs): DADOS_DIR (padrão /data, volume) e VISITAS_CHAVE (senha do painel /api/painel).
import http from "node:http";
import * as visitas from "./visitas.mjs";

const env = process.env;
const PORTA = Number(env.PORTA || 3000);
const GEMINI_MODELO = env.GEMINI_MODELO || "gemini-flash-lite-latest";
const LIMITE_DIA = Number(env.LIMITE_DIA || 1200);
const LIMITE_IP_MIN = Number(env.LIMITE_IP_MIN || 8);
const LIMITE_IP_DIA = Number(env.LIMITE_IP_DIA || 40);

const INTENCOES = ["operadora", "reclamacoes", "comparar", "preco", "lucro", "mensalidade", "mercado", "glossario", "fora"];
const TERMOS = ["sinistralidade", "idss", "reclamacao", "indice_combinado", "preco_tabela", "glosa", "ressarcimento_sus", "aplicacoes", "participacao_mercado", "mensalidade_media"];
// perguntas "fora" do site, por tema (lista fechada): mostra o que as pessoas procuram e o mapa ainda não responde,
// sem guardar o texto da pergunta. Ideia de Diego Arruda nos comentários do LinkedIn.
const TEMAS_FORA = ["cancelamento", "negativa", "cobertura", "reembolso", "carencia", "reajuste", "rede", "portabilidade", "como_reclamar", "outro"];
const UFS = ["AC", "AL", "AM", "AP", "BA", "CE", "DF", "ES", "GO", "MA", "MG", "MS", "MT", "PA", "PB", "PE", "PI", "PR", "RJ", "RN", "RO", "RR", "RS", "SC", "SE", "SP", "TO"];

const INSTRUCAO = `Você classifica perguntas feitas no site "Mapa da saúde suplementar", que mostra dados públicos da ANS sobre operadoras de plano de saúde no Brasil.
Responda SOMENTE com o JSON pedido. Nunca escreva números, opiniões nem respostas: só classifique.

intencao:
- "operadora": como está uma operadora específica (ex.: "a Hapvida é boa?", "me fala da Unimed Fortaleza")
- "reclamacoes": quem tem mais ou menos reclamação, ranking de reclamações (com ou sem operadora citada)
- "comparar": comparar duas ou mais operadoras, ou uma operadora com as concorrentes
- "preco": quanto custa um plano, preço por idade ou tipo de plano
- "lucro": lucro, de onde vem o lucro, aplicações financeiras, se a operadora ganha ou perde dinheiro
- "mensalidade": mensalidade média, para onde vai o dinheiro da mensalidade, quanto vai para atendimento
- "mercado": maiores operadoras, participação de mercado, concentração, quem domina o estado
- "glossario": o que significa um termo (preencha "termo")
- "fora": qualquer outra coisa (cobertura de um exame, como cancelar, reclamar de um caso pessoal, assuntos fora do site)

operadoras: os nomes das operadoras citadas, como o usuário escreveu (ex.: ["hapvida", "unimed fortaleza"]). Lista vazia se nenhuma.
uf: sigla do estado citado na pergunta (ex.: "Ceará" -> "CE", "Fortaleza" -> "CE"), ou null se nenhum.
idade: idade citada (número inteiro), ou null.
contratacao: "individual", "empresarial" ou "adesao" se citado, ou null.
acomodacao: "enfermaria" ou "apartamento" se citado, ou null.
ordem: "menos" se a pergunta busca o menor/melhor (menos reclamação, mais barato), "mais" se busca o maior/pior, ou null.
termo: para "glossario", um destes: ${TERMOS.join(", ")}; senão null.
tema: SÓ para "fora", o assunto da pergunta; senão null.
- "cancelamento": cancelar o plano, multa ou aviso de cancelamento, plano cancelado pela operadora
- "negativa": operadora negou ou não autorizou cirurgia, exame, internação ou tratamento; demora na autorização
- "cobertura": se o plano cobre um exame, cirurgia, remédio ou terapia; rol da ANS
- "reembolso": reembolso de consulta ou procedimento, valor ou prazo do reembolso
- "carencia": prazos de carência, doença preexistente, cobertura parcial temporária
- "reajuste": aumento da mensalidade, reajuste anual ou por faixa etária
- "rede": rede credenciada, achar médico ou hospital, descredenciamento, demora para marcar
- "portabilidade": trocar de plano ou de operadora levando as carências
- "como_reclamar": como ou onde reclamar, abrir reclamação na ANS, ouvidoria
- "outro": qualquer outro assunto`;

const ESQUEMA = {
  type: "OBJECT",
  properties: {
    intencao: { type: "STRING", enum: INTENCOES },
    operadoras: { type: "ARRAY", items: { type: "STRING" } },
    uf: { type: "STRING", nullable: true, enum: UFS },
    idade: { type: "INTEGER", nullable: true },
    contratacao: { type: "STRING", nullable: true, enum: ["individual", "empresarial", "adesao"] },
    acomodacao: { type: "STRING", nullable: true, enum: ["enfermaria", "apartamento"] },
    ordem: { type: "STRING", nullable: true, enum: ["mais", "menos"] },
    termo: { type: "STRING", nullable: true, enum: TERMOS },
    tema: { type: "STRING", nullable: true, enum: TEMAS_FORA },
  },
  required: ["intencao", "operadoras"],
};

// só passa o que é de lista fechada: o texto do modelo nunca chega à tela
function limpar(x) {
  const de = (v, lista) => (lista.includes(v) ? v : null);
  const ops = Array.isArray(x?.operadoras) ? x.operadoras.filter((s) => typeof s === "string").map((s) => s.slice(0, 60)).slice(0, 4) : [];
  const idade = Number.isInteger(x?.idade) && x.idade >= 0 && x.idade <= 110 ? x.idade : null;
  const intencao = de(x?.intencao, INTENCOES) || "fora";
  return {
    intencao, operadoras: ops, uf: de(String(x?.uf || "").toUpperCase(), UFS), idade,
    contratacao: de(x?.contratacao, ["individual", "empresarial", "adesao"]), acomodacao: de(x?.acomodacao, ["enfermaria", "apartamento"]),
    ordem: de(x?.ordem, ["mais", "menos"]), termo: de(x?.termo, TERMOS),
    tema: intencao === "fora" ? de(x?.tema, TEMAS_FORA) || "outro" : null,
  };
}

async function gemini(pergunta, uf) {
  const r = await fetch(`https://generativelanguage.googleapis.com/v1beta/models/${GEMINI_MODELO}:generateContent`, {
    method: "POST", headers: { "content-type": "application/json", "x-goog-api-key": env.GEMINI_API_KEY },
    body: JSON.stringify({
      systemInstruction: { parts: [{ text: INSTRUCAO }] },
      contents: [{ role: "user", parts: [{ text: `Estado escolhido no site: ${uf || "nenhum"}.\nPergunta: ${pergunta}` }] }],
      generationConfig: { responseMimeType: "application/json", responseSchema: ESQUEMA, temperature: 0, maxOutputTokens: 1024 },
    }),
    signal: AbortSignal.timeout(8000),
  });
  if (!r.ok) throw new Error(`gemini ${r.status}: ${(await r.text()).slice(0, 200)}`);
  const j = await r.json();
  const txt = j?.candidates?.[0]?.content?.parts?.map((p) => p.text || "").join("") || "";
  return JSON.parse(txt);
}

async function groq(pergunta, uf) {
  const r = await fetch("https://api.groq.com/openai/v1/chat/completions", {
    method: "POST", headers: { "content-type": "application/json", authorization: `Bearer ${env.GROQ_API_KEY}` },
    body: JSON.stringify({
      model: env.GROQ_MODELO, temperature: 0, max_tokens: 400, response_format: { type: "json_object" },
      messages: [{ role: "system", content: INSTRUCAO + "\nCampos: intencao, operadoras, uf, idade, contratacao, acomodacao, ordem, termo, tema." },
        { role: "user", content: `Estado escolhido no site: ${uf || "nenhum"}.\nPergunta: ${pergunta}` }],
    }),
    signal: AbortSignal.timeout(8000),
  });
  if (!r.ok) throw new Error(`groq ${r.status}: ${(await r.text()).slice(0, 200)}`);
  const j = await r.json();
  return JSON.parse(j?.choices?.[0]?.message?.content || "{}");
}

// ---------------------------------------------------------------- limites e cache (em memória)
const hoje = () => new Date().toISOString().slice(0, 10);
let dia = hoje(), totalDia = 0;
const porIp = new Map();   // ip -> {min, inicioMin, dia}
const cache = new Map();   // pergunta normalizada|uf -> resposta (as 1000 mais recentes)
function permitir(ip) {
  const agora = Date.now();
  if (dia !== hoje()) { dia = hoje(); totalDia = 0; porIp.clear(); }
  const c = porIp.get(ip) || { min: 0, inicioMin: agora, dia: 0 };
  if (agora - c.inicioMin > 60_000) { c.min = 0; c.inicioMin = agora; }
  if (c.min >= LIMITE_IP_MIN || c.dia >= LIMITE_IP_DIA) return "ip";
  if (totalDia >= LIMITE_DIA) return "dia";
  c.min++; c.dia++; porIp.set(ip, c);
  return null;
}
const normalizar = (s) => s.normalize("NFD").replace(/[̀-ͯ]/g, "").toLowerCase().replace(/[^a-z0-9 ]+/g, " ").replace(/\s+/g, " ").trim();

async function interpretar(pergunta, uf) {
  const chave = normalizar(pergunta) + "|" + (uf || "");
  if (cache.has(chave)) return { ...cache.get(chave), cache: true };
  let bruto = null, provedor = null, erros = [];
  if (env.GEMINI_API_KEY) { try { bruto = await gemini(pergunta, uf); provedor = "gemini"; } catch (e) { erros.push(String(e.message || e)); } }
  if (!bruto && env.GROQ_API_KEY && env.GROQ_MODELO) { try { bruto = await groq(pergunta, uf); provedor = "groq"; } catch (e) { erros.push(String(e.message || e)); } }
  if (!bruto) { const e = new Error(erros.join(" | ") || "nenhum provedor configurado"); e.semProvedor = !erros.length; throw e; }
  totalDia++;
  const out = { ...limpar(bruto), provedor };
  cache.set(chave, out);
  if (cache.size > 1000) cache.delete(cache.keys().next().value);
  return out;
}

// teto de eventos do contador: 60 por minuto por IP (evita inflar os números)
const eventos = new Map();
function eventoPermitido(ip) {
  const agora = Date.now(), e = eventos.get(ip) || { n: 0, t: agora };
  if (agora - e.t > 60_000) { e.n = 0; e.t = agora; }
  e.n++; eventos.set(ip, e);
  if (eventos.size > 5000) eventos.clear();
  return e.n <= 60;
}

// ---------------------------------------------------------------- HTTP
function responder(res, status, obj) {
  res.writeHead(status, { "content-type": "application/json; charset=utf-8", "cache-control": "no-store", "x-content-type-options": "nosniff" });
  res.end(JSON.stringify(obj));
}
const servidor = http.createServer(async (req, res) => {
  const url = new URL(req.url, "http://x");
  if (req.method === "GET" && url.pathname === "/api/saude") {
    return responder(res, 200, { ok: true, gemini: !!env.GEMINI_API_KEY, modelo: GEMINI_MODELO, groq: !!(env.GROQ_API_KEY && env.GROQ_MODELO), hoje: totalDia, limite: LIMITE_DIA });
  }
  const ipReq = String(req.headers["x-forwarded-for"] || req.socket.remoteAddress || "").split(",")[0].trim();
  const ua = String(req.headers["user-agent"] || "");
  // contador de visitas: eventos pequenos, sem resposta útil (204), com teto por IP
  if (req.method === "POST" && (url.pathname === "/api/visita" || url.pathname === "/api/visita/fim")) {
    if (!eventoPermitido(ipReq)) { res.writeHead(204); return res.end(); }
    let c = "";
    for await (const parte of req) { c += parte; if (c.length > 1500) { res.writeHead(413); return res.end(); } }
    let ev = {};
    try { ev = JSON.parse(c || "{}"); } catch { /* corpo inválido: ignora */ }
    if (url.pathname === "/api/visita") visitas.visita(ev, ipReq, ua); else visitas.saida(ev, ua);
    res.writeHead(204, { "cache-control": "no-store" }); return res.end();
  }
  if (req.method === "GET" && url.pathname === "/api/painel") {
    if (!env.VISITAS_CHAVE || url.searchParams.get("chave") !== env.VISITAS_CHAVE) return responder(res, 403, { erro: "chave inválida" });
    if (url.searchParams.get("formato") === "json") return responder(res, 200, visitas.resumo(90));
    res.writeHead(200, { "content-type": "text/html; charset=utf-8", "cache-control": "no-store", "x-robots-tag": "noindex" });
    return res.end(visitas.painelHtml());
  }
  if (req.method !== "POST" || url.pathname !== "/api/perguntar") return responder(res, 404, { erro: "não encontrado" });
  let corpo = "";
  for await (const parte of req) { corpo += parte; if (corpo.length > 2000) return responder(res, 413, { erro: "pergunta grande demais" }); }
  let p;
  try { p = JSON.parse(corpo); } catch { return responder(res, 400, { erro: "json inválido" }); }
  const pergunta = String(p?.pergunta || "").trim().slice(0, 300), uf = UFS.includes(p?.uf) ? p.uf : null;
  if (pergunta.length < 2) return responder(res, 400, { erro: "pergunta vazia" });
  const ip = String(req.headers["x-forwarded-for"] || req.socket.remoteAddress || "").split(",")[0].trim();
  const bloqueio = permitir(ip);
  if (bloqueio) return responder(res, 429, { erro: bloqueio === "dia" ? "limite do dia" : "muitas perguntas seguidas" });
  const humano = !visitas.ehRobo(ua);
  if (humano) visitas.pergunta();
  try {
    const r = await interpretar(pergunta, uf);
    if (humano) visitas.assunto(r.intencao, r.tema);   // só a classificação, nunca o texto
    console.log(`${new Date().toISOString()} ${r.provedor}${r.cache ? " cache" : ""} ${r.intencao}${r.tema ? "/" + r.tema : ""}`);   // sem a pergunta e sem IP: podem ter dado pessoal
    return responder(res, 200, r);
  } catch (e) {
    console.error(`${new Date().toISOString()} falha: ${e.message}`);
    return responder(res, e.semProvedor ? 503 : 502, { erro: "interpretação indisponível" });
  }
});
servidor.listen(PORTA, () => console.log(`assistente na porta ${PORTA}; gemini=${!!env.GEMINI_API_KEY} (${GEMINI_MODELO}) groq=${!!env.GROQ_API_KEY}`));
