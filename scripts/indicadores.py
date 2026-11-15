"""Etapa 3: indicadores por operadora (foto mais recente) -> ind_operadora.parquet

Períodos (alinhados à última informação completa de cada fonte):
  contábil ........ 12 meses até 2026T2 (jul/25–jun/26)
  carteira ........ jun/2026 (e média dos fins de trimestre jun/25–jun/26 para valores por vida)
  reclamações ..... IGR ponderado jul/25–jun/26
  IDSS ............ IDSS 2025 (ano-base 2024)
  glosa ........... 2º semestre de 2025
  ressarcimento ... atendimentos de 2024 (2025 ainda incompleto)

Regra de ranking (RANKING_OK): médico-hospitalar, ativa, ≥ 1.000 vidas médicas, receita 12m > 0 e
sinistralidade entre 30% e 150%. Quem fica de fora aparece na ficha com o motivo, sem posição.
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from comum import *

PER = "2026T2"
COMPS_12M = ["202506", "202509", "202512", "202603", "202606"]
COMP_ATUAL, COMP_ANO_ANT = "202606", "202506"
COMPS_2024 = ["202312", "202403", "202406", "202409", "202412"]

dim = pd.read_parquet(TRATADOS / "dim_operadora.parquet")
con = pd.read_parquet(TRATADOS / "fato_contabil.parquet")
ben = pd.read_parquet(TRATADOS / "fato_beneficiarios.parquet")
igr = pd.read_parquet(TRATADOS / "fato_igr.parquet")
idss = pd.read_parquet(TRATADOS / "fato_idss.parquet")
glo = pd.read_parquet(TRATADOS / "fato_glosa.parquet")
uso = pd.read_parquet(TRATADOS / "fato_ressarc_uso.parquet")
cob = pd.read_parquet(TRATADOS / "fato_ressarc_cobranca.parquet")

# ---------- contábil
c = con[con.PERIODO == PER].set_index("REG")
ind = pd.DataFrame(index=c.index)
for col in ["sinistralidade_12m", "indice_combinado_12m", "indice_desp_adm_12m", "indice_desp_comerc_12m",
            "margem_liquida_12m", "pct_judicial_12m", "contraprest_efet_12m", "desp_assist_12m",
            "resultado_liquido_12m", "resultado_operacional_12m", "resultado_financeiro_12m",
            "sinist_num_12m", "sinist_den_12m", "comb_num_12m", "comb_den_12m", "jud_total_12m"]:
    ind[col.replace("_12m", "")] = c[col]
ev = c.ev_conhecidos_12m.where(c.ev_conhecidos_12m > 0)
for k in ["procedimento", "pacote", "rede_propria", "rede_indireta", "capitation", "orcamento_global", "reembolso"]:
    ind[f"pct_ev_{k}"] = c[f"ev_{k}_12m"].fillna(0) / ev   # conta ausente = forma não usada (0%), desde que haja eventos
# sinistralidade 12m um ano antes (tendência)
ind["sinistralidade_ano_ant"] = con[con.PERIODO == "2025T2"].set_index("REG").sinistralidade_12m

# ---------- carteira
mh = ben[ben.COBERTURA == "MH"]
v = mh.groupby(["REG", "COMPETENCIA"]).ATIVOS.sum().unstack()
ind = ind.join(pd.DataFrame({
    "vidas_mh": v.get(COMP_ATUAL),
    "vidas_mh_ano_ant": v.get(COMP_ANO_ANT),
    "vidas_mh_media_12m": v[COMPS_12M].mean(axis=1, skipna=False),
    "vidas_mh_media_2024": v[COMPS_2024].mean(axis=1, skipna=False),
}), how="outer")
ind["cresc_vidas_12m"] = ind.vidas_mh / ind.vidas_mh_ano_ant - 1
atual = mh[mh.COMPETENCIA == COMP_ATUAL]
tot = atual.groupby("REG").ATIVOS.sum()
ind["pct_59mais"] = atual[atual.FAIXA_REAJ == "59 anos ou mais"].groupby("REG").ATIVOS.sum() / tot
ind["pct_individual"] = atual[atual.CONTRATACAO == "Individual ou familiar"].groupby("REG").ATIVOS.sum() / tot
ind["pct_empresarial"] = atual[atual.CONTRATACAO == "Coletivo empresarial"].groupby("REG").ATIVOS.sum() / tot
ind["pct_adesao"] = atual[atual.CONTRATACAO == "Coletivo por adesão"].groupby("REG").ATIVOS.sum() / tot
ind["receita_vida_mes"] = ind.contraprest_efet / ind.vidas_mh_media_12m / 12
ind["custo_vida_mes"] = ind.desp_assist / ind.vidas_mh_media_12m / 12

# ---------- reclamações (IGR ponderado no período)
i = igr[(igr.COBERTURA == "MH") & igr.COMPETENCIA.between("202507", "202606")]
g = i.groupby("REG")[["QTD_RECLAMACOES", "QTD_BENEFICIARIOS"]].sum()
ind["igr_12m"] = g.QTD_RECLAMACOES / g.QTD_BENEFICIARIOS * 1e5
ind["reclamacoes_12m"] = g.QTD_RECLAMACOES

# ---------- IDSS
s = idss[idss.ANO_IDSS == 2025].set_index("REG")
for k in ["IDSS", "IDQS", "IDGA", "IDSM", "IDGR"]:
    ind[k.lower()] = s[k]

# ---------- glosa
gl = glo[glo.SEMESTRE == "2025S2"].set_index("REG")
ind["glosa_inicial"] = gl.GLOSA_INICIAL_PCT / 100
ind["glosa_final"] = gl.GLOSA_FINAL_PCT / 100
ind["tempo_pagamento_dias"] = gl.TEMPO_PAGAMENTO_DIAS
ind["flag_glosa"] = gl.FLAG_GLOSA_EXTREMA | gl.FLAG_GLOSA_FINAL_MAIOR

# ---------- ressarcimento (atendimentos de 2024)
u = uso[uso.COMPETENCIA.str[:4] == "2024"]
ug = u.groupby(["REG", "GRUPO_LEITURA"])[["ATENDIMENTOS", "VL_ATENDIMENTO"]].sum().unstack(fill_value=0)
ind["sus_atend_2024"] = ug["ATENDIMENTOS"].sum(axis=1)
ind["sus_atend_falha_2024"] = ug["ATENDIMENTOS"].get("Provável falha de acesso")
ind["sus_valor_2024"] = ug["VL_ATENDIMENTO"].sum(axis=1)
ind["sus_por_mil"] = ind.sus_atend_2024.fillna(0) / ind.vidas_mh_media_2024 * 1000
ind["sus_falha_por_mil"] = ind.sus_atend_falha_2024.fillna(0) / ind.vidas_mh_media_2024 * 1000
# cobrança acumulada 2019–2025: quanto do cobrado está suspenso na Justiça / pago
cb = cob.groupby(["REG", "SITUACAO_COBRANCA"]).VALOR_COBRADO.sum().unstack(fill_value=0)
ind["sus_cobrado"] = cb.sum(axis=1)
ind["sus_pct_justica"] = cb.get("Suspenso na Justiça", 0) / ind.sus_cobrado.where(ind.sus_cobrado > 0)
ind["sus_pct_pago"] = (cb.get("Pago", 0) + cb.get("Parcelado", 0)) / ind.sus_cobrado.where(ind.sus_cobrado > 0)

# ---------- cadastro e regra de ranking
ind.index.name = "REG"
ind = dim.set_index("REG")[["NOME_EXIBICAO", "RAZAO_SOCIAL", "MODALIDADE", "SEGMENTO", "PORTE", "ATIVA",
                            "UF_SEDE", "REGIAO_SEDE", "UF_PRINCIPAL", "PCT_UF_PRINCIPAL"]].join(ind, how="inner")
ind = ind[ind.SEGMENTO == "MH"]
motivo = pd.Series("", index=ind.index)
motivo[~ind.ATIVA] = "Operadora cancelada"
motivo[(motivo == "") & ~(ind.vidas_mh >= 1000)] = "Menos de 1.000 vidas médicas"
tem_tri = ind.index.isin(c.index)
tem_anual = ind.index.isin(con[con.PERIODO == "2025T4"].REG)
motivo[(motivo == "") & ~tem_tri & ~tem_anual] = "Não enviou demonstração contábil recente à ANS"
motivo[(motivo == "") & ~tem_tri & tem_anual] = "Só há balanço anual (ficha mostra 2025)"
motivo[(motivo == "") & ind.sinist_den.isna()] = "Histórico contábil incompleto nos últimos 12 meses"
motivo[(motivo == "") & ~(ind.sinist_den > 0)] = "Sem receita de plano nos últimos 12 meses"
motivo[(motivo == "") & ~ind.sinistralidade.between(0.3, 1.5)] = "Sinistralidade atípica (fora de 30%–150%)"
ind["MOTIVO_FORA_RANKING"] = motivo.replace("", None)
ind["RANKING_OK"] = ind.MOTIVO_FORA_RANKING.isna()
ind = ind.reset_index()
ind.to_parquet(TRATADOS / "ind_operadora.parquet", index=False)

print(f"ind_operadora: {len(ind)} operadoras médico-hospitalares | no ranking: {ind.RANKING_OK.sum()}")
print(ind.MOTIVO_FORA_RANKING.value_counts().to_string())
r = ind[ind.RANKING_OK]
print(f"ranking cobre {r.vidas_mh.sum() / ind.vidas_mh.sum():.1%} das vidas e "
      f"{r.contraprest_efet.sum() / ind.contraprest_efet.clip(lower=0).sum():.1%} da receita")
