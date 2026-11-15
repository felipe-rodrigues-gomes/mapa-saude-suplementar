"""Camada enxuta para o Power BI (dados/pbi/*.parquet). Só operadoras médico-hospitalares.

dOperadora   operadora (cadastro + foto atual de ind_operadora)
dTrimestre   trimestre 2021T1–2026T2
dCompetencia mês (fins de trimestre da carteira e meses do IGR)
fContabil    operadora × trimestre (acumulado no ano e 12 meses; numeradores e denominadores)
fCarteira    competência × operadora × contratação × faixa de reajuste (vidas médicas)
fIGR         operadora × mês (reclamações e beneficiários, assistência médica)
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from comum import *

PBI = RAIZ / "dados" / "pbi"
PBI.mkdir(parents=True, exist_ok=True)


def salvar(df: pd.DataFrame, nome: str):
    """Grava com tipos que o conector Parquet do Power Query lê sem surpresa:
    texto como string (não large_string nem categoria), datas em microssegundos."""
    import pyarrow as pa, pyarrow.parquet as pq
    df = df.copy()
    for c in df.columns:
        if isinstance(df[c].dtype, pd.CategoricalDtype) or df[c].dtype == object or str(df[c].dtype).startswith("str"):
            df[c] = df[c].astype(object).where(df[c].notna(), None)
    t = pa.Table.from_pandas(df, preserve_index=False)
    campos = []
    for f in t.schema:
        tp = f.type
        if pa.types.is_large_string(tp) or pa.types.is_dictionary(tp) or pa.types.is_string(tp):
            tp = pa.string()
        elif pa.types.is_integer(tp):
            tp = pa.int64()
        campos.append(pa.field(f.name, tp))
    pq.write_table(t.cast(pa.schema(campos)), PBI / f"{nome}.parquet")

dim = pd.read_parquet(TRATADOS / "dim_operadora.parquet")
ind = pd.read_parquet(TRATADOS / "ind_operadora.parquet")
mh = dim[dim.SEGMENTO == "MH"]
regs = set(mh.REG)

# ---------- dOperadora
foto = ["sinistralidade", "sinistralidade_ano_ant", "indice_combinado", "indice_desp_adm", "margem_liquida",
        "resultado_liquido", "resultado_operacional", "resultado_financeiro", "contraprest_efet",
        "vidas_mh", "cresc_vidas_12m", "pct_59mais", "pct_individual", "pct_empresarial", "pct_adesao",
        "receita_vida_mes", "custo_vida_mes", "igr_12m", "idss", "idqs", "idga", "idsm", "idgr",
        "glosa_inicial", "glosa_final", "flag_glosa", "tempo_pagamento_dias",
        "sus_por_mil", "sus_falha_por_mil", "sus_pct_justica", "sus_pct_pago", "pct_judicial",
        "pct_ev_procedimento", "pct_ev_pacote", "pct_ev_rede_propria", "pct_ev_rede_indireta",
        "pct_ev_capitation", "pct_ev_orcamento_global", "pct_ev_reembolso",
        "RANKING_OK", "MOTIVO_FORA_RANKING"]
d = mh[["REG", "NOME_EXIBICAO", "RAZAO_SOCIAL", "CNPJ", "MODALIDADE", "PORTE", "ATIVA", "UF_SEDE", "REGIAO_SEDE",
        "UF_PRINCIPAL"]].merge(ind[["REG"] + foto], on="REG", how="left")
d["RANKING_OK"] = d.RANKING_OK.fillna(False).astype(bool)
d["MOTIVO_FORA_RANKING"] = d.MOTIVO_FORA_RANKING.where(~d.RANKING_OK, None)
d.loc[~d.RANKING_OK & d.MOTIVO_FORA_RANKING.isna(), "MOTIVO_FORA_RANKING"] = "Sem dados recentes"
d["flag_glosa"] = d.flag_glosa.astype("boolean").fillna(True).astype(bool)
d["BUSCA"] = d.NOME_EXIBICAO.str.strip() + " · " + d.REG     # nome único para a caixa de busca
salvar(d, "dOperadora")

# ---------- fContabil
con = pd.read_parquet(TRATADOS / "fato_contabil.parquet")
con = con[con.REG.isin(regs)]
base = ["sinist_num", "sinist_den", "comb_num", "comb_den", "contraprest_efet", "desp_assist", "desp_adm",
        "desp_comerc", "resultado_liquido", "resultado_operacional", "resultado_financeiro", "jud_total",
        "ev_conhecidos", "ev_procedimento", "ev_pacote", "ev_rede_propria", "ev_rede_indireta",
        "ev_capitation", "ev_orcamento_global", "ev_reembolso"]
cols = ["REG", "PERIODO"] + [f"{b}_{v}" for b in base for v in ("ytd", "12m")]
salvar(con[cols], "fContabil")

# ---------- dTrimestre
t = con[["PERIODO", "ANO", "TRI", "DATA_FIM"]].drop_duplicates().sort_values("PERIODO").reset_index(drop=True)
t["ROTULO"] = t.TRI.astype(str) + "º tri " + t.ANO.astype(str)
t["ROTULO_CURTO"] = t.ANO.astype(str).str[2:] + "T" + t.TRI.astype(str)
t["ORDEM"] = t.index + 1
t["FIM_DE_ANO"] = t.TRI == 4
salvar(t, "dTrimestre")

# ---------- fCarteira
ben = pd.read_parquet(TRATADOS / "fato_beneficiarios.parquet")
b = ben[(ben.COBERTURA == "MH") & ben.REG.isin(regs)]
b = b.groupby(["COMPETENCIA", "REG", "CONTRATACAO", "FAIXA_REAJ"], observed=True).ATIVOS.sum().reset_index()
b = b[b.ATIVOS > 0]
for c in ["CONTRATACAO", "FAIXA_REAJ"]:
    b[c] = b[c].astype(str)
salvar(b, "fCarteira")

# ---------- fIGR
igr = pd.read_parquet(TRATADOS / "fato_igr.parquet")
g = igr[(igr.COBERTURA == "MH") & igr.REG.isin(regs) & (igr.COMPETENCIA >= "202101")]
salvar(g[["REG", "COMPETENCIA", "QTD_RECLAMACOES", "QTD_BENEFICIARIOS"]], "fIGR")

# ---------- dCompetencia
comp = sorted(set(b.COMPETENCIA) | set(g.COMPETENCIA))
c = pd.DataFrame({"COMPETENCIA": comp})
c["DATA"] = pd.to_datetime(c.COMPETENCIA + "01", format="%Y%m%d")
meses = "jan fev mar abr mai jun jul ago set out nov dez".split()
c["ROTULO"] = c.DATA.dt.month.map(lambda m: meses[m - 1]) + "/" + c.DATA.dt.year.astype(str).str[2:]
c["ANO"] = c.DATA.dt.year
c["FIM_DE_TRIMESTRE"] = c.DATA.dt.month.isin([3, 6, 9, 12])
salvar(c, "dCompetencia")

# ---------- dIndicador (tabela desconectada que alimenta a ficha: uma linha por indicador)
# MELHOR: "menor" / "maior" / "" (sem julgamento: depende do contexto)
ind_def = [
    ("sinistralidade", "Quanto da mensalidade volta em atendimento", "Sinistralidade 12 meses: (eventos + corresponsabilidade cedida) ÷ (contraprestações efetivas + corresponsabilidade cedida), critério da ANS.", "pct", ""),
    ("indice_combinado", "Custos para cada R$ 100 recebidos", "Índice combinado 12 meses (ANS). Acima de 100% a operação do plano dá prejuízo.", "pct", "menor"),
    ("margem_liquida", "Lucro final sobre a receita", "Resultado líquido ÷ contraprestações efetivas, 12 meses.", "pct", "maior"),
    ("indice_desp_adm", "Quanto vai para administração", "Despesas administrativas ÷ (contraprestações efetivas + corresponsabilidade cedida + receitas administrativas), 12 meses.", "pct", "menor"),
    ("receita_vida_mes", "Receita por cliente, por mês", "Contraprestações efetivas 12 meses ÷ média de vidas médicas ÷ 12.", "brl", ""),
    ("custo_vida_mes", "Custo assistencial por cliente, por mês", "Eventos indenizáveis 12 meses ÷ média de vidas médicas ÷ 12.", "brl", ""),
    ("cresc_vidas_12m", "Crescimento de clientes em 12 meses", "Vidas médicas jun/2026 ÷ jun/2025 − 1.", "pct", "maior"),
    ("pct_59mais", "Clientes com 59 anos ou mais", "Faixa de reajuste da ANS, jun/2026.", "pct", ""),
    ("igr_12m", "Reclamações por 100 mil clientes, por mês", "IGR da ANS ponderado de jul/2025 a jun/2026. Abaixo de 20 mil clientes o índice oscila muito.", "num1", "menor"),
    ("idss", "Nota de qualidade da ANS (0 a 1)", "IDSS 2025, ano-base 2024.", "num3", "maior"),
    ("glosa_inicial", "Quanto da conta da rede é recusado (glosa)", "Glosa inicial, 2º semestre de 2025 (painel de glosas da ANS). Valores improváveis ficam em branco.", "pct", ""),
    ("tempo_pagamento_dias", "Dias para pagar a rede", "Tempo médio entre a cobrança do prestador e o pagamento, 2º semestre de 2025.", "num0", "menor"),
    ("sus_falha_por_mil", "Uso do SUS por possível falha de acesso (por mil)", "Parto, psiquiatria e cirurgia programável identificados no ressarcimento ao SUS, atendimentos de 2024.", "num1", "menor"),
    ("sus_pct_justica", "Cobrança do SUS parada na Justiça", "Valor cobrado pelo ressarcimento ao SUS (2019–2025) suspenso judicialmente ÷ total cobrado.", "pct", "menor"),
    ("pct_judicial", "Gasto com decisões judiciais", "Despesas judiciais (eventos cobertos e não cobertos) ÷ eventos indenizáveis, 12 meses.", "pct", "menor"),
    ("pct_ev_rede_propria", "Atendimento em rede própria", "Eventos por rateio de rede própria ÷ eventos conhecidos, 12 meses.", "pct", ""),
]
di = pd.DataFrame(ind_def, columns=["CODIGO", "INDICADOR", "COMO_CALCULA", "FORMATO", "MELHOR"])
di["ORDEM"] = range(1, len(di) + 1)
salvar(di, "dIndicador")

# ---------- dFormaPagamento (desconectada: uma linha por forma de pagamento à rede)
fp = pd.DataFrame([("procedimento", "Por procedimento"), ("pacote", "Em pacote"), ("rede_propria", "Rede própria"),
                   ("rede_indireta", "Rede indireta"), ("reembolso", "Reembolso"), ("capitation", "Capitation"),
                   ("orcamento_global", "Orçamento global")], columns=["CODIGO", "FORMA"])
fp["ORDEM"] = range(1, len(fp) + 1)
salvar(fp, "dFormaPagamento")

for f in sorted(PBI.glob("*.parquet")):
    x = pd.read_parquet(f)
    print(f"{f.name:22s} {len(x):>9,} linhas  {len(x.columns):>3} colunas  {f.stat().st_size / 1e6:6.2f} MB")
