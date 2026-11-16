"""Capítulo 1 por estado: mensalidade média, para onde ela vai e o lucro das operadoras com os clientes do estado.

A ANS publica as contas por operadora, não por estado. Estimativa: cada conta de cada operadora
(12 meses até jun/2026, mesmas contas do Brasil em exportar_site.py) é repartida entre os estados
pela parte dos clientes de plano médico que ela tem em cada um (média de set/25, dez/25, mar/26 e jun/26).
Mensalidade média = contraprestações efetivas do estado ÷ clientes médios do estado ÷ 12.
Saída: site/dados/cada_uf.json
"""
import json, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from comum import *

CONTAS = ["31", "32", "33", "34", "37", "41", "43", "44", "46", "35", "45", "36", "47", "61", "3", "4"]
dim = pd.read_parquet(TRATADOS / "dim_operadora.parquet")
mhreg = set(dim[dim.SEGMENTO == "MH"].REG)


def contas(z):
    x = ler_zip_csv(BRUTOS / "contabeis" / f"{z}.zip")
    x["REG"] = reg(x.REG_ANS)
    x = x[x.REG.isin(mhreg) & x.CD_CONTA_CONTABIL.isin(CONTAS)]
    return x.assign(v=num_br(x.VL_SALDO_FINAL)).groupby(["REG", "CD_CONTA_CONTABIL"]).v.sum()


s = contas("2T2026").add(contas("4T2025"), fill_value=0).sub(contas("2T2025"), fill_value=0)
s = s.unstack(fill_value=0).reindex(columns=CONTAS, fill_value=0)

ben = pd.read_parquet(TRATADOS / "fato_beneficiarios.parquet")
ben = ben[(ben.COBERTURA == "MH") & ben.REG.isin(mhreg) & ben.COMPETENCIA.isin(["202509", "202512", "202603", "202606"])]
ben["UF"] = ben.UF.astype(str)
vid = ben.groupby(["REG", "UF", "COMPETENCIA"], observed=True).ATIVOS.sum().groupby(["REG", "UF"], observed=True).mean()
vid = vid[vid > 0]
parte = vid / vid.groupby(level="REG").transform("sum")          # parte dos clientes da operadora em cada UF

regs = s.index.intersection(parte.index.get_level_values("REG").unique())
print("operadoras com contas e clientes:", len(regs), "de", len(s))


def bloco(t, clientes):
    base = t["31"] + t["32"]
    p = {"atendimento": t["41"], "administracao": t["46"], "venda": t["43"], "outras": t["44"] - (t["33"] + t["34"] + t["37"])}
    p["sobra"] = base - sum(p.values())
    out = {k: round(v / base * 100, 4) for k, v in p.items()}
    out.update({"aplicacoes": round((t["35"] - t["45"]) / base * 100, 4),
                "lucro_pct": round((t["3"] - t["4"] - t["61"]) / base * 100, 4),
                "lucro_bi": round((t["3"] - t["4"] - t["61"]) / 1e9, 3),
                "sobra_bi": round(p["sobra"] / 1e9, 3), "aplicacoes_bi": round((t["35"] - t["45"]) / 1e9, 3),
                "receita_bi": round(base / 1e9, 3), "clientes": int(round(clientes)),
                "mensalidade": round(base / clientes / 12, 2)})
    return out


saida = {}
for uf, g in parte.groupby(level="UF"):
    w = g.droplevel("UF").reindex(regs).dropna()
    t = s.loc[w.index].mul(w, axis=0).sum()
    saida[uf] = bloco(t, vid.xs(uf, level="UF").reindex(w.index).sum())
saida["BR"] = bloco(s.loc[regs].sum(), vid.groupby(level="REG").sum().reindex(regs).sum())

(RAIZ / "site" / "dados" / "cada_uf.json").write_text(json.dumps(saida, ensure_ascii=False, separators=(",", ":")), encoding="utf-8")
for uf in ["BR", "CE", "SP", "RJ", "MG", "RR"]:
    d = saida[uf]
    print(uf, f"mensalidade R$ {d['mensalidade']:.2f}", f"atend {d['atendimento']:.1f}%", f"sobra {d['sobra']:.1f}%",
          f"lucro R$ {d['lucro_bi']:.2f} bi", f"receita R$ {d['receita_bi']:.1f} bi", f"clientes {d['clientes']:,}")
print("soma lucro UFs:", round(sum(v["lucro_bi"] for k, v in saida.items() if k != "BR"), 2), "| BR:", saida["BR"]["lucro_bi"])
