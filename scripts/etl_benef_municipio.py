"""Beneficiários por município (para o mapa de cobertura), só nos meses com população IBGE consistente.

Saída: dados/tratados/beneficiarios_municipio.parquet
Grão: competência × município (IBGE 6 dígitos) × cobertura; vidas totais e com 59 anos ou mais.
Uso: python -I scripts/etl_benef_municipio.py <raiz_do_projeto>
"""
import io, sys, time, zipfile, urllib.request
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
import pandas as pd

RAIZ = Path(sys.argv[1])
BASE = "https://dadosabertos.ans.gov.br/FTP/PDA/informacoes_consolidadas_de_beneficiarios-024"
UFS = "AC AL AM AP BA CE DF ES GO MA MG MS MT PA PB PE PI PR RJ RN RO RR RS SC SE SP TO XX".split()
MESES = ["202412", "202512", "202609"]
TMP = RAIZ / "dados" / "brutos" / "_tmp_benef_mun"
SAIDA = RAIZ / "dados" / "tratados" / "beneficiarios_municipio.parquet"


def processar(mes, uf):
    nome = f"pda-024-icb-{uf}-{mes[:4]}_{mes[4:]}.zip"
    z = TMP / nome
    for t in range(4):
        try:
            urllib.request.urlretrieve(f"{BASE}/{mes}/{nome}", z); break
        except Exception as e:
            if "404" in str(e): return None
            time.sleep(10 * (t + 1))
    zf = zipfile.ZipFile(z); membro = zf.namelist()[0]
    partes = []
    with zf.open(membro) as f:
        # lê como latin-1 (nunca falha); a classificação usa só os trechos sem acento
        for ch in pd.read_csv(io.TextIOWrapper(f, encoding="latin-1"), sep=";", dtype=str, chunksize=1_500_000,
                              usecols=["SG_UF", "CD_MUNICIPIO", "COBERTURA_ASSIST_PLAN", "DE_FAIXA_ETARIA_REAJ", "QT_BENEFICIARIO_ATIVO"]):
            ch["q"] = pd.to_numeric(ch.QT_BENEFICIARIO_ATIVO, errors="coerce").fillna(0).astype("int64")
            cob = ch.COBERTURA_ASSIST_PLAN.fillna("")
            ch["COBERTURA"] = "NI"
            ch.loc[cob.str.match(r"^M.{1,2}dico"), "COBERTURA"] = "MH"
            ch.loc[cob.str.match(r"^Odontol"), "COBERTURA"] = "ODONTO"
            ch["q59"] = ch.q.where(ch.DE_FAIXA_ETARIA_REAJ.fillna("").str.startswith("59"), 0)
            partes.append(ch.groupby(["SG_UF", "CD_MUNICIPIO", "COBERTURA"], dropna=False)[["q", "q59"]].sum().reset_index())
    zf.close(); z.unlink()
    return pd.concat(partes)


def main():
    TMP.mkdir(parents=True, exist_ok=True)
    tudo = []
    for mes in MESES:
        t0 = time.time()
        with ThreadPoolExecutor(max_workers=4) as ex:
            res = [r for r in ex.map(lambda uf: processar(mes, uf), UFS) if r is not None]
        d = pd.concat(res).groupby(["SG_UF", "CD_MUNICIPIO", "COBERTURA"], dropna=False)[["q", "q59"]].sum().reset_index()
        d.insert(0, "COMPETENCIA", mes)
        tudo.append(d)
        print(f"{mes}: {d.q.sum():,} vidas, {d.CD_MUNICIPIO.nunique()} municípios, {time.time() - t0:.0f}s", flush=True)
    out = pd.concat(tudo).rename(columns={"q": "ATIVOS", "q59": "ATIVOS_59MAIS"})
    out.to_parquet(SAIDA, index=False)
    print("FIM")


if __name__ == "__main__":
    main()
