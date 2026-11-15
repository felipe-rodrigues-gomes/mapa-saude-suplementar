"""Demonstrações contábeis (DIOPS) -> fato_contabil.parquet

Grão: operadora × ano × trimestre.
Para cada conta, três versões:
  _ytd  acumulado no ano (saldo final do arquivo do trimestre)
  _tri  trimestre isolado (saldo final - saldo inicial do mesmo arquivo)
  _12m  12 meses móveis = ytd(T, A) + ytd(4T, A-1) - ytd(T, A-1)
Contas:
  31  receitas com operações de assistência à saúde | 32 (-) tributos diretos
  311 contraprestações líquidas | 312 variação das provisões técnicas
  3117 (-) contraprestações de corresponsabilidade cedida (CCT)
  41  eventos indenizáveis líquidos (despesa assistencial)
  46  despesas administrativas | 43 despesas de comercialização

Sinistralidade (a variante que reproduz a ANS, erro de 0,04 a 0,38 p.p. em 2024–2026):
  (41 + |3117|) / (31 + 32 + |3117|)
  31 + 32 = contraprestações efetivas (receita de assistência líquida de tributos diretos).
"""
import re, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from comum import *

CONTAS = {"31": "receita_assist", "32": "tributos_diretos", "311": "contraprest_liq",
          "312": "var_prov_tec", "3117": "corresp_cedida", "41": "desp_assist",
          "46": "desp_adm", "43": "desp_comerc",
          # resultado (nota metodológica do Painel Econômico-Financeiro da ANS)
          "3": "receitas_total", "4": "despesas_total", "61": "impostos_particip",
          "33": "outras_rec_oper", "34": "trib_outras_ativ", "37": "receitas_adm",
          "44": "outras_desp_oper", "35": "receitas_fin", "45": "despesas_fin",
          "36": "receitas_patrim", "47": "despesas_patrim",
          # eventos por forma de pagamento à rede
          "411": "ev_conhecidos", "4111": "ev_procedimento", "4112": "ev_capitation",
          "4113": "ev_orcamento_global", "4114": "ev_pacote", "4115": "ev_rede_propria",
          "4116": "ev_rede_indireta", "4117": "ev_reembolso", "4118": "ev_sus", "4119": "ev_outras_formas"}
# contas de último nível somadas por padrão (despesas judiciais, RN 435/2018, desde 2019)
PADROES = {"jud_cobertos": r"^411\d{5}7$",       # eventos com cobertura contratual, por decisão judicial
           "jud_nao_cobertos": r"^4413\d9\d4$"}  # eventos sem cobertura contratual, por decisão judicial


def ler_trimestre(z: Path) -> pd.DataFrame:
    df = ler_zip_csv(z)
    pad = []
    for nome, rx in PADROES.items():
        p = df[df.CD_CONTA_CONTABIL.str.match(rx)].copy()
        p["CD_CONTA_CONTABIL"] = nome
        pad.append(p)
    df = pd.concat([df[df.CD_CONTA_CONTABIL.isin(CONTAS)]] + pad).copy()
    df["REG"] = reg(df.REG_ANS)
    df["fim"] = num_br(df.VL_SALDO_FINAL)
    # 1T a 3T de 2021 não trazem saldo inicial: o trimestre isolado sai da diferença dos acumulados
    df["ini"] = num_br(df.VL_SALDO_INICIAL) if "VL_SALDO_INICIAL" in df else float("nan")
    m = re.match(r"(\d)T(\d{4})", z.stem)
    df["TRI"], df["ANO"] = int(m.group(1)), int(m.group(2))
    # mesma conta repetida no arquivo (raro): soma
    return df.groupby(["REG", "ANO", "TRI", "CD_CONTA_CONTABIL"], as_index=False)[["fim", "ini"]].sum(min_count=1)


def main():
    arquivos = sorted((BRUTOS / "contabeis").glob("*T20*.zip"))
    d = pd.concat([ler_trimestre(z) for z in arquivos])
    d["conta"] = d.CD_CONTA_CONTABIL.map(CONTAS).fillna(d.CD_CONTA_CONTABIL)
    d = d.sort_values(["REG", "CD_CONTA_CONTABIL", "ANO", "TRI"])
    anterior = d.groupby(["REG", "CD_CONTA_CONTABIL", "ANO"]).fim.shift(1)
    dif_ytd = (d.fim - anterior).where(d.TRI > 1, d.fim)
    dif_ytd = dif_ytd.where(~((d.TRI > 1) & anterior.isna()))   # sem o trimestre anterior, não inventa
    d["tri_isol"] = (d.fim - d.ini).fillna(dif_ytd)
    ytd = d.pivot_table(index=["REG", "ANO", "TRI"], columns="conta", values="fim", aggfunc="sum")
    tri = d.pivot_table(index=["REG", "ANO", "TRI"], columns="conta", values="tri_isol", aggfunc="sum")
    ytd.columns = [f"{c}_ytd" for c in ytd.columns]
    tri.columns = [f"{c}_tri" for c in tri.columns]
    f = ytd.join(tri).reset_index()

    # 12 meses móveis
    base = f[["REG", "ANO", "TRI"] + [c for c in f.columns if c.endswith("_ytd")]]
    ant = base.copy(); ant["ANO"] += 1                       # mesmo trimestre do ano anterior
    ano_ant = base[base.TRI == 4].drop(columns="TRI").copy(); ano_ant["ANO"] += 1   # ano anterior fechado
    m = base.merge(ant, on=["REG", "ANO", "TRI"], how="left", suffixes=("", "_aa")) \
            .merge(ano_ant, on=["REG", "ANO"], how="left", suffixes=("", "_fa"))
    for conta in list(CONTAS.values()) + list(PADROES):
        c = f"{conta}_ytd"
        if c not in m: continue
        ltm = m[c] + m[f"{c}_fa"] - m[f"{c}_aa"]
        # 4º trimestre: o próprio ano fechado, não precisa do ano anterior
        f[f"{conta}_12m"] = ltm.where(m.TRI != 4, m[c]).values
    # presença do arquivo no trimestre (sem a conta, ytd = NaN mas a operadora entregou)
    f["PERIODO"] = f.ANO.astype(str) + "T" + f.TRI.astype(str)
    f["DATA_FIM"] = pd.to_datetime(dict(year=f.ANO, month=f.TRI * 3, day=1)) + pd.offsets.MonthEnd(0)

    # contraprestações efetivas e sinistralidade no critério da ANS
    for v in ("ytd", "tri", "12m"):
        cct = f[f"corresp_cedida_{v}"].fillna(0).abs()
        f[f"contraprest_efet_{v}"] = f[f"receita_assist_{v}"] + f[f"tributos_diretos_{v}"].fillna(0)
        f[f"sinist_num_{v}"] = f[f"desp_assist_{v}"] + cct          # numerador (para somar no Power BI)
        f[f"sinist_den_{v}"] = f[f"contraprest_efet_{v}"] + cct     # denominador
        den = f[f"sinist_den_{v}"]
        f[f"sinistralidade_{v}"] = (f[f"sinist_num_{v}"] / den).where(den > 0)

        # resultados (contas de redutoras, como 32 e 34, já vêm negativas)
        z = lambda c: f[f"{c}_{v}"].fillna(0)
        f[f"resultado_liquido_{v}"] = z("receitas_total") - z("despesas_total") - z("impostos_particip")
        f[f"resultado_operacional_{v}"] = (z("receita_assist") + z("tributos_diretos") + z("outras_rec_oper")
                                           + z("trib_outras_ativ") + z("receitas_adm")
                                           - z("desp_assist") - z("desp_adm") - z("desp_comerc") - z("outras_desp_oper"))
        f[f"resultado_financeiro_{v}"] = z("receitas_fin") - z("despesas_fin")
        f[f"resultado_patrimonial_{v}"] = z("receitas_patrim") - z("despesas_patrim")
        for c in ("resultado_liquido", "resultado_operacional", "resultado_financeiro", "resultado_patrimonial"):
            f.loc[f[f"receitas_total_{v}"].isna(), f"{c}_{v}"] = float("nan")

        # índices da ANS: numerador e denominador separados para o Power BI somar antes de dividir
        f[f"comb_num_{v}"] = f[f"sinist_num_{v}"] + z("desp_adm") + z("desp_comerc")
        f[f"comb_den_{v}"] = f[f"sinist_den_{v}"] + z("receitas_adm")
        f[f"indice_combinado_{v}"] = (f[f"comb_num_{v}"] / f[f"comb_den_{v}"]).where(f[f"comb_den_{v}"] > 0)
        f[f"indice_desp_adm_{v}"] = (z("desp_adm") / f[f"comb_den_{v}"]).where(f[f"comb_den_{v}"] > 0)
        f[f"indice_desp_comerc_{v}"] = (z("desp_comerc") / den).where(den > 0)
        f[f"margem_liquida_{v}"] = (f[f"resultado_liquido_{v}"] / f[f"contraprest_efet_{v}"]).where(f[f"contraprest_efet_{v}"] > 0)
        f[f"jud_total_{v}"] = z("jud_cobertos") + z("jud_nao_cobertos")
        f[f"pct_judicial_{v}"] = (f[f"jud_total_{v}"] / f[f"desp_assist_{v}"]).where(f[f"desp_assist_{v}"] > 0)

    f = f.sort_values(["REG", "ANO", "TRI"]).reset_index(drop=True)
    f.to_parquet(TRATADOS / "fato_contabil.parquet", index=False)
    print(f"fato_contabil: {len(f):,} linhas, {f.REG.nunique()} operadoras, {f.PERIODO.min()} a {f.PERIODO.max()}")
    print("12m preenchido por período:", f.groupby("PERIODO").sinistralidade_12m.count().to_dict())


if __name__ == "__main__":
    main()
