"""Validações da etapa 2. Imprime um relatório; nada é alterado."""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from comum import *

pd.set_option("display.width", 200, "display.max_columns", 30)
dim = pd.read_parquet(TRATADOS / "dim_operadora.parquet")
con = pd.read_parquet(TRATADOS / "fato_contabil.parquet").merge(dim[["REG", "SEGMENTO", "MODALIDADE", "NOME_EXIBICAO"]], on="REG", how="left")
ben = pd.read_parquet(TRATADOS / "fato_beneficiarios.parquet")
igr = pd.read_parquet(TRATADOS / "fato_igr.parquet")
idss = pd.read_parquet(TRATADOS / "fato_idss.parquet")
glo = pd.read_parquet(TRATADOS / "fato_glosa.parquet")
mh = con[con.SEGMENTO == "MH"]

print("## 1. Sinistralidade médico-hospitalar × ANS (acumulado do período)")
ans = {"2024T4": 83.8, "2025T2": 81.1, "2025T4": 81.7, "2026T2": 81.9}
g = mh.groupby("PERIODO")[["sinist_num_ytd", "sinist_den_ytd"]].sum()
for p, a in ans.items():
    s = g.loc[p, "sinist_num_ytd"] / g.loc[p, "sinist_den_ytd"] * 100
    print(f"  {p}: calculado {s:.2f}% | ANS {a}% | diferença {s - a:+.2f} p.p.")

print("\n## 1b. Resultado e índices × Painel Econômico-Financeiro da ANS (médico-hospitalares, acumulado)")
ref = {"2024T4": {"resultado_liquido_ytd": 10.2}, "2025T4": {"resultado_liquido_ytd": 23.4, "resultado_operacional_ytd": 9.8},
       "2026T2": {"resultado_liquido_ytd": 10.89}}
for p, itens in ref.items():
    x = mh[mh.PERIODO == p]
    for c, a in itens.items():
        print(f"  {p} {c}: calculado R$ {x[c].sum() / 1e9:.2f} bi | ANS R$ {a} bi")
    print(f"  {p} operadoras com lucro: {(x.resultado_liquido_ytd > 0).mean():.1%} | índice combinado {x.comb_num_ytd.sum() / x.comb_den_ytd.sum():.1%}")
x = mh[mh.PERIODO == "2026T2"]
print(f"  despesas judiciais 12m até 2026T2: R$ {x.jud_total_12m.sum() / 1e9:.2f} bi ({x.jud_total_12m.sum() / x.desp_assist_12m.sum():.2%} dos eventos) | ANS ~R$ 5,2 bi, ~1,8%")

print("\n## 2. Sinistralidade 12 meses por operadora — valores suspeitos (2026T2, médico-hospitalar)")
u = mh[mh.PERIODO == "2026T2"].copy()
print(f"  operadoras: {len(u)} | sem 12m: {u.sinistralidade_12m.isna().sum()} | denominador <= 0: {(u.sinist_den_12m <= 0).sum()}")
print(f"  < 30%: {(u.sinistralidade_12m < .3).sum()} | > 150%: {(u.sinistralidade_12m > 1.5).sum()}")
print(u.sort_values("sinistralidade_12m").dropna(subset=["sinistralidade_12m"])
      .iloc[list(range(4)) + list(range(-4, 0))][["REG", "NOME_EXIBICAO", "MODALIDADE", "sinist_den_12m", "sinistralidade_12m"]].to_string(index=False))

print("\n## 3. Beneficiários por competência (milhões)")
t = ben.groupby(["COMPETENCIA", "COBERTURA"], observed=True).ATIVOS.sum().unstack() / 1e6
print(t.round(2).to_string())

print("\n## 4. Beneficiários × denominador do IGR (mesma competência, por operadora, médico-hospitalar)")
ult = ben.COMPETENCIA.max()
b = ben[(ben.COMPETENCIA == ult) & (ben.COBERTURA == "MH")].groupby("REG").ATIVOS.sum()
i = pd.read_csv(BRUTOS / "igr" / "igr_2023.csv", sep=";", dtype=str)
i = i[(i.COBERTURA == "Assistência médica") & (i.COMPETENCIA_BENEFICIARIO.str.replace("-", "") == ult)]
i = i.assign(REG=reg(i.REGISTRO_OPERADORA), q=pd.to_numeric(i.QTD_BENEFICIARIOS)).groupby("REG").q.max()
m = pd.concat([b.rename("nosso"), i.rename("igr")], axis=1).dropna()
m["dif_pct"] = (m.nosso / m.igr - 1) * 100
print(f"  competência {ult}: {len(m)} operadoras | total nosso {m.nosso.sum()/1e6:.2f} mi × IGR {m.igr.sum()/1e6:.2f} mi")
print(f"  |dif| < 1%: {(m.dif_pct.abs() < 1).mean():.1%} | |dif| > 5%: {(m.dif_pct.abs() > 5).sum()}")

print("\n## 5. Cobertura dos indicadores nas operadoras médico-hospitalares com contábil em 2026T2")
base = set(u.REG)
cob = {
    "beneficiários (último mês)": set(b.index),
    "IGR (último mês)": set(igr[(igr.COBERTURA == "MH") & (igr.COMPETENCIA == igr.COMPETENCIA.max())].REG),
    "IDSS 2025": set(idss[idss.ANO_IDSS == 2025].REG),
    "glosa 2025S2": set(glo[glo.SEMESTRE == "2025S2"].REG),
    "glosa 2025S2 sem flag": set(glo[(glo.SEMESTRE == "2025S2") & ~glo.FLAG_GLOSA_EXTREMA].REG),
}
rec = u.set_index("REG").sinist_den_12m
for k, s in cob.items():
    tem = base & s
    print(f"  {k}: {len(tem)}/{len(base)} operadoras ({rec[list(tem)].sum() / rec.sum():.1%} da receita)")

print("\n## 6. Receita e custo por beneficiário/mês (12m até 2026T2, vidas médico-hospitalares médias)")
comps = ["202506", "202509", "202512", "202603", "202606"]
vid = ben[ben.COMPETENCIA.isin(comps) & (ben.COBERTURA == "MH")].groupby(["REG", "COMPETENCIA"]).ATIVOS.sum().unstack()
vid = vid[vid.notna().all(axis=1)].mean(axis=1).rename("vidas_media")
x = u.set_index("REG").join(vid, how="inner")
x = x[x.vidas_media > 0]
x["receita_vida_mes"] = x.contraprest_efet_12m / x.vidas_media / 12
x["custo_vida_mes"] = x.desp_assist_12m / x.vidas_media / 12
print(f"  mercado: receita R$ {x.contraprest_efet_12m.sum() / x.vidas_media.sum() / 12:,.0f} | custo R$ {x.desp_assist_12m.sum() / x.vidas_media.sum() / 12:,.0f} por vida/mês")
print("  distribuição receita/vida/mês:", x.receita_vida_mes.describe(percentiles=[.01, .1, .5, .9, .99]).round(0).to_dict())
print("  por modalidade (mediana):", x.groupby("MODALIDADE").receita_vida_mes.median().round(0).to_dict())
