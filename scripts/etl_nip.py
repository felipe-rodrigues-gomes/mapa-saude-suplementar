"""Reclamações (NIP) por operadora × estado do beneficiário × tema -> fato_nip.parquet

Período: jul/2025 a jun/2026 (o mesmo do IGR e da contabilidade em 12 meses).
Só assistência médica: sai a demanda de plano exclusivamente odontológico.
Excluídas as classificadas "Não se aplica" (duplicidade, beneficiário de outra operadora, dados insuficientes),
como faz a ANS.
Resolvida na mediação (taxa de resolutividade da ANS, ficha técnica):
  (Inativa + Não procedente + Reparação voluntária) ÷ (Inativa + NP + RVE + Núcleo)
  "Inativa" inclui a presunção de resolução quando o consumidor não responde (RN 483/22, art. 12, II).
Uso: python -I scripts/etl_nip.py
"""
import io, sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from comum import *

INI, FIM = "202507", "202606"
COLS = ["ANO_REFERENCIA", "MES_REFERENCIA", "ASSUNTO", "REGISTRO_OPERADORA", "TIPOS_COBERTURAS_CONTRATADAS",
        "UF_BENEFICIARIO", "CLASSIFICACAO_NIP", "NATUREZA_NIP", "SITUACAO_NIP", "TIPO_PLANO_CONTRATADO"]


def ler(caminho):
    with open(caminho, "rb") as f:
        amostra = f.read(3_000_000)
    enc = "utf-8"
    try:
        amostra[:-8].decode("utf-8")
    except UnicodeDecodeError:
        enc = "latin-1"
    partes = []
    for ch in pd.read_csv(caminho, sep=";", dtype=str, encoding=enc, usecols=COLS, chunksize=500_000, on_bad_lines="skip"):
        ch["COMP"] = ch.ANO_REFERENCIA.str.strip() + ch.MES_REFERENCIA.str.strip().str.zfill(2)
        ch = ch[ch.COMP.between(INI, FIM)]
        if not ch.empty:
            partes.append(ch)
    return pd.concat(partes)


def tema(assunto: str) -> str:
    """Último nível da árvore temática, sem espaços sobrando ("Produto ou Plano >> Cobertura >> Reembolso" -> "Reembolso")."""
    if not isinstance(assunto, str):
        return "Não informado"
    return assunto.split(">>")[-1].strip()


def classe(c, sit):
    c = (c or "").upper() if isinstance(c, str) else ""
    sit = sit if isinstance(sit, str) else ""
    if c in ("INATIVA", "NP", "RVE"):
        return "resolvida"
    if c.startswith("N") and "CLEO" in c:            # NÚCLEO (acento varia)
        return "processo"
    if c in ("NA",) or "Duplicidade" in sit or "não pertencente" in sit or "Insuficiência" in sit or "Insufici" in sit:
        return "nao_se_aplica"
    return "andamento"


def main():
    d = pd.concat([ler(BRUTOS / "nip" / f"nip_{a}.csv") for a in (2025, 2026)])
    print(f"demandas no período: {len(d):,}")
    d["REG"] = reg(d.REGISTRO_OPERADORA)
    d["UF"] = d.UF_BENEFICIARIO.fillna("XX").str.strip().str.upper()
    cob = d.TIPOS_COBERTURAS_CONTRATADAS.fillna("")
    d = d[~cob.str.strip().str.startswith("Odontol")]          # só exclusivamente odontológico sai
    d["CLASSE"] = [classe(c, s) for c, s in zip(d.CLASSIFICACAO_NIP, d.SITUACAO_NIP)]
    print("classes:", d.CLASSE.value_counts().to_dict())
    d = d[d.CLASSE != "nao_se_aplica"]
    d["TEMA"] = d.ASSUNTO.map(tema)
    d["NATUREZA"] = d.NATUREZA_NIP.fillna("Não informada").str.strip()
    g = d.groupby(["REG", "UF", "TEMA", "NATUREZA", "CLASSE"]).size().rename("DEMANDAS").reset_index()
    g.to_parquet(TRATADOS / "fato_nip.parquet", index=False)
    print(f"fato_nip: {len(g):,} linhas | demandas válidas: {g.DEMANDAS.sum():,} | operadoras: {g.REG.nunique()}")
    print("natureza:", g.groupby("NATUREZA").DEMANDAS.sum().to_dict())
    print("temas:", g.groupby("TEMA").DEMANDAS.sum().sort_values(ascending=False).head(12).to_dict())


if __name__ == "__main__":
    main()
