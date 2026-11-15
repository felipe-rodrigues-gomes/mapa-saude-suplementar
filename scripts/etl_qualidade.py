"""IGR, IDSS e glosa -> fatos em formato longo.

fato_igr.parquet    operadora × competência (mês) × cobertura
fato_idss.parquet   operadora × ano do IDSS (ano-base = ano - 1) × dimensão
fato_glosa.parquet  operadora × semestre, um indicador por coluna
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from comum import *


def igr():
    d = ler_csv(BRUTOS / "igr" / "igr_2023.csv")
    out = pd.DataFrame({
        "REG": reg(d.REGISTRO_OPERADORA),
        "COMPETENCIA": d.COMPETENCIA.str.replace("-", ""),
        "COBERTURA": d.COBERTURA.map({"Assistência médica": "MH", "Exclusivamente odontológica": "ODONTO"}),
        "IGR": num_br(d.IGR),
        "QTD_RECLAMACOES": pd.to_numeric(d.QTD_RECLAMACOES),
        "QTD_BENEFICIARIOS": pd.to_numeric(d.QTD_BENEFICIARIOS),
        "PORTE_IGR": d.PORTE_OPERADORA,
    })
    # conferência: IGR = reclamações / beneficiários × 100 mil
    calc = out.QTD_RECLAMACOES / out.QTD_BENEFICIARIOS * 1e5
    dif = (calc - out.IGR).abs()
    print(f"IGR: {len(out):,} linhas | confere com recl/benef×100mil: {(dif < 0.01).mean():.1%} | "
          f"benef=0: {(out.QTD_BENEFICIARIOS == 0).sum()}")
    out.to_parquet(TRATADOS / "fato_igr.parquet", index=False)


def idss():
    d = ler_csv(BRUTOS / "idss" / "idss_2016_2025.csv")
    d["REG"] = reg(d.REGISTRO_OPERADORA)
    cols = [c for c in d.columns if c[:4] in ("IDSS", "IDQS", "IDGA", "IDSM", "IDGR")]
    l = d.melt(id_vars="REG", value_vars=cols, var_name="col", value_name="v")
    l["DIMENSAO"] = l.col.str[:4]
    l["ANO_IDSS"] = l.col.str[5:9].astype(int)
    l["ANO_BASE"] = l.col.str[10:14].astype(int)
    l["NOTA"] = num_br(l.v)
    l = l.dropna(subset=["NOTA"])
    w = l.pivot_table(index=["REG", "ANO_IDSS", "ANO_BASE"], columns="DIMENSAO", values="NOTA").reset_index()
    w.columns.name = None
    fora = ((w[["IDSS", "IDQS", "IDGA", "IDSM", "IDGR"]] < 0) | (w[["IDSS", "IDQS", "IDGA", "IDSM", "IDGR"]] > 1)).sum().sum()
    print(f"IDSS: {len(w):,} linhas | notas fora de 0–1: {fora} | por ano: {w.groupby('ANO_IDSS').REG.count().to_dict()}")
    w.to_parquet(TRATADOS / "fato_idss.parquet", index=False)


def glosa():
    arqs = {"percentual_glosa_inicial": ("PC_GLOSA_INCIAL", "GLOSA_INICIAL_PCT"),
            "percentual_glosa_final": ("PC_GLOSA_FINAL", "GLOSA_FINAL_PCT"),
            "tempo_medio_pagamento": ("QT_TEMPO_PAGAMENTO", "TEMPO_PAGAMENTO_DIAS"),
            "numero_guias_sem_retorno": ("PC_NUMERO_GUIAS_SEM_RETORNO", "GUIAS_SEM_RETORNO_QTD_PCT"),
            "valor_guias_sem_retorno": ("PC_VALOR_GUIAS_SEM_RETORNO", "GUIAS_SEM_RETORNO_VALOR_PCT")}
    w = None
    for arq, (col, nome) in arqs.items():
        d = ler_csv(BRUTOS / "glosa" / f"{arq}.csv")
        x = pd.DataFrame({"REG": reg(d.REGISTRO_OPERADORA), "SEMESTRE": d.CD_PERIODO.str.replace("-0", "S"),
                          "PORTE_GLOSA": d.DE_PORTE_OPERADORA,
                          "SEGMENTACAO_GLOSA": d.NM_SEGMENTACAO_OPERADORA, nome: num_br(d[col])})
        assert not x.duplicated(["REG", "SEMESTRE"]).any(), arq
        w = x if w is None else w.merge(x, on=["REG", "SEMESTRE", "PORTE_GLOSA", "SEGMENTACAO_GLOSA"], how="outer")
    # regras de qualidade (não apagam o dado, só marcam)
    w["FLAG_GLOSA_FINAL_MAIOR"] = w.GLOSA_FINAL_PCT > w.GLOSA_INICIAL_PCT + 0.01
    w["FLAG_GLOSA_EXTREMA"] = (w.GLOSA_INICIAL_PCT < 0.05) | (w.GLOSA_INICIAL_PCT >= 50)
    print(f"Glosa: {len(w):,} linhas | semestres {w.SEMESTRE.min()}–{w.SEMESTRE.max()} | "
          f"final>inicial: {w.FLAG_GLOSA_FINAL_MAIOR.mean():.1%} | extrema (<0,05% ou ≥50%): {w.FLAG_GLOSA_EXTREMA.mean():.1%}")
    w.to_parquet(TRATADOS / "fato_glosa.parquet", index=False)


if __name__ == "__main__":
    igr(); idss(); glosa()
