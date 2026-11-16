"""Preço de tabela e rede hospitalar por operadora × estado.

fato_preco.parquet  operadora × UF × faixa etária × contratação × acomodação
    VCM (valor comercial da mensalidade informado na nota técnica, NTRP jun/2026), só planos
    médico-hospitalares ATIVOS com internação. Mediana em dois passos: primeiro a mediana de cada plano
    entre os municípios da UF (um plano vendido em 180 municípios não vale 180 vezes), depois a mediana
    entre os planos da operadora.
fato_rede.parquet   operadora × UF (× município)
    Hospitais distintos (CNES, classe "Assistência Hospitalar") com vínculo ativo em pelo menos um plano
    ativo; quantos com urgência e emergência no contrato; quantos próprios.
Uso: python -I scripts/etl_preco_rede.py [preco|rede]
"""
import io, sys, zipfile, pathlib
sys.path.insert(0, str(pathlib.Path(__file__).parent))
from comum import *

FAIXAS = {"01": "0 a 18", "02": "19 a 23", "03": "24 a 28", "04": "29 a 33", "05": "34 a 38", "06": "39 a 43",
          "07": "44 a 48", "08": "49 a 53", "09": "54 a 58", "10": "59 ou mais"}


def enc_de(amostra: bytes):
    try:
        amostra[:-8].decode("utf-8"); return "utf-8"
    except UnicodeDecodeError:
        return "latin-1"


def preco():
    car_path = BRUTOS / "preco" / "caracteristicas.csv"
    with open(car_path, "rb") as f:
        enc = enc_de(f.read(3_000_000))
    car = pd.read_csv(car_path, sep=";", dtype=str, encoding=enc,
                      usecols=["ID_PLANO", "REGISTRO_OPERADORA", "GR_CONTRATACAO", "GR_SGMT_ASSISTENCIAL", "SGMT_ASSISTENCIAL",
                               "ACOMODACAO_HOSPITALAR", "SITUACAO_PLANO", "COBERTURA", "ABRANGENCIA_COBERTURA", "FATOR_MODERADOR"])
    print("situação:", car.SITUACAO_PLANO.value_counts().head(5).to_dict())
    print("segmentação:", car.GR_SGMT_ASSISTENCIAL.value_counts().head(8).to_dict())
    print("acomodação:", car.ACOMODACAO_HOSPITALAR.value_counts().head(6).to_dict())
    print("contratação:", car.GR_CONTRATACAO.value_counts().head(6).to_dict())
    ativo = car.SITUACAO_PLANO.fillna("").str.upper().str.startswith("ATIVO")
    hosp = car.SGMT_ASSISTENCIAL.fillna("").str.contains("Hospitalar", case=False)
    car = car[ativo & hosp].copy()
    car["REG"] = reg(car.REGISTRO_OPERADORA)
    ct = car.GR_CONTRATACAO.fillna("")
    car["CONTRATACAO"] = None
    car.loc[ct.str.match(r"^Individual"), "CONTRATACAO"] = "Individual ou familiar"
    car.loc[ct.str.match(r"^Coletivo [Ee]mpresarial$"), "CONTRATACAO"] = "Coletivo empresarial"
    car.loc[ct.str.match(r"^Coletivo por [Aa]des"), "CONTRATACAO"] = "Coletivo por adesão"
    ac = car.ACOMODACAO_HOSPITALAR.fillna("").str.lower()
    car["ACOMODACAO"] = None
    car.loc[ac.str.contains("individual|apartamento"), "ACOMODACAO"] = "Apartamento"
    car.loc[ac.str.contains("coletiva|enfermaria"), "ACOMODACAO"] = "Enfermaria"
    car = car.dropna(subset=["CONTRATACAO", "ACOMODACAO"]).set_index("ID_PLANO")[["REG", "CONTRATACAO", "ACOMODACAO", "FATOR_MODERADOR"]]
    print(f"planos ativos com internação e tipo definido: {len(car):,}")
    geo = pd.read_csv(BRUTOS / "preco" / "geografia.csv", sep=";", dtype=str, encoding="latin-1")
    geo = geo.set_index(geo.columns[0])[geo.columns[2]]  # CD_MUNICIPIO -> SG_UF
    zf = zipfile.ZipFile(BRUTOS / "preco" / "vcm_202606.zip")
    nome = zf.namelist()[0]
    with zf.open(nome) as f:
        enc = enc_de(f.read(3_000_000))
    partes = []
    with zf.open(nome) as f:
        for ch in pd.read_csv(io.TextIOWrapper(f, encoding=enc), sep=";", dtype=str, chunksize=2_000_000):
            ch.columns = [c.strip().upper() for c in ch.columns]
            ch = ch[ch.ID_PLANO.isin(car.index)]
            if ch.empty:
                continue
            ch["UF"] = ch.CD_MUNICIPIO.map(geo)
            ch["VCM"] = num_br(ch.VCM)
            ch["FX"] = ch.CD_FAIXA_ETARIA.str.strip().str.zfill(2)
            partes.append(ch.groupby(["ID_PLANO", "UF", "FX"]).VCM.agg(["median", "size"]).reset_index())
            print(f"  lote: {len(ch):,} linhas úteis", flush=True)
    p = pd.concat(partes).groupby(["ID_PLANO", "UF", "FX"]).apply(lambda g: (g["median"] * g["size"]).sum() / g["size"].sum()).rename("VCM_PLANO").reset_index()
    p = p.join(car, on="ID_PLANO")
    out = p.groupby(["REG", "UF", "FX", "CONTRATACAO", "ACOMODACAO"]).agg(VCM=("VCM_PLANO", "median"), PLANOS=("ID_PLANO", "nunique")).reset_index()
    out["FAIXA"] = out.FX.map(FAIXAS)
    out.to_parquet(TRATADOS / "fato_preco.parquet", index=False)
    print(f"fato_preco: {len(out):,} linhas, {out.REG.nunique()} operadoras, {out.UF.nunique()} UFs")
    x = out[(out.FX == "05") & (out.UF == "CE")].sort_values("VCM")
    print(x.head(12).to_string(index=False))


def rede():
    # o zip da ANS usa "deflate64", que o zipfile do Python não abre: lê cada CSV (um por UF) pelo unzip
    import shutil, subprocess
    arq = BRUTOS / "rede" / "rede.zip"
    unzip = shutil.which("unzip") or "unzip"
    nomes = [n for n in zipfile.ZipFile(arq).namelist() if n.lower().endswith(".csv")]
    cols = ["REGISTRO_OPERADORA", "DE_SITUACAO_PRINCIPAL", "CD_CNES", "DE_CLAS_ESTB_SAUDE", "LG_URGENCIA_EMERGENCIA",
            "DE_TIPO_PRESTADOR", "SG_UF", "CD_MUNICIPIO", "NM_MUNICIPIO", "DT_VINCULO_FIM"]
    chaves = ["REG", "SG_UF", "CD_MUNICIPIO", "NM_MUNICIPIO", "CD_CNES"]
    partes = []
    for nome in nomes:
        pr = subprocess.Popen([unzip, "-p", str(arq), nome], stdout=subprocess.PIPE)
        n = 0
        for ch in pd.read_csv(io.TextIOWrapper(pr.stdout, encoding="latin-1"), sep=";", dtype=str, usecols=cols, chunksize=2_000_000):
            ch = ch[ch.DE_SITUACAO_PRINCIPAL.fillna("").str.upper().str.startswith("ATIVO")
                    & ch.DT_VINCULO_FIM.isna()
                    & ch.DE_CLAS_ESTB_SAUDE.fillna("").str.contains("Hospitalar", case=False)]
            if ch.empty:
                continue
            ch = ch.assign(REG=reg(ch.REGISTRO_OPERADORA), URG=ch.LG_URGENCIA_EMERGENCIA.fillna("0").str.strip() == "1",
                           PROPRIO=ch.DE_TIPO_PRESTADOR.fillna("").str.startswith("Pr"))
            partes.append(ch.groupby(chaves).agg(URG=("URG", "max"), PROPRIO=("PROPRIO", "max")).reset_index())
            n += len(ch)
        pr.wait()
        if pr.returncode:
            raise SystemExit(f"unzip falhou em {nome}")
        print(f"  {nome}: {n:,} vínculos ativos de hospitais", flush=True)
    h = pd.concat(partes).groupby(chaves).agg(URG=("URG", "max"), PROPRIO=("PROPRIO", "max")).reset_index()
    h.to_parquet(TRATADOS / "rede_hospitais.parquet", index=False)
    uf = h.groupby(["REG", "SG_UF"]).agg(HOSPITAIS=("CD_CNES", "nunique"), COM_URGENCIA=("URG", "sum"), PROPRIOS=("PROPRIO", "sum"),
                                          MUNICIPIOS=("CD_MUNICIPIO", "nunique")).reset_index()
    uf.to_parquet(TRATADOS / "fato_rede.parquet", index=False)
    print(f"fato_rede: {len(uf):,} linhas | hospitais distintos no país: {h.CD_CNES.nunique():,}")
    print(uf[uf.SG_UF == "CE"].sort_values("HOSPITAIS", ascending=False).head(10).to_string(index=False))


if __name__ == "__main__":
    alvo = sys.argv[1] if len(sys.argv) > 1 else "tudo"
    if alvo in ("preco", "tudo"):
        preco()
    if alvo in ("rede", "tudo"):
        rede()
