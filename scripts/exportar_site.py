"""Etapa 5: dados do site (site/dados/*.json), já agregados para o navegador não fazer conta pesada.

mercado.json     gancho (resultado por ano), sinistralidade 12m, quadro por modalidade
clientes.json    carteira por contratação e idade, cobertura por UF e mapa (caminhos SVG)
municipios.json  cobertura por município (busca da sua cidade)
qualidade.json   pontos sinistralidade × reclamação × nota ANS
sus.json         ressarcimento: grupos de leitura, modalidades, cobrança
operadoras.json  ficha de cada operadora ativa + quartis do porte (mesmas regras das medidas do Power BI)
"""
import json, math, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from comum import *

SITE = RAIZ / "site" / "dados"
SITE.mkdir(parents=True, exist_ok=True)
PER = "2026T2"


def r(x, n=4):
    if x is None or (isinstance(x, float) and (math.isnan(x) or math.isinf(x))):
        return None
    return round(float(x), n)


def gravar(nome, obj):
    txt = json.dumps(obj, ensure_ascii=False, separators=(",", ":"), allow_nan=False)
    (SITE / f"{nome}.json").write_text(txt, encoding="utf-8")
    print(f"{nome}.json  {len(txt) / 1024:,.0f} KB")


def limpa(o):
    if isinstance(o, dict):
        return {k: limpa(v) for k, v in o.items()}
    if isinstance(o, list):
        return [limpa(v) for v in o]
    if isinstance(o, float):
        return r(o)
    if hasattr(o, "item"):
        return limpa(o.item())
    return o


dim = pd.read_parquet(TRATADOS / "dim_operadora.parquet")
ind = pd.read_parquet(TRATADOS / "ind_operadora.parquet")
con = pd.read_parquet(TRATADOS / "fato_contabil.parquet").merge(dim[["REG", "SEGMENTO", "MODALIDADE"]], on="REG")
con = con[con.SEGMENTO == "MH"]
ben = pd.read_parquet(TRATADOS / "fato_beneficiarios.parquet")
mh = ben[ben.COBERTURA == "MH"]
rk = ind[ind.RANKING_OK]

# ------------------------------------------------------------------ mercado
anos = []
for ano, g in con[con.TRI == 4].groupby("ANO"):
    anos.append({"ano": int(ano), "operacao": g.resultado_operacional_ytd.sum() / 1e9,
                 "aplicacoes": g.resultado_financeiro_ytd.sum() / 1e9, "lucro": g.resultado_liquido_ytd.sum() / 1e9,
                 "sinist": g.sinist_num_ytd.sum() / g.sinist_den_ytd.sum()})
anos = [a for a in anos if 2021 <= a["ano"] <= 2025]
serie = []
for per, g in con[con.PERIODO >= "2021T4"].groupby("PERIODO"):
    linha = {"periodo": per, "mercado": g.sinist_num_12m.sum() / g.sinist_den_12m.sum()}
    for m, gm in g.groupby("MODALIDADE"):
        if gm.sinist_den_12m.sum() > 0:
            linha[m] = gm.sinist_num_12m.sum() / gm.sinist_den_12m.sum()
    serie.append(linha)


def quadro(g):
    w = g.vidas_mh
    return {"operadoras": len(g), "vidas": w.sum(),
            "sinist": g.sinist_num.sum() / g.sinist_den.sum(),
            "combinado": g.comb_num.sum() / g.comb_den.sum(),
            "margem": g.resultado_liquido.sum() / g.contraprest_efet.sum(),
            "pct_prejuizo": (g.resultado_liquido < 0).mean(),
            "pct_prejuizo_operacao": (g.resultado_operacional < 0).mean(),
            "receita_vida": g.contraprest_efet.sum() / g.vidas_mh_media_12m.sum() / 12,
            "custo_vida": g.desp_assist.sum() / g.vidas_mh_media_12m.sum() / 12,
            "pct59": (g.pct_59mais * w).sum() / w.sum()}


por_mod = {m: quadro(g) for m, g in rk.groupby("MODALIDADE")}
mercado = {
    "atualizado": "15/11/2026", "periodo_contabil": "12 meses até jun/2026",
    "anos": anos,
    "acumulado": {k: sum(a[k] for a in anos) for k in ("operacao", "aplicacoes", "lucro")},
    "operadoras_ranking": int(len(rk)),
    "pct_salvas": float(((rk.resultado_operacional < 0) & (rk.resultado_liquido > 0)).mean()),
    "pct_prejuizo_operacao": float((rk.resultado_operacional < 0).mean()),
    "pct_prejuizo": float((rk.resultado_liquido < 0).mean()),
    "sinist_12m": serie, "modalidades": por_mod, "total": quadro(rk),
}
gravar("mercado", limpa(mercado))

# ------------------------------------------------------------------ clientes e mapa
comp = sorted(mh.COMPETENCIA.unique())
contrat = mh.groupby(["COMPETENCIA", "CONTRATACAO"], observed=True).ATIVOS.sum().unstack(fill_value=0)
faixa = mh.groupby(["COMPETENCIA", "FAIXA_REAJ"], observed=True).ATIVOS.sum().unstack(fill_value=0)
evol = [{"comp": c, "total": int(contrat.loc[c].sum()),
         "empresarial": int(contrat.loc[c].get("Coletivo empresarial", 0)),
         "individual": int(contrat.loc[c].get("Individual ou familiar", 0)),
         "adesao": int(contrat.loc[c].get("Coletivo por adesão", 0)),
         "mais59": int(faixa.loc[c].get("59 anos ou mais", 0))} for c in comp]
mun = pd.read_parquet(TRATADOS / "dim_municipio.parquet")
pop_uf = mun.groupby("UF").POP_2026.sum()
u0 = mh[mh.COMPETENCIA == "202112"].groupby("UF", observed=True).ATIVOS.sum()
u1 = mh[mh.COMPETENCIA == "202609"]
nomes = dim.set_index("REG").NOME_EXIBICAO
ufs = {}
for uf, g in u1.groupby("UF", observed=True):
    uf = str(uf)
    if uf not in pop_uf.index:
        continue
    por_op = g.groupby("REG").ATIVOS.sum().sort_values(ascending=False)
    sh = por_op / por_op.sum()
    ufs[uf] = {"vidas": int(por_op.sum()), "pop": int(pop_uf[uf]), "cobertura": por_op.sum() / pop_uf[uf],
               "cresc": por_op.sum() / u0.get(uf, float("nan")) - 1, "hhi": float((sh ** 2).sum() * 10000),
               "lider": nomes.get(por_op.index[0], por_op.index[0]), "lider_pct": float(sh.iloc[0]),
               "top3_pct": float(sh.head(3).sum()), "operadoras": int((por_op >= 100).sum())}
# mapa: projeção equiretangular corrigida pela latitude média, caminhos SVG prontos
geo = json.load(open(BRUTOS / "ibge" / "malha_uf.json", encoding="utf-8"))
COD = {"11": "RO", "12": "AC", "13": "AM", "14": "RR", "15": "PA", "16": "AP", "17": "TO", "21": "MA", "22": "PI", "23": "CE",
       "24": "RN", "25": "PB", "26": "PE", "27": "AL", "28": "SE", "29": "BA", "31": "MG", "32": "ES", "33": "RJ", "35": "SP",
       "41": "PR", "42": "SC", "43": "RS", "50": "MS", "51": "MT", "52": "GO", "53": "DF"}
k = math.cos(math.radians(-15))
pts = [(x * k, -y) for f in geo["features"] for poly in (f["geometry"]["coordinates"] if f["geometry"]["type"] == "MultiPolygon" else [f["geometry"]["coordinates"]]) for ring in poly for x, y in ring]
minx, maxx = min(p[0] for p in pts), max(p[0] for p in pts)
miny, maxy = min(p[1] for p in pts), max(p[1] for p in pts)
LARG = 600
esc = LARG / (maxx - minx)
caminhos = {}
for f in geo["features"]:
    uf = COD[str(f["properties"]["codarea"])]
    polys = f["geometry"]["coordinates"] if f["geometry"]["type"] == "MultiPolygon" else [f["geometry"]["coordinates"]]
    d = []
    for poly in polys:
        for ring in poly:
            xy = [((x * k - minx) * esc, (-y - miny) * esc) for x, y in ring]
            d.append("M" + "L".join(f"{a:.1f},{b:.1f}" for a, b in xy) + "Z")
    caminhos[uf] = "".join(d)
clientes = {"evolucao": evol, "ufs": ufs, "mapa": {"largura": LARG, "altura": round((maxy - miny) * esc), "caminhos": caminhos},
            "brasil": {"vidas": int(u1.ATIVOS.sum()), "pop": int(pop_uf.sum()), "cobertura": u1.ATIVOS.sum() / pop_uf.sum()}}
gravar("clientes", limpa(clientes))

# ------------------------------------------------------------------ municípios
bm = pd.read_parquet(TRATADOS / "beneficiarios_municipio.parquet")
bm = bm[(bm.COMPETENCIA == "202609") & (bm.COBERTURA == "MH")].groupby("CD_MUNICIPIO")[["ATIVOS", "ATIVOS_59MAIS"]].sum()
m = mun.set_index("COD_MUNICIPIO").join(bm, how="left").fillna({"ATIVOS": 0, "ATIVOS_59MAIS": 0})
gravar("municipios", [[i, row.MUNICIPIO, row.UF, int(row.POP_2026), int(row.ATIVOS)] for i, row in m.iterrows()])

# ------------------------------------------------------------------ qualidade
q = rk[(rk.vidas_mh >= 20000) & rk.igr_12m.notna()]
pts = [[o.REG, o.NOME_EXIBICAO, o.MODALIDADE, o.PORTE, r(o.sinistralidade), r(o.igr_12m, 1), r(o.idss), int(o.vidas_mh)] for o in q.itertuples()]
qualidade = {"pontos": pts, "mediana_sinist": q.sinistralidade.median(), "mediana_igr": q.igr_12m.median(),
             "corr_sinist_igr": q[["sinistralidade", "igr_12m"]].corr("spearman").iloc[0, 1],
             "corr_idss_igr": q[["idss", "igr_12m"]].corr("spearman").iloc[0, 1]}
gravar("qualidade", limpa(qualidade))

# ------------------------------------------------------------------ SUS
uso = pd.read_parquet(TRATADOS / "fato_ressarc_uso.parquet")
cob = pd.read_parquet(TRATADOS / "fato_ressarc_cobranca.parquet")
g = uso.groupby(["GRUPO_LEITURA", "MOTIVO"])[["ATENDIMENTOS", "VL_ATENDIMENTO"]].sum().reset_index()
tot_a, tot_v = g.ATENDIMENTOS.sum(), g.VL_ATENDIMENTO.sum()
motivos = [{"grupo": x.GRUPO_LEITURA, "motivo": x.MOTIVO, "pct_atend": x.ATENDIMENTOS / tot_a, "pct_valor": x.VL_ATENDIMENTO / tot_v}
           for x in g.sort_values("ATENDIMENTOS", ascending=False).itertuples() if x.ATENDIMENTOS > 0]
grupos = {k: {"pct_atend": v.ATENDIMENTOS / tot_a, "pct_valor": v.VL_ATENDIMENTO / tot_v}
          for k, v in g.groupby("GRUPO_LEITURA")[["ATENDIMENTOS", "VL_ATENDIMENTO"]].sum().iterrows()}
# razão observado/esperado por modalidade, padronizada pela UF (atendimentos de 2024)
u = uso[uso.COMPETENCIA.str[:4] == "2024"].groupby(["REG", "UF_BENEFICIARIO", "GRUPO_LEITURA"]).ATENDIMENTOS.sum().unstack(fill_value=0)
u["total"] = u.sum(axis=1); u = u.reset_index().rename(columns={"UF_BENEFICIARIO": "UF"})
v = mh[mh.COMPETENCIA.isin(["202312", "202403", "202406", "202409", "202412"])]
v = v.groupby(["REG", "UF", "COMPETENCIA"], observed=True).ATIVOS.sum().groupby(["REG", "UF"], observed=True).mean().rename("vidas").reset_index()
v["UF"] = v.UF.astype(str)
x = v.merge(u, on=["REG", "UF"], how="left").fillna(0).merge(dim[["REG", "MODALIDADE", "SEGMENTO"]], on="REG")
x = x[(x.vidas > 0) & (x.SEGMENTO == "MH")]
tx = x.groupby("UF").total.sum() / x.groupby("UF").vidas.sum()
txf = x.groupby("UF")["Provável falha de acesso"].sum() / x.groupby("UF").vidas.sum()
x["esp"], x["espf"] = x.UF.map(tx) * x.vidas, x.UF.map(txf) * x.vidas
mods = {}
for mo, gg in x.groupby("MODALIDADE"):
    mods[mo] = {"por_mil": gg.total.sum() / gg.vidas.sum() * 1000, "razao": gg.total.sum() / gg.esp.sum(),
                "razao_falha": gg["Provável falha de acesso"].sum() / gg.espf.sum()}
cb = cob.groupby("SITUACAO_COBRANCA").VALOR_COBRADO.sum()
jud = cob[cob.SITUACAO_COBRANCA == "Suspenso na Justiça"].groupby("REG").VALOR_COBRADO.sum().sort_values(ascending=False)
sus = {"atendimentos": int(tot_a), "anos": "2019 a 2025", "grupos": grupos, "motivos": motivos, "modalidades": mods,
       "cobranca": {k: v / 1e6 for k, v in cb.items() if v > 0}, "cobrado_mi": cb.sum() / 1e6,
       "justica_mi": jud.sum() / 1e6, "justica_top5_pct": jud.head(5).sum() / jud.sum(),
       "justica_operadoras": int((jud > 0).sum()), "operadoras_cobradas": int(cob.groupby("REG").VALOR_COBRADO.sum().gt(0).sum()),
       "analise": cob.groupby("RESULTADO_ANALISE").ATENDIMENTOS.sum().to_dict()}
gravar("sus", limpa(sus))

# ------------------------------------------------------------------ operadoras (ficha) e quartis por porte
CODIGOS = ["sinistralidade", "indice_combinado", "margem_liquida", "indice_desp_adm", "receita_vida_mes", "custo_vida_mes",
           "cresc_vidas_12m", "pct_59mais", "igr_12m", "idss", "glosa_inicial", "tempo_pagamento_dias",
           "sus_falha_por_mil", "sus_pct_justica", "pct_judicial", "pct_ev_rede_propria"]
FORMAS = ["procedimento", "pacote", "rede_propria", "rede_indireta", "reembolso", "capitation", "orcamento_global"]
ind = ind.copy()
ind["flag_glosa"] = ind.flag_glosa.astype("boolean").fillna(True).astype(bool)
ind.loc[ind.flag_glosa, "glosa_inicial"] = float("nan")
quartis = {}
for porte, gp in rk.assign(flag_glosa=rk.flag_glosa.astype("boolean").fillna(True).astype(bool)).groupby("PORTE"):
    quartis[porte] = {}
    for c in CODIGOS:
        s = gp[c]
        if c == "glosa_inicial":
            s = s[~gp.flag_glosa]
        if c == "igr_12m":
            s = s[gp.vidas_mh >= 20000]
        s = s.dropna()
        quartis[porte][c] = [s.quantile(.25), s.quantile(.5), s.quantile(.75), int(len(s))] if len(s) >= 5 else None
tri = sorted(con[con.PERIODO >= "2023T1"].PERIODO.unique())
sin_tri = con[con.PERIODO.isin(tri)].pivot_table(index="REG", columns="PERIODO", values="sinistralidade_12m")
vid = mh[mh.COMPETENCIA >= "202303"].groupby(["REG", "COMPETENCIA"]).ATIVOS.sum().unstack()
uf_op = mh[mh.COMPETENCIA == "202606"].groupby(["REG", "UF"], observed=True).ATIVOS.sum()
ops = []
for o in ind[ind.ATIVA].itertuples():
    reg = o.REG
    ufo = uf_op.get(reg)
    ufo = {} if ufo is None else {str(k): int(v) for k, v in ufo.sort_values(ascending=False).items() if v >= 100}
    ops.append({
        "reg": reg, "nome": o.NOME_EXIBICAO, "razao": o.RAZAO_SOCIAL, "modalidade": o.MODALIDADE, "porte": o.PORTE,
        "uf_sede": o.UF_SEDE, "ranking": bool(o.RANKING_OK), "motivo": o.MOTIVO_FORA_RANKING,
        "vidas": None if pd.isna(o.vidas_mh) else int(o.vidas_mh),
        "ind": {c: r(getattr(o, c)) for c in CODIGOS},
        "rede": {f: r(getattr(o, f"pct_ev_{f}")) for f in FORMAS},
        "resultado": {"operacao": r(o.resultado_operacional / 1e6, 1), "aplicacoes": r(o.resultado_financeiro / 1e6, 1),
                      "lucro": r(o.resultado_liquido / 1e6, 1)},
        "sinist_tri": [r(sin_tri.loc[reg, t]) if reg in sin_tri.index and t in sin_tri.columns else None for t in tri],
        "vidas_tri": [int(vid.loc[reg, c]) if reg in vid.index and c in vid.columns and not pd.isna(vid.loc[reg, c]) else None for c in vid.columns],
        "ufs": ufo})
operadoras = {"trimestres": tri, "competencias": list(vid.columns), "quartis": quartis, "operadoras": ops}
gravar("operadoras", limpa(operadoras))
