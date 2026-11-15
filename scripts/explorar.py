"""Etapa 3: exploração em busca de achados. Só imprime; nada é gravado.
Uso: python -I scripts/explorar.py [mercado|serie|qualidade|sus|uf]
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from comum import *

pd.set_option("display.width", 230, "display.max_columns", 40, "display.max_rows", 200)
i = pd.read_parquet(TRATADOS / "ind_operadora.parquet")
i["flag_glosa"] = i.flag_glosa.astype("boolean").fillna(True).astype(bool)
r = i[i.RANKING_OK].copy()
alvo = sys.argv[1] if len(sys.argv) > 1 else "mercado"


def agg(g):
    w = g.vidas_mh
    return pd.Series({
        "n": len(g), "vidas_mi": w.sum() / 1e6,
        "sinist": g.sinist_num.sum() / g.sinist_den.sum(), "sinist_mediana": g.sinistralidade.median(),
        "combinado": g.comb_num.sum() / g.comb_den.sum(),
        "margem": g.resultado_liquido.sum() / g.contraprest_efet.sum(),
        "pct_com_prejuizo": (g.resultado_liquido < 0).mean(),
        "pct_prejuizo_operacional": (g.resultado_operacional < 0).mean(),
        "receita_vida_mes": g.contraprest_efet.sum() / g.vidas_mh_media_12m.sum() / 12,
        "custo_vida_mes": g.desp_assist.sum() / g.vidas_mh_media_12m.sum() / 12,
        "pct_59mais": (g.pct_59mais * w).sum() / w.sum(),
        "pct_individual": (g.pct_individual * w).sum() / w.sum(),
        "cresc_vidas_12m": g.vidas_mh.sum() / g.vidas_mh_ano_ant.sum() - 1,
        "igr": g.reclamacoes_12m.sum() / w.sum() * 1e5 / 12,
        "idss_mediana": g.idss.median(),
        "glosa_mediana": g.loc[~g.flag_glosa, "glosa_inicial"].median(),
        "sus_por_mil": g.sus_atend_2024.sum() / g.vidas_mh_media_2024.sum() * 1000,
        "sus_falha_por_mil": g.sus_atend_falha_2024.sum() / g.vidas_mh_media_2024.sum() * 1000,
        "judicial": g.jud_total.sum() / g.desp_assist.sum(),
        "rede_propria": (g.pct_ev_rede_propria * g.desp_assist).sum() / g.desp_assist.sum(),
    })


if alvo == "mercado":
    for por in ["MODALIDADE", "PORTE"]:
        print(f"\n=== por {por}")
        print(r.groupby(por).apply(agg).T.round(3).to_string())
    print("\n=== mercado (ranking)")
    print(agg(r).round(3).to_string())
    salvas = r[(r.resultado_operacional < 0) & (r.resultado_liquido > 0)]
    print(f"\nprejuízo na operação mas lucro no fim (salvas pelo financeiro): {len(salvas)} de {len(r)} "
          f"({len(salvas) / len(r):.1%}); prejuízo operacional: {(r.resultado_operacional < 0).sum()}")
    print("lucro líquido concentrado: top 3 =", f"{r.resultado_liquido.nlargest(3).sum() / r.resultado_liquido.clip(lower=0).sum():.1%}",
          "dos lucros positivos;", r.nlargest(3, "resultado_liquido")[["NOME_EXIBICAO", "resultado_liquido"]].to_dict("records"))

if alvo == "sus":
    uso = pd.read_parquet(TRATADOS / "fato_ressarc_uso.parquet")
    ben = pd.read_parquet(TRATADOS / "fato_beneficiarios.parquet")
    dim = pd.read_parquet(TRATADOS / "dim_operadora.parquet")[["REG", "MODALIDADE", "NOME_EXIBICAO"]]
    u = uso[uso.COMPETENCIA.str[:4] == "2024"].groupby(["REG", "UF_BENEFICIARIO", "GRUPO_LEITURA"]).ATENDIMENTOS.sum().unstack(fill_value=0)
    u["total"] = u.sum(axis=1); u = u.reset_index().rename(columns={"UF_BENEFICIARIO": "UF"})
    v = ben[(ben.COBERTURA == "MH") & ben.COMPETENCIA.isin(["202312", "202403", "202406", "202409", "202412"])]
    v = v.groupby(["REG", "UF", "COMPETENCIA"], observed=True).ATIVOS.sum().groupby(["REG", "UF"], observed=True).mean().rename("vidas").reset_index()
    v["UF"] = v.UF.astype(str)
    x = v.merge(u, on=["REG", "UF"], how="left").fillna(0).merge(dim, on="REG")
    x = x[x.vidas > 0]
    # taxa observada × esperada se a operadora tivesse a taxa média de cada UF onde atua (padronização indireta)
    taxa_uf = x.groupby("UF").apply(lambda g: g.total.sum() / g.vidas.sum())
    taxa_uf_f = x.groupby("UF").apply(lambda g: g["Provável falha de acesso"].sum() / g.vidas.sum())
    x["esperado"] = x.UF.map(taxa_uf) * x.vidas
    x["esperado_f"] = x.UF.map(taxa_uf_f) * x.vidas
    print("taxa por mil vidas por UF (2024):"); print((taxa_uf * 1000).round(1).sort_values().to_string())
    m = x.groupby("MODALIDADE")[["total", "esperado", "Provável falha de acesso", "esperado_f", "vidas"]].sum()
    m["obs_por_mil"] = m.total / m.vidas * 1000
    m["razao_obs_esp"] = m.total / m.esperado
    m["razao_falha_obs_esp"] = m["Provável falha de acesso"] / m.esperado_f
    print("\npor modalidade, controlando pela UF (razão > 1 = usa mais o SUS que o esperado para os estados onde atua):")
    print(m[["obs_por_mil", "razao_obs_esp", "razao_falha_obs_esp"]].round(2).to_string())
    o = x.groupby(["REG", "NOME_EXIBICAO", "MODALIDADE"])[["total", "esperado", "Provável falha de acesso", "esperado_f", "vidas"]].sum()
    o = o[o.vidas >= 100000]
    o["razao"] = o.total / o.esperado; o["razao_falha"] = o["Provável falha de acesso"] / o.esperado_f
    print("\nmaiores operadoras (>=100 mil vidas): razão observada/esperada")
    print(o.sort_values("razao", ascending=False)[["vidas", "razao", "razao_falha"]].round(2).head(12).to_string())
    print(o.sort_values("razao")[["vidas", "razao", "razao_falha"]].round(2).head(8).to_string())
    cob = pd.read_parquet(TRATADOS / "fato_ressarc_cobranca.parquet")
    c = cob.groupby("REG").apply(lambda g: pd.Series({"cobrado": g.VALOR_COBRADO.sum(),
            "justica": g.loc[g.SITUACAO_COBRANCA == "Suspenso na Justiça", "VALOR_COBRADO"].sum()})).join(dim.set_index("REG"))
    c = c.sort_values("justica", ascending=False)
    print(f"\nsuspenso na Justiça: R$ {c.justica.sum() / 1e6:,.0f} mi de R$ {c.cobrado.sum() / 1e6:,.0f} mi cobrados; "
          f"top 5 operadoras = {c.justica.head(5).sum() / c.justica.sum():.1%}; top 10 = {c.justica.head(10).sum() / c.justica.sum():.1%}")
    c["pct"] = c.justica / c.cobrado
    print(c.head(10)[["NOME_EXIBICAO", "MODALIDADE", "cobrado", "justica", "pct"]].round(2).to_string())
    print("operadoras com algo suspenso na Justiça:", (c.justica > 0).sum(), "de", (c.cobrado > 0).sum())

if alvo == "qualidade":
    q = r.copy()
    for k in ["sinistralidade", "igr_12m", "idss", "glosa_inicial", "sus_falha_por_mil", "pct_59mais", "pct_individual", "receita_vida_mes", "custo_vida_mes", "indice_combinado"]:
        q[k] = q[k].astype(float)
    print("correlação de Spearman (operadoras do ranking):")
    print(q[["sinistralidade", "indice_combinado", "igr_12m", "idss", "glosa_inicial", "sus_falha_por_mil", "pct_59mais", "pct_individual", "receita_vida_mes"]].corr("spearman").round(2).to_string())
    # quadrantes dentro do porte: sinistralidade × IGR, contra a mediana do porte
    q = q.dropna(subset=["sinistralidade", "igr_12m"])
    q = q[q.vidas_mh >= 20000]  # IGR de operadora pequena oscila demais
    q["sin_alta"] = q.sinistralidade > q.groupby("PORTE").sinistralidade.transform("median")
    q["igr_alto"] = q.igr_12m > q.groupby("PORTE").igr_12m.transform("median")
    print("\nquadrantes (médias e grandes; mediana do porte):")
    print(pd.crosstab(q.sin_alta, q.igr_alto, values=q.vidas_mh, aggfunc="sum", normalize=True).round(3))
    print(pd.crosstab(q.MODALIDADE, [q.sin_alta, q.igr_alto]).to_string())
    big = q[q.vidas_mh >= 500000].sort_values("igr_12m", ascending=False)
    print("\ngrandes (>=500 mil vidas): IGR e IDSS")
    print(big[["NOME_EXIBICAO", "MODALIDADE", "vidas_mh", "sinistralidade", "igr_12m", "idss", "glosa_inicial", "tempo_pagamento_dias", "sus_falha_por_mil"]].round(3).to_string(index=False))

if alvo == "uf":
    ben = pd.read_parquet(TRATADOS / "fato_beneficiarios.parquet")
    dim = pd.read_parquet(TRATADOS / "dim_operadora.parquet")[["REG", "NOME_EXIBICAO", "MODALIDADE"]]
    mun = pd.read_parquet(TRATADOS / "dim_municipio.parquet")
    b = ben[(ben.COBERTURA == "MH") & ben.COMPETENCIA.isin(["202112", "202609"])]
    b = b.groupby(["COMPETENCIA", "UF", "REG"], observed=True).ATIVOS.sum().reset_index()
    b["UF"] = b.UF.astype(str)
    a = b[b.COMPETENCIA == "202609"].merge(dim, on="REG")
    pop = mun.groupby("UF").POP_2026.sum()

    def conc(g):
        s = g.sort_values("ATIVOS", ascending=False); tot = s.ATIVOS.sum(); sh = s.ATIVOS / tot
        return pd.Series({"vidas_mil": tot / 1e3, "cobertura": tot / pop.get(g.name, float("nan")),
                          "top1": sh.iloc[0], "top3": sh.head(3).sum(), "hhi": (sh ** 2).sum() * 10000,
                          "lider": s.NOME_EXIBICAO.iloc[0][:28], "n_ops_90pct": int((sh.cumsum() < .9).sum() + 1)})
    t = a.groupby("UF").apply(conc).sort_values("hhi", ascending=False)
    print(t.round(3).to_string())
    o = b.pivot_table(index="UF", columns="COMPETENCIA", values="ATIVOS", aggfunc="sum")
    o["cresc"] = o["202609"] / o["202112"] - 1
    print("\ncrescimento de vidas dez/21 → set/26 por UF:"); print(o.cresc.sort_values().round(3).to_string())
    # grupo com 'HAPVIDA' no nome: participação por região
    a["hap"] = a.NOME_EXIBICAO.str.upper().str.contains("HAPVIDA")
    from etl_cadastro import REGIAO
    a["REGIAO"] = a.UF.map(REGIAO)
    print("\nparticipação das operadoras com 'HAPVIDA' no nome, por região:")
    print((a[a.hap].groupby("REGIAO").ATIVOS.sum() / a.groupby("REGIAO").ATIVOS.sum()).round(3).to_string())
    ce = a[a.UF == "CE"].sort_values("ATIVOS", ascending=False).head(8)
    ce["share"] = ce.ATIVOS / a[a.UF == "CE"].ATIVOS.sum()
    print("\nCeará, maiores carteiras:"); print(ce[["NOME_EXIBICAO", "MODALIDADE", "ATIVOS", "share"]].round(3).to_string(index=False))

if alvo == "serie":
    con = pd.read_parquet(TRATADOS / "fato_contabil.parquet").merge(
        pd.read_parquet(TRATADOS / "dim_operadora.parquet")[["REG", "SEGMENTO", "MODALIDADE"]], on="REG")
    m = con[(con.SEGMENTO == "MH") & con.PERIODO.str.endswith("T4")]
    s = m.groupby("ANO").apply(lambda g: pd.Series({
        "sinist": g.sinist_num_ytd.sum() / g.sinist_den_ytd.sum(),
        "combinado": g.comb_num_ytd.sum() / g.comb_den_ytd.sum(),
        "lucro_bi": g.resultado_liquido_ytd.sum() / 1e9,
        "operacional_bi": g.resultado_operacional_ytd.sum() / 1e9,
        "financeiro_bi": g.resultado_financeiro_ytd.sum() / 1e9,
        "pct_prejuizo": (g.resultado_liquido_ytd < 0).mean(),
        "pct_prej_oper": (g.resultado_operacional_ytd < 0).mean(),
        "judicial_bi": g.jud_total_ytd.sum() / 1e9,
        "n": g.resultado_liquido_ytd.notna().sum()}))
    print(s.round(3).to_string())
    print("\nsinistralidade 12m por modalidade (T2 de cada ano):")
    t = con[(con.SEGMENTO == "MH") & con.PERIODO.str.endswith("T2")].groupby(["ANO", "MODALIDADE"]).apply(
        lambda g: g.sinist_num_12m.sum() / g.sinist_den_12m.sum()).unstack()
    print(t.round(3).to_string())
    ben = pd.read_parquet(TRATADOS / "fato_beneficiarios.parquet")
    b = ben[(ben.COBERTURA == "MH") & ben.COMPETENCIA.str.endswith("12") | (ben.COMPETENCIA == "202609")]
    b = b[b.COBERTURA == "MH"]
    e = b.groupby(["COMPETENCIA"]).apply(lambda g: pd.Series({
        "vidas_mi": g.ATIVOS.sum() / 1e6,
        "pct_59mais": g.loc[g.FAIXA_REAJ == "59 anos ou mais", "ATIVOS"].sum() / g.ATIVOS.sum(),
        "pct_individual": g.loc[g.CONTRATACAO == "Individual ou familiar", "ATIVOS"].sum() / g.ATIVOS.sum(),
        "pct_empresarial": g.loc[g.CONTRATACAO == "Coletivo empresarial", "ATIVOS"].sum() / g.ATIVOS.sum(),
        "pct_0a18": g.loc[g.FAIXA_REAJ == "0 a 18 anos", "ATIVOS"].sum() / g.ATIVOS.sum()}))
    print("\ncarteira médico-hospitalar:"); print(e.round(4).to_string())
    f = b[b.COMPETENCIA.isin(["202112", "202609"])].groupby(["COMPETENCIA", "CONTRATACAO", "FAIXA_REAJ"], observed=True).ATIVOS.sum().unstack(0)
    f["var"] = f["202609"] - f["202112"]
    print("\nvariação de vidas dez/21 → set/26 por contratação:"); print(f.groupby(level=0).sum().round(0).to_string())
    print("\n59+ por contratação:"); print(f.xs("59 anos ou mais", level=1).round(0).to_string())
