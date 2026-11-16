"""Um arquivo por estado (site/dados/uf/XX.json) para a tela de reclamações e o comparador.

Concorrentes = operadoras médico-hospitalares com >= 1% dos clientes do estado OU >= 5 mil clientes nele,
de qualquer porte. Ranking de reclamações só com >= 20 mil clientes no estado (abaixo disso o índice oscila).
Indicadores do estado: clientes, participação, crescimento 12m, 59+, reclamações (NIP jul/25–jun/26) por mil
clientes por ano, resolução na mediação (fórmula da ANS), temas, ida ao SUS por possível falha de acesso (2024),
hospitais na rede e preço de tabela (quando fato_rede / fato_preco existirem).
Indicadores da operadora inteira (contábeis e de qualidade nacionais): vêm de ind_operadora.
"""
import json, math, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from comum import *

SAIDA = RAIZ / "site" / "dados" / "uf"
SAIDA.mkdir(parents=True, exist_ok=True)
MIN_RANKING = 20000


def r(x, n=4):
    if x is None:
        return None
    try:
        if isinstance(x, float) and (math.isnan(x) or math.isinf(x)):
            return None
        return round(float(x), n)
    except (TypeError, ValueError):
        return None


dim = pd.read_parquet(TRATADOS / "dim_operadora.parquet")
ind = pd.read_parquet(TRATADOS / "ind_operadora.parquet").set_index("REG")
mhreg = set(dim[dim.SEGMENTO == "MH"].REG)
nomes = dim.set_index("REG")
ben = pd.read_parquet(TRATADOS / "fato_beneficiarios.parquet")
ben = ben[(ben.COBERTURA == "MH") & ben.REG.isin(mhreg)]
ben["UF"] = ben.UF.astype(str)
mun = pd.read_parquet(TRATADOS / "dim_municipio.parquet")
pop = mun.groupby("UF").POP_2026.sum()
nip = pd.read_parquet(TRATADOS / "fato_nip.parquet")
uso = pd.read_parquet(TRATADOS / "fato_ressarc_uso.parquet")
rede = pd.read_parquet(TRATADOS / "fato_rede.parquet") if (TRATADOS / "fato_rede.parquet").exists() else None
preco = pd.read_parquet(TRATADOS / "fato_preco.parquet") if (TRATADOS / "fato_preco.parquet").exists() else None
print("rede:", rede is not None, "| preço:", preco is not None)

# clientes por operadora × UF em jun/2026, jun/2025 e média dos 4 trimestres (denominador das reclamações)
v = ben.groupby(["REG", "UF", "COMPETENCIA"], observed=True).ATIVOS.sum().unstack()
v_med = v[["202509", "202512", "202603", "202606"]].mean(axis=1)
v59 = ben[(ben.COMPETENCIA == "202606") & (ben.FAIXA_REAJ == "59 anos ou mais")].groupby(["REG", "UF"], observed=True).ATIVOS.sum()
vind = ben[(ben.COMPETENCIA == "202606") & (ben.CONTRATACAO == "Individual ou familiar")].groupby(["REG", "UF"], observed=True).ATIVOS.sum()
# reclamações
nip_ou = nip.groupby(["REG", "UF"]).DEMANDAS.sum()
nip_cls = nip.pivot_table(index=["REG", "UF"], columns="CLASSE", values="DEMANDAS", aggfunc="sum").fillna(0)
nip_tema = nip.groupby(["REG", "UF", "TEMA"]).DEMANDAS.sum()
# SUS: atendimentos de 2024 com provável falha de acesso, por UF do beneficiário
sus = uso[(uso.COMPETENCIA.str[:4] == "2024")]
sus_f = sus[sus.GRUPO_LEITURA == "Provável falha de acesso"].groupby(["REG", "UF_BENEFICIARIO"]).ATENDIMENTOS.sum()
v24 = ben[ben.COMPETENCIA.isin(["202312", "202403", "202406", "202409", "202412"])].groupby(["REG", "UF", "COMPETENCIA"], observed=True).ATIVOS.sum().groupby(["REG", "UF"], observed=True).mean()

NAC = ["sinistralidade", "margem_liquida", "indice_combinado", "idss", "glosa_inicial", "tempo_pagamento_dias", "sus_pct_justica", "igr_12m", "receita_vida_mes"]
ind_flag = ind.flag_glosa.astype("boolean").fillna(True).astype(bool)

resumo = {}
for uf in sorted(pop.index):
    if uf not in v.index.get_level_values(1):
        continue
    vu = v.xs(uf, level="UF")
    atual = vu["202606"].dropna()
    total = atual.sum()
    share = atual / total
    sel = atual[(share >= 0.01) | (atual >= 5000)].sort_values(ascending=False)
    ops = []
    for reg_, vid in sel.items():
        k = (reg_, uf)
        n_rec = nip_ou.get(k, 0)
        den = v_med.get(k, float("nan"))
        cls = nip_cls.loc[k] if k in nip_cls.index else None
        resol = (cls["resolvida"] / (cls["resolvida"] + cls["processo"])) if cls is not None and (cls["resolvida"] + cls["processo"]) >= 20 else None
        temas = nip_tema.get(reg_, pd.Series(dtype=float))
        temas = temas.xs(uf, level=0) if hasattr(temas, "index") and isinstance(temas.index, pd.MultiIndex) and uf in temas.index.get_level_values(0) else pd.Series(dtype=float)
        top = [[t, int(q)] for t, q in temas.sort_values(ascending=False).head(3).items()] if len(temas) else []
        o = {"reg": reg_, "nome": nomes.NOME_EXIBICAO.get(reg_, reg_), "modalidade": nomes.MODALIDADE.get(reg_),
             "porte": nomes.PORTE.get(reg_), "vidas": int(vid), "participacao": r(vid / total),
             "cresc_12m": r(vid / vu["202506"].get(reg_, float("nan")) - 1) if vu["202506"].get(reg_, 0) else None,
             "pct59": r(v59.get(k, 0) / vid), "pct_individual": r(vind.get(k, 0) / vid),
             "reclamacoes": int(n_rec), "rec_por_mil": r(n_rec / den * 1000, 2) if den and den > 0 else None,
             "no_ranking_reclamacoes": bool(vid >= MIN_RANKING), "resolvidas": r(resol), "temas": top,
             "sus_falha_por_mil": r(sus_f.get(k, 0) / v24.get(k, float("nan")) * 1000, 2) if v24.get(k, 0) and v24.get(k, 0) >= 1000 else None}
        if rede is not None:
            rr = rede[(rede.REG == reg_) & (rede.SG_UF == uf)]
            o["hospitais"] = int(rr.HOSPITAIS.sum()) if len(rr) else 0
            o["hospitais_urgencia"] = int(rr.COM_URGENCIA.sum()) if len(rr) else 0
            o["hospitais_proprios"] = int(rr.PROPRIOS.sum()) if len(rr) else 0
        if preco is not None:
            pp = preco[(preco.REG == reg_) & (preco.UF == uf)]
            o["preco"] = {f"{x.FX}|{x.CONTRATACAO}|{x.ACOMODACAO}": [r(x.VCM, 2), int(x.PLANOS)] for x in pp.itertuples()}
        if reg_ in ind.index:
            io_ = ind.loc[reg_]
            o["nacional"] = {c: r(io_[c]) for c in NAC}
            if ind_flag.get(reg_, True):
                o["nacional"]["glosa_inicial"] = None
            o["ranking_nacional"] = bool(io_["RANKING_OK"])
        ops.append(o)
    rank = [o for o in ops if o["no_ranking_reclamacoes"] and o["rec_por_mil"] is not None]
    # média do estado: todas as reclamações de planos médicos do estado ÷ todos os clientes
    rec_uf = nip[nip.UF == uf].DEMANDAS.sum()
    cli_med = v_med.xs(uf, level="UF").sum()
    temas_uf = nip[nip.UF == uf].groupby("TEMA").DEMANDAS.sum().sort_values(ascending=False).head(5)
    cls_uf = nip[nip.UF == uf].groupby("CLASSE").DEMANDAS.sum()
    dados = {"uf": uf, "clientes": int(total), "populacao": int(pop[uf]), "cobertura": r(total / pop[uf]),
             "operadoras_com_clientes": int((atual >= 100).sum()),
             "rec_por_mil_estado": r(rec_uf / cli_med * 1000, 2), "reclamacoes_estado": int(rec_uf),
             "resolvidas_estado": r(cls_uf.get("resolvida", 0) / (cls_uf.get("resolvida", 0) + cls_uf.get("processo", 0))),
             "temas_estado": [[t, int(q)] for t, q in temas_uf.items()],
             "ranking_minimo": MIN_RANKING, "operadoras": ops, "no_ranking": len(rank)}
    (SAIDA / f"{uf}.json").write_text(json.dumps(dados, ensure_ascii=False, separators=(",", ":"), allow_nan=False), encoding="utf-8")
    resumo[uf] = {"concorrentes": len(ops), "no_ranking": len(rank), "rec_por_mil": dados["rec_por_mil_estado"]}

cli_br = v_med.sum()
brasil = {"rec_por_mil": r(nip.DEMANDAS.sum() / cli_br * 1000, 2), "reclamacoes": int(nip.DEMANDAS.sum()),
          "resolvidas": r(nip[nip.CLASSE == "resolvida"].DEMANDAS.sum() / nip[nip.CLASSE.isin(["resolvida", "processo"])].DEMANDAS.sum()),
          "estados": resumo}
(SAIDA / "brasil.json").write_text(json.dumps(brasil, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
print("Brasil:", brasil["rec_por_mil"], "por mil; resolvidas", brasil["resolvidas"])
print(json.dumps(resumo, ensure_ascii=False))
ce = json.load(open(SAIDA / "CE.json", encoding="utf-8"))
print("CE:", ce["rec_por_mil_estado"], ce["resolvidas_estado"], ce["temas_estado"][:3])
for o in sorted([o for o in ce["operadoras"] if o["no_ranking_reclamacoes"]], key=lambda o: -(o["rec_por_mil"] or 0)):
    print(f'  {o["nome"][:34]:34s} {o["vidas"]:>9,} {o["participacao"]:.1%}  {o["rec_por_mil"]:>6} por mil  resolvidas {o["resolvidas"]}  {o["temas"][:1]}')
