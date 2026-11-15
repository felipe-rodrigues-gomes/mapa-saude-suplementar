"""Cadastro das operadoras + fato de beneficiários consolidado.

dim_operadora.parquet      uma linha por operadora (ativas + canceladas)
fato_beneficiarios.parquet competência × operadora × UF × cobertura × contratação × faixa de reajuste × sexo

Regras:
- SEGMENTO (como a ANS): MH se a operadora tem beneficiário médico-hospitalar; ODONTO se só tem
  odontológico; ADM para administradora de benefícios; sem beneficiários -> segmentação do painel
  de glosa / IGR -> modalidade.
- PORTE (como a ANS): vínculos ativos totais (médico + odonto) no mês: pequeno < 20 mil,
  médio 20 mil–100 mil, grande > 100 mil. Na dim vai o porte do último mês com carteira.
- Campos de contato do cadastro (representante, e-mail, telefone) são descartados.
"""
import sys, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from comum import *

MODALIDADE = {
    "Autogestão": "Autogestão", "Cooperativa Médica": "Cooperativa médica", "Filantropia": "Filantropia",
    "Medicina de Grupo": "Medicina de grupo", "Seguradora Especializada em Saúde": "Seguradora",
    "Seguradora": "Seguradora", "Cooperativa odontológica": "Cooperativa odontológica",
    "Odontologia de Grupo": "Odontologia de grupo", "Administradora de Benefícios": "Administradora",
    "Administradora": "Administradora",
}
REGIAO = {**dict.fromkeys("AC AM AP PA RO RR TO".split(), "Norte"),
          **dict.fromkeys("AL BA CE MA PB PE PI RN SE".split(), "Nordeste"),
          **dict.fromkeys("DF GO MS MT".split(), "Centro-Oeste"),
          **dict.fromkeys("ES MG RJ SP".split(), "Sudeste"),
          **dict.fromkeys("PR RS SC".split(), "Sul")}


def porte(vidas):
    return pd.cut(vidas, [-1, 19_999, 100_000, float("inf")], labels=["Pequeno", "Médio", "Grande"]).astype(str)


def beneficiarios() -> pd.DataFrame:
    partes = []
    for p in sorted((TRATADOS / "beneficiarios").glob("*.parquet")):
        d = pd.read_parquet(p)
        d["REG"] = reg(d.CD_OPERADORA)
        # parte dos arquivos da ANS vem com acentos corrompidos na origem ("M�dico-hospitalar"):
        # a classificação usa só os trechos sem acento
        # e alguns arquivos UTF-8 foram lidos como latin-1 ("MÃ©dico"): desfaz o mojibake
        for c in ("COBERTURA_ASSIST_PLAN", "DE_CONTRATACAO_PLANO", "DE_FAIXA_ETARIA_REAJ"):
            d[c] = d[c].map(lambda s: s.encode("latin-1").decode("utf-8", "replace")
                            if isinstance(s, str) and "Ã" in s else s)
        cob = d.COBERTURA_ASSIST_PLAN.fillna("")
        d["COBERTURA"] = "NI"
        d.loc[cob.str.match(r"^M.dico-hospitalar"), "COBERTURA"] = "MH"
        d.loc[cob.str.match(r"^Odontol.gico"), "COBERTURA"] = "ODONTO"
        ct = d.DE_CONTRATACAO_PLANO.fillna("")
        d["CONTRATACAO"] = "Outros / não identificado"
        misto = ct.str.contains("+", regex=False)   # planos com mais de um tipo -> "Outros"
        d.loc[ct.str.match(r"^Coletivo Empresarial") & ~misto, "CONTRATACAO"] = "Coletivo empresarial"
        d.loc[ct.str.match(r"^Individual ou Familiar$"), "CONTRATACAO"] = "Individual ou familiar"
        d.loc[ct.str.match(r"^Coletivo por Ades") & ~misto, "CONTRATACAO"] = "Coletivo por adesão"
        d["FAIXA_REAJ"] = d.DE_FAIXA_ETARIA_REAJ.where(~d.DE_FAIXA_ETARIA_REAJ.str.startswith("Informada", na=True), "Não informada")
        d["SEXO"] = d.TP_SEXO.where(d.TP_SEXO.isin(["F", "M"]), "NI")
        d["UF"] = d.SG_UF.fillna("XX")
        g = d.groupby(["COMPETENCIA", "REG", "UF", "COBERTURA", "CONTRATACAO", "FAIXA_REAJ", "SEXO"], as_index=False)[
            ["QT_BENEFICIARIO_ATIVO", "QT_BENEFICIARIO_ADERIDO", "QT_BENEFICIARIO_CANCELADO"]].sum()
        partes.append(g)
    f = pd.concat(partes, ignore_index=True)
    f.columns = [c.replace("QT_BENEFICIARIO_", "") for c in f.columns]
    f = f.rename(columns={"ATIVO": "ATIVOS", "ADERIDO": "ADERIDOS", "CANCELADO": "CANCELADOS"})
    f["COMPETENCIA"] = f.COMPETENCIA.astype(str)
    for c in ["UF", "COBERTURA", "CONTRATACAO", "FAIXA_REAJ", "SEXO"]:
        f[c] = f[c].astype("category")
    return f


def main():
    ben = beneficiarios()
    ben.to_parquet(TRATADOS / "fato_beneficiarios.parquet", index=False)
    print(f"fato_beneficiarios: {len(ben):,} linhas, competências {sorted(ben.COMPETENCIA.unique())}")

    a = ler_csv(BRUTOS / "cadop" / "ativas.csv").assign(ATIVA=True)
    c = ler_csv(BRUTOS / "cadop" / "canceladas.csv").assign(ATIVA=False)
    cad = pd.concat([a, c], ignore_index=True)
    cad["REG"] = reg(cad.REGISTRO_OPERADORA)
    dim = pd.DataFrame({
        "REG": cad.REG, "CNPJ": cad.CNPJ, "RAZAO_SOCIAL": cad.RAZAO_SOCIAL.str.strip(),
        "NOME_FANTASIA": cad.NOME_FANTASIA.str.strip(),
        "MODALIDADE": cad.MODALIDADE.map(MODALIDADE).fillna(cad.MODALIDADE),
        "UF_SEDE": cad.UF, "CIDADE_SEDE": cad.CIDADE, "ATIVA": cad.ATIVA,
        "DATA_REGISTRO": pd.to_datetime(cad.DATA_REGISTRO_ANS, errors="coerce"),
        "DATA_CANCELAMENTO": pd.to_datetime(cad.get("DATA_DESCREDENCIAMENTO"), errors="coerce"),
    }).drop_duplicates("REG")
    dim["REGIAO_SEDE"] = dim.UF_SEDE.map(REGIAO)

    # carteira no último mês em que a operadora aparece
    ult = ben.groupby("REG", observed=True).COMPETENCIA.max().rename("ULT_COMP")
    tot = ben.groupby(["REG", "COMPETENCIA", "COBERTURA"], observed=True).ATIVOS.sum().unstack(fill_value=0)
    tot["TOTAL"] = tot.sum(axis=1)
    tot = tot.reset_index().merge(ult, on="REG")
    tot = tot[tot.COMPETENCIA == tot.ULT_COMP].set_index("REG")
    dim = dim.set_index("REG").join(tot[["ULT_COMP", "MH", "ODONTO", "TOTAL"]].rename(
        columns={"ULT_COMP": "COMPETENCIA_CARTEIRA", "MH": "VIDAS_MH", "ODONTO": "VIDAS_ODONTO", "TOTAL": "VIDAS_TOTAL"}))
    dim["PORTE"] = porte(dim.VIDAS_TOTAL).where(dim.VIDAS_TOTAL.notna(), "Sem carteira")

    # UF principal (carteira médico-hospitalar; odonto se não tiver médico)
    uf = ben[ben.COMPETENCIA == ben.REG.map(ult)]
    uf = uf.groupby(["REG", "COBERTURA", "UF"], observed=True).ATIVOS.sum().reset_index()
    uf = uf.sort_values("COBERTURA").groupby(["REG", "UF"], observed=True).first().reset_index()  # MH antes de ODONTO
    uf = uf.sort_values(["REG", "ATIVOS"], ascending=[True, False])
    princ = uf.groupby("REG").first()
    princ["PCT_UF_PRINCIPAL"] = princ.ATIVOS / uf.groupby("REG").ATIVOS.sum()
    dim = dim.join(princ[["UF"]].rename(columns={"UF": "UF_PRINCIPAL"})).join(princ[["PCT_UF_PRINCIPAL"]])

    # segmento
    g = pd.read_parquet(TRATADOS / "fato_glosa.parquet").sort_values("SEMESTRE").groupby("REG").SEGMENTACAO_GLOSA.last()
    seg_glosa = g.map(lambda s: "MH" if "dico" in s else "ODONTO")
    dim["SEGMENTO"] = None
    dim.loc[dim.VIDAS_MH > 0, "SEGMENTO"] = "MH"
    dim.loc[(dim.SEGMENTO.isna()) & (dim.VIDAS_ODONTO > 0), "SEGMENTO"] = "ODONTO"
    dim.loc[dim.MODALIDADE == "Administradora", "SEGMENTO"] = "ADM"
    dim["SEGMENTO"] = dim.SEGMENTO.fillna(seg_glosa)
    dim.loc[dim.SEGMENTO.isna() & dim.MODALIDADE.isin(["Cooperativa odontológica", "Odontologia de grupo"]), "SEGMENTO"] = "ODONTO"
    dim["SEGMENTO"] = dim.SEGMENTO.fillna("MH")
    dim["FONTE_SEGMENTO"] = "beneficiários"
    dim.loc[dim.VIDAS_TOTAL.isna(), "FONTE_SEGMENTO"] = "glosa/modalidade"

    # nome curto para gráfico
    dim["NOME_EXIBICAO"] = dim.NOME_FANTASIA.where(dim.NOME_FANTASIA.notna() & (dim.NOME_FANTASIA.str.len() > 2),
                                                   dim.RAZAO_SOCIAL)
    dim = dim.reset_index()

    # operadoras que aparecem nos fatos mas não no cadastro
    contab = pd.read_parquet(TRATADOS / "fato_contabil.parquet", columns=["REG"]).REG.unique()
    orfas = sorted(set(contab) - set(dim.REG)) + sorted(set(ben.REG.unique()) - set(dim.REG))
    if orfas:
        print(f"ATENÇÃO: {len(orfas)} operadoras sem cadastro:", orfas[:20])
    dim.to_parquet(TRATADOS / "dim_operadora.parquet", index=False)
    print(f"dim_operadora: {len(dim):,} | segmento: {dim.SEGMENTO.value_counts().to_dict()} | "
          f"porte (ativas): {dim[dim.ATIVA].PORTE.value_counts().to_dict()}")
    x = dim[(dim.SEGMENTO == "MH") & ~dim.MODALIDADE.isin(["Autogestão", "Cooperativa médica", "Filantropia", "Medicina de grupo", "Seguradora"])]
    y = dim[(dim.SEGMENTO == "ODONTO") & dim.MODALIDADE.isin(["Autogestão", "Cooperativa médica", "Filantropia", "Medicina de grupo", "Seguradora"])]
    print(f"modalidade odonto classificada MH: {len(x)} | modalidade médica classificada ODONTO: {len(y)}")
    print(y[["REG", "RAZAO_SOCIAL", "MODALIDADE", "VIDAS_MH", "VIDAS_ODONTO"]].head(15).to_string(index=False))


if __name__ == "__main__":
    main()
